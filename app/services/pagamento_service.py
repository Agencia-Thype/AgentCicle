"""
Validação de compras das lojas (App Store / Google Play).

Estado atual: o app é publicado gratuito (COBRANCA_ATIVA=false) e nada aqui é
executado. Este módulo existe para que, ao ligar a cobrança, exista um único
ponto obrigatório de validação - e para que seja impossível conceder premium
sem prova de compra, como acontecia no /assinatura/ativar original.

Como completar quando for monetizar:

  iOS   - POST para https://buy.itunes.apple.com/verifyReceipt (produção) com
          fallback para sandbox, ou a App Store Server API v2 (recomendada).
          Conferir bundle_id == com.agentcicle.app e o product_id esperado.

  Android - Google Play Developer API, purchases.subscriptionsv2.get, usando uma
          service account com acesso ao app. Conferir packageName e o estado da
          assinatura, e reconhecer a compra (acknowledge) em até 3 dias.

Regras que não podem ser afrouxadas:
  - Validar sempre no servidor. Recibo verificado no cliente não vale nada.
  - Recusar recibo já usado por outra conta (evita compartilhamento).
  - Tratar renovação, cancelamento e reembolso via notificações do servidor
    (App Store Server Notifications v2 / Google Play RTDN), não por polling.
"""

from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException

Plataforma = Literal["ios", "android"]


@dataclass(frozen=True)
class CompraValidada:
    """Resultado de uma compra confirmada pela loja."""

    plataforma: Plataforma
    id_transacao: str
    product_id: str
    duracao_meses: int


def validar_compra(plataforma: Plataforma, token_compra: str) -> CompraValidada:
    """
    Confirma junto à loja que a compra existe, é válida e pertence a este app.

    Falha fechado de propósito: enquanto a integração não estiver implementada,
    nenhuma assinatura pode ser ativada por esta via.
    """
    raise HTTPException(
        status_code=501,
        detail=(
            "Validação de compra não implementada. Integre App Store / Google "
            "Play em app/services/pagamento_service.py antes de ligar a cobrança."
        ),
    )
