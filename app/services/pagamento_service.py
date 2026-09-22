"""
Validação de compras das lojas (App Store / Google Play).

Toda assinatura nasce aqui: a rota /assinatura/ativar só escreve no banco
depois que a loja confirma a compra. Nada de conceder premium pela palavra do
cliente - um recibo conferido no aparelho não vale nada, porque o aparelho é de
quem está comprando.

Configuração (variáveis de ambiente):

  Google Play
    GOOGLE_PLAY_SERVICE_ACCOUNT       caminho do JSON da service account
    GOOGLE_PLAY_SERVICE_ACCOUNT_JSON  ou o JSON inteiro, para servidores sem disco
    ANDROID_PACKAGE_NAME              padrão com.agentcicle.app

  App Store
    APPLE_ISSUER_ID                   App Store Connect > Integrações > Chaves
    APPLE_KEY_ID                      id da chave .p8
    APPLE_PRIVATE_KEY                 conteúdo do .p8 (ou APPLE_PRIVATE_KEY_PATH)
    APPLE_BUNDLE_ID                   padrão com.agentcicle.app

  Produtos
    PRODUTOS_ASSINATURA               "id:meses,id:meses"; padrão em PRODUTOS_PADRAO

Sem a configuração da plataforma a validação falha fechado (503): é melhor
recusar uma compra legítima e devolver o dinheiro do que liberar premium sem
pagamento. Renovação, cancelamento e reembolso dependem das notificações das
lojas (App Store Server Notifications v2 / Google Play RTDN), que ainda não
estão implementadas.
"""

import json
import os
import time
from base64 import urlsafe_b64decode
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Optional

import jwt
import requests
from fastapi import HTTPException

Plataforma = Literal["ios", "android"]

# product_id da loja -> meses de assinatura concedidos.
PRODUTOS_PADRAO = {
    "ciclica_premium_mensal": 1,
    "ciclica_premium_anual": 12,
}

_TIMEOUT = 20

_APPLE_HOSTS = (
    "https://api.storekit.itunes.apple.com",
    "https://api.storekit-sandbox.itunes.apple.com",
)

_GOOGLE_ESCOPO = "https://www.googleapis.com/auth/androidpublisher"
_GOOGLE_ESTADOS_VALIDOS = (
    "SUBSCRIPTION_STATE_ACTIVE",
    "SUBSCRIPTION_STATE_IN_GRACE_PERIOD",
)


@dataclass(frozen=True)
class CompraValidada:
    """Resultado de uma compra confirmada pela loja."""

    plataforma: Plataforma
    id_transacao: str
    product_id: str
    duracao_meses: int
    expira_em: Optional[datetime] = None


def produtos_assinatura() -> dict:
    """Mapa product_id -> meses, lido do ambiente ou o padrão."""
    bruto = os.getenv("PRODUTOS_ASSINATURA")
    if not bruto:
        return dict(PRODUTOS_PADRAO)

    produtos = {}
    for par in bruto.split(","):
        produto, _, meses = par.partition(":")
        try:
            produtos[produto.strip()] = int(meses.strip())
        except ValueError:
            continue
    return produtos or dict(PRODUTOS_PADRAO)


def _meses_do_produto(product_id: str) -> int:
    meses = produtos_assinatura().get(product_id)
    if not meses:
        # Produto que não é nosso, ou que existe na loja e não foi cadastrado
        # aqui: sem duração conhecida não há o que ativar.
        raise HTTPException(status_code=400, detail="Produto não reconhecido")
    return meses


def _sem_configuracao(loja: str) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail=f"Validação de compra indisponível: {loja} não configurada no servidor.",
    )


def _compra_invalida(motivo: str) -> HTTPException:
    return HTTPException(status_code=400, detail=f"Compra inválida: {motivo}")


# --------------------------------------------------------------- Google Play
def _credenciais_google():
    """Credenciais da service account, do arquivo ou do JSON no ambiente."""
    from google.oauth2 import service_account  # import tardio: só o Android usa

    bruto = os.getenv("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON")
    caminho = os.getenv("GOOGLE_PLAY_SERVICE_ACCOUNT")

    if bruto:
        info = json.loads(bruto)
    elif caminho and os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as arquivo:
            info = json.load(arquivo)
    else:
        raise _sem_configuracao("Google Play")

    return service_account.Credentials.from_service_account_info(info, scopes=[_GOOGLE_ESCOPO])


def _token_google() -> str:
    from google.auth.transport.requests import Request as RequisicaoGoogle

    credenciais = _credenciais_google()
    credenciais.refresh(RequisicaoGoogle())
    return credenciais.token


def _validar_android(token_compra: str) -> CompraValidada:
    """
    Confirma a assinatura pela Google Play Developer API (subscriptionsv2).

    Também reconhece a compra quando necessário: sem o acknowledge em até 3
    dias, o Google estorna o pagamento automaticamente.
    """
    pacote = os.getenv("ANDROID_PACKAGE_NAME", "com.agentcicle.app")
    cabecalhos = {"Authorization": f"Bearer {_token_google()}"}
    url = (
        f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/"
        f"{pacote}/purchases/subscriptionsv2/tokens/{token_compra}"
    )

    resposta = requests.get(url, headers=cabecalhos, timeout=_TIMEOUT)
    if resposta.status_code == 404:
        raise _compra_invalida("a Google Play não reconhece este token")
    if resposta.status_code >= 400:
        raise HTTPException(status_code=502, detail="Google Play indisponível para validar a compra")

    dados = resposta.json()
    estado = dados.get("subscriptionState")
    if estado not in _GOOGLE_ESTADOS_VALIDOS:
        raise _compra_invalida(f"assinatura não está ativa ({estado})")

    itens = dados.get("lineItems") or []
    if not itens:
        raise _compra_invalida("compra sem itens")

    item = itens[-1]
    product_id = item.get("productId", "")
    duracao_meses = _meses_do_produto(product_id)
    expira_em = _data_iso(item.get("expiryTime"))

    # latestOrderId identifica o pagamento: é ele que impede a mesma compra
    # valer em duas contas.
    id_transacao = dados.get("latestOrderId") or token_compra

    if dados.get("acknowledgementState") == "ACKNOWLEDGEMENT_STATE_PENDING":
        _reconhecer_android(pacote, product_id, token_compra, cabecalhos)

    return CompraValidada("android", id_transacao, product_id, duracao_meses, expira_em)


def _reconhecer_android(pacote: str, product_id: str, token_compra: str, cabecalhos: dict) -> None:
    """Acknowledge da compra. Falhar aqui não invalida a assinatura já paga."""
    url = (
        f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/"
        f"{pacote}/purchases/subscriptions/{product_id}/tokens/{token_compra}:acknowledge"
    )
    try:
        requests.post(url, headers=cabecalhos, json={}, timeout=_TIMEOUT)
    except requests.RequestException as erro:
        print(f"Aviso: não foi possível reconhecer a compra na Google Play: {erro}")


# ----------------------------------------------------------------- App Store
def _chave_apple() -> str:
    chave = os.getenv("APPLE_PRIVATE_KEY")
    if chave:
        # Em .env a chave costuma vir numa linha só, com \n escapado.
        return chave.replace("\\n", "\n")

    caminho = os.getenv("APPLE_PRIVATE_KEY_PATH")
    if caminho and os.path.exists(caminho):
        with open(caminho, "r", encoding="utf-8") as arquivo:
            return arquivo.read()

    raise _sem_configuracao("App Store")


def _token_apple() -> str:
    """JWT ES256 exigido pela App Store Server API."""
    issuer = os.getenv("APPLE_ISSUER_ID")
    key_id = os.getenv("APPLE_KEY_ID")
    if not issuer or not key_id:
        raise _sem_configuracao("App Store")

    agora = int(time.time())
    return jwt.encode(
        {
            "iss": issuer,
            "iat": agora,
            "exp": agora + 600,
            "aud": "appstoreconnect-v1",
            "bid": os.getenv("APPLE_BUNDLE_ID", "com.agentcicle.app"),
        },
        _chave_apple(),
        algorithm="ES256",
        headers={"kid": key_id, "typ": "JWT"},
    )


def _payload_jws(assinado: str) -> dict:
    """
    Conteúdo de um JWS da Apple, sem verificar a assinatura.

    A resposta veio da própria App Store por TLS nesta requisição, então a
    origem já está garantida. Verificar a cadeia x5c seria necessário para um
    JWS recebido de terceiros, como o corpo de uma notificação.
    """
    try:
        corpo = assinado.split(".")[1]
        corpo += "=" * (-len(corpo) % 4)
        return json.loads(urlsafe_b64decode(corpo))
    except (IndexError, ValueError) as erro:
        raise _compra_invalida("resposta da App Store ilegível") from erro


def _validar_ios(token_compra: str) -> CompraValidada:
    """
    Confirma a transação pela App Store Server API.

    `token_compra` é o transactionId do StoreKit 2. Tenta produção e cai para o
    sandbox, que é o ambiente das compras de teste e do TestFlight.
    """
    cabecalhos = {"Authorization": f"Bearer {_token_apple()}"}
    resposta = None

    for host in _APPLE_HOSTS:
        resposta = requests.get(
            f"{host}/inApps/v1/transactions/{token_compra}",
            headers=cabecalhos,
            timeout=_TIMEOUT,
        )
        if resposta.status_code != 404:
            break

    if resposta is None or resposta.status_code == 404:
        raise _compra_invalida("a App Store não reconhece esta transação")
    if resposta.status_code >= 400:
        raise HTTPException(status_code=502, detail="App Store indisponível para validar a compra")

    dados = _payload_jws(resposta.json().get("signedTransactionInfo", ""))

    bundle_esperado = os.getenv("APPLE_BUNDLE_ID", "com.agentcicle.app")
    if dados.get("bundleId") != bundle_esperado:
        raise _compra_invalida("compra é de outro aplicativo")

    if dados.get("revocationDate"):
        raise _compra_invalida("compra estornada")

    expira_em = _data_ms(dados.get("expiresDate"))
    if expira_em and expira_em < datetime.now(timezone.utc):
        raise _compra_invalida("assinatura expirada")

    product_id = dados.get("productId", "")
    duracao_meses = _meses_do_produto(product_id)

    # originalTransactionId é estável entre renovações: amarra a assinatura a
    # uma conta e impede o mesmo pagamento valer em duas.
    id_transacao = str(
        dados.get("originalTransactionId") or dados.get("transactionId") or token_compra
    )

    return CompraValidada("ios", id_transacao, product_id, duracao_meses, expira_em)


# -------------------------------------------------------------------- comuns
def _data_iso(valor) -> Optional[datetime]:
    if not valor:
        return None
    try:
        return datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except ValueError:
        return None


def _data_ms(valor) -> Optional[datetime]:
    if not valor:
        return None
    try:
        return datetime.fromtimestamp(int(valor) / 1000, tz=timezone.utc)
    except (TypeError, ValueError):
        return None


def validar_compra(plataforma: Plataforma, token_compra: str) -> CompraValidada:
    """
    Confirma junto à loja que a compra existe, é válida e pertence a este app.

    Levanta HTTPException em qualquer dúvida: sem confirmação da loja, nenhuma
    assinatura é ativada.
    """
    if not token_compra:
        raise _compra_invalida("token vazio")

    if plataforma == "android":
        return _validar_android(token_compra)
    if plataforma == "ios":
        return _validar_ios(token_compra)

    raise HTTPException(status_code=400, detail="Plataforma inválida")
