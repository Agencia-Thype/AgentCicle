"""
Testes da validação de compras das lojas.

O que importa aqui é o que NÃO passa: sem confirmação da loja, sem produto
conhecido ou com recibo de outra conta, nenhuma assinatura é ativada.
"""
import json
from base64 import urlsafe_b64encode
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.sqlalchemy_models import CompraLoja, Usuario
from app.services import pagamento_service
from app.services.pagamento_service import produtos_assinatura, validar_compra


class RespostaFalsa:
    """Resposta HTTP mínima no formato que o requests devolve."""

    def __init__(self, status_code: int, corpo: dict | None = None):
        self.status_code = status_code
        self._corpo = corpo or {}

    def json(self) -> dict:
        return self._corpo


def _limpar_configuracao(monkeypatch):
    for variavel in (
        "GOOGLE_PLAY_SERVICE_ACCOUNT",
        "GOOGLE_PLAY_SERVICE_ACCOUNT_JSON",
        "APPLE_ISSUER_ID",
        "APPLE_KEY_ID",
        "APPLE_PRIVATE_KEY",
        "APPLE_PRIVATE_KEY_PATH",
        "PRODUTOS_ASSINATURA",
    ):
        monkeypatch.delenv(variavel, raising=False)


def _jws(payload: dict) -> str:
    """JWS no formato da Apple. Só o corpo importa: a origem é a própria API."""
    corpo = urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"cabecalho.{corpo}.assinatura"


def _transacao_apple(**campos) -> dict:
    base = {
        "bundleId": "com.agentcicle.app",
        "productId": "ciclica_premium_mensal",
        "originalTransactionId": "1000000000000001",
        "expiresDate": int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp() * 1000),
    }
    base.update(campos)
    return base


class TestEntradasInvalidas:
    """Nada de chamar a loja com lixo"""

    def test_token_vazio(self):
        with pytest.raises(HTTPException) as erro:
            validar_compra("ios", "")
        assert erro.value.status_code == 400

    def test_plataforma_invalida(self):
        with pytest.raises(HTTPException) as erro:
            validar_compra("web", "recibo")  # type: ignore[arg-type]
        assert erro.value.status_code == 400


class TestFalhaFechado:
    """Sem credenciais, a validação recusa - nunca libera"""

    def test_android_sem_configuracao(self, monkeypatch):
        _limpar_configuracao(monkeypatch)
        with pytest.raises(HTTPException) as erro:
            validar_compra("android", "token-qualquer")
        assert erro.value.status_code == 503

    def test_ios_sem_configuracao(self, monkeypatch):
        _limpar_configuracao(monkeypatch)
        with pytest.raises(HTTPException) as erro:
            validar_compra("ios", "1000000000000001")
        assert erro.value.status_code == 503


class TestGooglePlay:
    """Validação de assinatura no Android"""

    @pytest.fixture(autouse=True)
    def _credenciais(self, monkeypatch):
        _limpar_configuracao(monkeypatch)
        monkeypatch.setattr(pagamento_service, "_token_google", lambda: "token-de-acesso")

    def _responder(self, monkeypatch, corpo: dict, status: int = 200):
        monkeypatch.setattr(
            pagamento_service.requests, "get", lambda *a, **k: RespostaFalsa(status, corpo)
        )
        monkeypatch.setattr(pagamento_service.requests, "post", lambda *a, **k: RespostaFalsa(200))

    def test_assinatura_ativa_e_aceita(self, monkeypatch):
        self._responder(monkeypatch, {
            "subscriptionState": "SUBSCRIPTION_STATE_ACTIVE",
            "latestOrderId": "GPA.3300-0000-0000-00000",
            "lineItems": [{
                "productId": "ciclica_premium_mensal",
                "expiryTime": "2026-12-01T10:00:00Z",
            }],
        })

        compra = validar_compra("android", "token-da-compra")

        assert compra.plataforma == "android"
        assert compra.id_transacao == "GPA.3300-0000-0000-00000"
        assert compra.duracao_meses == 1
        assert compra.expira_em.year == 2026

    def test_plano_anual_da_doze_meses(self, monkeypatch):
        self._responder(monkeypatch, {
            "subscriptionState": "SUBSCRIPTION_STATE_ACTIVE",
            "latestOrderId": "GPA.1111",
            "lineItems": [{"productId": "ciclica_premium_anual"}],
        })

        assert validar_compra("android", "token").duracao_meses == 12

    def test_assinatura_cancelada_recusada(self, monkeypatch):
        self._responder(monkeypatch, {
            "subscriptionState": "SUBSCRIPTION_STATE_CANCELED",
            "lineItems": [{"productId": "ciclica_premium_mensal"}],
        })

        with pytest.raises(HTTPException) as erro:
            validar_compra("android", "token")
        assert erro.value.status_code == 400

    def test_produto_desconhecido_recusado(self, monkeypatch):
        self._responder(monkeypatch, {
            "subscriptionState": "SUBSCRIPTION_STATE_ACTIVE",
            "latestOrderId": "GPA.2222",
            "lineItems": [{"productId": "produto_de_outro_app"}],
        })

        with pytest.raises(HTTPException) as erro:
            validar_compra("android", "token")
        assert erro.value.status_code == 400

    def test_token_desconhecido_pela_loja(self, monkeypatch):
        self._responder(monkeypatch, {}, status=404)

        with pytest.raises(HTTPException) as erro:
            validar_compra("android", "token-inventado")
        assert erro.value.status_code == 400

    def test_loja_fora_do_ar(self, monkeypatch):
        self._responder(monkeypatch, {}, status=500)

        with pytest.raises(HTTPException) as erro:
            validar_compra("android", "token")
        assert erro.value.status_code == 502


class TestAppStore:
    """Validação de transação no iOS"""

    @pytest.fixture(autouse=True)
    def _credenciais(self, monkeypatch):
        _limpar_configuracao(monkeypatch)
        monkeypatch.setattr(pagamento_service, "_token_apple", lambda: "jwt-falso")

    def _responder(self, monkeypatch, transacao: dict, status: int = 200):
        corpo = {"signedTransactionInfo": _jws(transacao)}
        monkeypatch.setattr(
            pagamento_service.requests, "get", lambda *a, **k: RespostaFalsa(status, corpo)
        )

    def test_transacao_valida_e_aceita(self, monkeypatch):
        self._responder(monkeypatch, _transacao_apple())

        compra = validar_compra("ios", "1000000000000001")

        assert compra.plataforma == "ios"
        assert compra.id_transacao == "1000000000000001"
        assert compra.duracao_meses == 1

    def test_compra_de_outro_app_recusada(self, monkeypatch):
        self._responder(monkeypatch, _transacao_apple(bundleId="com.outro.app"))

        with pytest.raises(HTTPException) as erro:
            validar_compra("ios", "1000000000000001")
        assert erro.value.status_code == 400

    def test_compra_estornada_recusada(self, monkeypatch):
        self._responder(monkeypatch, _transacao_apple(revocationDate=1735689600000))

        with pytest.raises(HTTPException) as erro:
            validar_compra("ios", "1000000000000001")
        assert erro.value.status_code == 400

    def test_assinatura_expirada_recusada(self, monkeypatch):
        vencida = int((datetime.now(timezone.utc) - timedelta(days=1)).timestamp() * 1000)
        self._responder(monkeypatch, _transacao_apple(expiresDate=vencida))

        with pytest.raises(HTTPException) as erro:
            validar_compra("ios", "1000000000000001")
        assert erro.value.status_code == 400

    def test_transacao_desconhecida(self, monkeypatch):
        self._responder(monkeypatch, {}, status=404)

        with pytest.raises(HTTPException) as erro:
            validar_compra("ios", "0000")
        assert erro.value.status_code == 400


class TestProdutos:
    """Catálogo de produtos configurável"""

    def test_padrao_tem_mensal_e_anual(self, monkeypatch):
        monkeypatch.delenv("PRODUTOS_ASSINATURA", raising=False)
        produtos = produtos_assinatura()
        assert produtos["ciclica_premium_mensal"] == 1
        assert produtos["ciclica_premium_anual"] == 12

    def test_lido_do_ambiente(self, monkeypatch):
        monkeypatch.setenv("PRODUTOS_ASSINATURA", "plano_teste:2, plano_longo:24")
        produtos = produtos_assinatura()
        assert produtos == {"plano_teste": 2, "plano_longo": 24}

    def test_valor_quebrado_cai_no_padrao(self, monkeypatch):
        monkeypatch.setenv("PRODUTOS_ASSINATURA", "sem_meses")
        assert produtos_assinatura() == pagamento_service.PRODUTOS_PADRAO


class TestAtivacaoPelaRota:
    """/assinatura/ativar só grava depois da loja confirmar"""

    def _compra(self, id_transacao="GPA.9999"):
        return pagamento_service.CompraValidada(
            plataforma="android",
            id_transacao=id_transacao,
            product_id="ciclica_premium_mensal",
            duracao_meses=1,
        )

    def test_compra_validada_ativa_e_fica_registrada(
        self, client: TestClient, headers_auth: dict, db: Session, usuario_teste, monkeypatch
    ):
        monkeypatch.setenv("COBRANCA_ATIVA", "true")
        monkeypatch.setattr(
            "app.routes.assinatura.validar_compra", lambda *a, **k: self._compra()
        )

        response = client.post(
            "/assinatura/ativar",
            headers=headers_auth,
            json={"plataforma": "android", "token_compra": "token-bom"},
        )

        assert response.status_code == 200
        db.refresh(usuario_teste)
        assert usuario_teste.assinatura_ativa == 1

        registro = db.query(CompraLoja).filter(CompraLoja.id_transacao == "GPA.9999").first()
        assert registro is not None
        assert registro.usuario_id == usuario_teste.id

    def test_recibo_de_outra_conta_recusado(
        self, client: TestClient, headers_auth: dict, db: Session, usuario_teste, monkeypatch
    ):
        """O recibo é de quem comprou: reenviá-lo em outra conta não vale."""
        outra = Usuario(nome="Outra", email="outra@example.com", verificado=1)
        db.add(outra)
        db.commit()
        db.refresh(outra)

        db.add(CompraLoja(
            usuario_id=outra.id,
            plataforma="android",
            id_transacao="GPA.9999",
            product_id="ciclica_premium_mensal",
            duracao_meses=1,
            created_at=datetime.now(),
        ))
        db.commit()

        monkeypatch.setenv("COBRANCA_ATIVA", "true")
        monkeypatch.setattr(
            "app.routes.assinatura.validar_compra", lambda *a, **k: self._compra()
        )

        response = client.post(
            "/assinatura/ativar",
            headers=headers_auth,
            json={"plataforma": "android", "token_compra": "token-roubado"},
        )

        assert response.status_code == 409
        db.refresh(usuario_teste)
        assert not usuario_teste.assinatura_ativa

    def test_dono_pode_reenviar_a_propria_compra(
        self, client: TestClient, headers_auth: dict, db: Session, usuario_teste, monkeypatch
    ):
        """O app reprocessa pendências: o mesmo recibo do dono não pode falhar."""
        monkeypatch.setenv("COBRANCA_ATIVA", "true")
        monkeypatch.setattr(
            "app.routes.assinatura.validar_compra", lambda *a, **k: self._compra()
        )
        corpo = {"plataforma": "android", "token_compra": "token-bom"}

        assert client.post("/assinatura/ativar", headers=headers_auth, json=corpo).status_code == 200
        assert client.post("/assinatura/ativar", headers=headers_auth, json=corpo).status_code == 200

        registros = db.query(CompraLoja).filter(CompraLoja.id_transacao == "GPA.9999").count()
        assert registros == 1
