import os
import socket

_getaddrinfo_original = socket.getaddrinfo


def _getaddrinfo_ipv4(host, port, family=0, *args, **kwargs):
    if family == socket.AF_UNSPEC:
        family = socket.AF_INET
    return _getaddrinfo_original(host, port, family, *args, **kwargs)


def preferir_ipv4() -> None:
    """
    Faz as conexões de saída do processo resolverem só endereços IPv4.

    Na VPS o IPv6 tem endereço e rota, mas a conexão TCP de saída não completa.
    Como o Python tenta os endereços IPv6 primeiro, buscar os certificados do
    Google para validar o token do Firebase gastava o timeout inteiro em cada um
    dos 8 endereços (8 x 10 s) antes de cair no IPv4: quem abria o app com o
    cache de certificados vencido esperava ~80 s em todas as rotas.

    Vale para requests/urllib3 (Firebase, lojas) e httpx (OpenAI). Quem pede
    uma família explícita não é afetado. Desligue com FORCAR_IPV4=false.
    """
    if os.getenv("FORCAR_IPV4", "true").lower() in ("0", "false", "no", "nao", "não"):
        return
    socket.getaddrinfo = _getaddrinfo_ipv4
