"""Configurações de produto lidas do ambiente."""

import os


def _flag(nome: str, padrao: bool = False) -> bool:
    valor = os.getenv(nome)
    if valor is None:
        return padrao
    return valor.strip().lower() in ("1", "true", "yes", "on", "sim")


def cobranca_ativa() -> bool:
    """
    Indica se a monetização está ligada.

    Enquanto for False o app é totalmente gratuito: ninguém perde acesso pelo
    fim do trial e as rotas de ativação/cancelamento de assinatura ficam
    desligadas. Isso é intencional para o lançamento - um app sem paywall e sem
    menção a preço não precisa de compra in-app (App Store 3.1.1 / Google Play
    Payments). Ao ligar, a cobrança precisa passar por StoreKit / Play Billing
    com validação de recibo no servidor, nunca pelo /assinatura/ativar atual.

    Lê a variável a cada chamada de propósito, para permitir alternar em testes.
    """
    return _flag("COBRANCA_ATIVA", padrao=False)
