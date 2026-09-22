"""
Webhooks das lojas: renovação, cancelamento, reembolso e falha de pagamento.

Endereços para cadastrar quando a cobrança for ligada:
  App Store Connect > App > Notificações do servidor  ->  /notificacoes-loja/apple
  Google Play > Monetização > RTDN (tópico Pub/Sub)   ->  /notificacoes-loja/google

Quem chama aqui é a loja, não o app: não há usuário autenticado. A proteção é
dupla - um segredo combinado (NOTIFICACOES_LOJA_TOKEN) e, principalmente, o
fato de o conteúdo da notificação não ser acreditado: o estado da assinatura é
sempre reconsultado na loja antes de mudar qualquer coisa.
"""

import os
import secrets

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.routes.assinatura import exigir_cobranca_ativa
from app.services.notificacoes_loja_service import processar_apple, processar_google
from app.utils.logging import log_info, log_warning

router = APIRouter(prefix="/notificacoes-loja", tags=["Assinatura"])


def conferir_segredo(
    token: str | None = Query(None, description="Segredo combinado com a loja"),
    x_notificacao_token: str | None = Header(None),
):
    """
    Confere o segredo, quando configurado.

    O Pub/Sub do Google só permite acrescentar query string na URL, então o
    segredo é aceito nos dois lugares. Sem NOTIFICACOES_LOJA_TOKEN definido a
    rota fica aberta - o que é tolerável porque nada é aceito sem reconsultar a
    loja, mas configure assim que tiver o endereço público.
    """
    esperado = os.getenv("NOTIFICACOES_LOJA_TOKEN")
    if not esperado:
        return

    recebido = x_notificacao_token or token or ""
    if not secrets.compare_digest(recebido, esperado):
        raise HTTPException(status_code=401, detail="Notificação não autorizada")


@router.post("/apple", dependencies=[Depends(exigir_cobranca_ativa), Depends(conferir_segredo)])
def notificacao_apple(corpo: dict = Body(...), db: Session = Depends(get_db)):
    """Recebe uma App Store Server Notification v2."""
    resultado = processar_apple(db, corpo)
    log_info("Notificação da App Store processada", resultado)
    return resultado


@router.post("/google", dependencies=[Depends(exigir_cobranca_ativa), Depends(conferir_segredo)])
def notificacao_google(corpo: dict = Body(...), db: Session = Depends(get_db)):
    """
    Recebe uma Real-time Developer Notification da Google Play.

    Responde 200 mesmo para compra desconhecida: o Pub/Sub reenvia tudo que não
    for confirmado, e insistir numa compra que não é nossa não leva a lugar
    nenhum.
    """
    resultado = processar_google(db, corpo)
    if resultado.get("resultado") == "ignorado":
        log_warning("Notificação da Google Play ignorada", resultado)
    else:
        log_info("Notificação da Google Play processada", resultado)
    return resultado
