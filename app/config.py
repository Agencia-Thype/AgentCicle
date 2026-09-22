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


def dias_de_trial() -> int:
    """
    Dias de teste grátis para uma conta nova.

    Vale a partir da criação da conta; terminado o prazo, sem assinatura ativa,
    o acesso é bloqueado - mas só quando COBRANCA_ATIVA estiver ligada, porque
    no modo gratuito o fim do trial não tira o acesso de ninguém.

    Lê a variável a cada chamada, para permitir alternar em testes.
    """
    valor = os.getenv("DIAS_TRIAL")
    if valor is None:
        return 3
    try:
        dias = int(valor.strip())
    except ValueError:
        return 3
    return dias if dias > 0 else 3
