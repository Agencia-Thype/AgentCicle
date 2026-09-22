"""
Notificações das lojas (App Store Server Notifications v2 / Google Play RTDN).

Renovação, cancelamento, reembolso e falha de pagamento acontecem fora do app:
ninguém abre o Cíclica para avisar que cancelou. Sem isto, uma assinatura
cancelada continuaria valendo até a data que gravamos na compra.

Segurança: o corpo da notificação não é fonte de verdade. Dele sai apenas o
identificador da compra; o estado é reconsultado na loja pelo pagamento_service,
que fala direto com a Apple ou o Google por TLS. Assim uma notificação forjada
não libera nem tira o premium de ninguém - no máximo provoca uma consulta.
"""

import json
from base64 import b64decode
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.sqlalchemy_models import CompraLoja, Usuario
from app.services.assinatura_service import cancelar_assinatura
from app.services.pagamento_service import _payload_jws, validar_compra
from app.utils.cache import invalidate_cache


def _compra_registrada(db: Session, token: str) -> CompraLoja | None:
    """A compra guardada na ativação, pelo token da loja ou pelo id da transação."""
    return (
        db.query(CompraLoja)
        .filter((CompraLoja.token_compra == token) | (CompraLoja.id_transacao == token))
        .order_by(CompraLoja.id.desc())
        .first()
    )


def _renovar(db: Session, registro: CompraLoja, expira_em: datetime | None, meses: int) -> None:
    """Estende a assinatura até a data que a loja informa."""
    usuario = db.query(Usuario).filter(Usuario.id == registro.usuario_id).first()
    if not usuario:
        return

    usuario.assinatura_ativa = 1
    # A data vem da loja quando existe: é ela que sabe quando a cobrança cai.
    usuario.data_fim_assinatura = expira_em or datetime.now() + timedelta(days=30 * meses)
    if usuario.data_inicio_assinatura is None:
        usuario.data_inicio_assinatura = datetime.now()

    registro.expira_em = expira_em
    db.commit()
    invalidate_cache(f"status_usuario_{usuario.id}")


def _aplicar(db: Session, plataforma: str, token: str) -> dict:
    """
    Reconsulta a compra na loja e acerta a assinatura conforme a resposta.

    Compra que a loja não reconhece mais, estornada ou vencida derruba o
    premium; compra válida estende até a nova data.
    """
    if not token:
        return {"resultado": "ignorado", "motivo": "notificação sem token"}

    registro = _compra_registrada(db, token)
    if not registro:
        # Compra de outro ambiente ou anterior à integração: não há usuário a
        # quem aplicar. Responder ok evita a loja reenviar para sempre.
        return {"resultado": "ignorado", "motivo": "compra não registrada"}

    try:
        compra = validar_compra(plataforma, token)
    except HTTPException as erro:
        if erro.status_code >= 500:
            # Loja fora do ar: deixa a notificação ser reenviada mais tarde em
            # vez de cancelar a assinatura de quem está pagando.
            raise
        cancelar_assinatura(db, registro.usuario_id)
        return {"resultado": "cancelada", "usuario_id": registro.usuario_id}

    _renovar(db, registro, compra.expira_em, compra.duracao_meses)
    return {"resultado": "renovada", "usuario_id": registro.usuario_id}


def processar_apple(db: Session, corpo: dict) -> dict:
    """
    Notificação v2 da App Store: um JWS com a transação dentro.

    Só o transactionId é aproveitado; o resto é confirmado com a Apple.
    """
    assinado = corpo.get("signedPayload")
    if not assinado:
        raise HTTPException(status_code=400, detail="Notificação sem signedPayload")

    payload = _payload_jws(assinado)
    dados = payload.get("data") or {}
    transacao = {}
    if dados.get("signedTransactionInfo"):
        transacao = _payload_jws(dados["signedTransactionInfo"])

    token = str(transacao.get("transactionId") or transacao.get("originalTransactionId") or "")
    resultado = _aplicar(db, "ios", token)
    resultado["notificacao"] = payload.get("notificationType")
    return resultado


def processar_google(db: Session, corpo: dict) -> dict:
    """
    Notificação RTDN da Google Play, que chega embrulhada em uma mensagem do
    Pub/Sub: o conteúdo vem em base64 no campo `message.data`.
    """
    dados_base64 = (corpo.get("message") or {}).get("data")
    if not dados_base64:
        raise HTTPException(status_code=400, detail="Notificação sem message.data")

    try:
        conteudo = json.loads(b64decode(dados_base64))
    except (ValueError, TypeError) as erro:
        raise HTTPException(status_code=400, detail="Notificação ilegível") from erro

    aviso = conteudo.get("subscriptionNotification") or {}
    token = aviso.get("purchaseToken", "")

    # Mensagem de teste do console do Google: não tem compra nenhuma.
    if conteudo.get("testNotification"):
        return {"resultado": "ignorado", "motivo": "notificação de teste"}

    resultado = _aplicar(db, "android", token)
    resultado["notificacao"] = aviso.get("notificationType")
    return resultado
