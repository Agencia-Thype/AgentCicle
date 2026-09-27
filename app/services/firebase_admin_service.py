import json
import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials

_FIREBASE_APP = None


def get_firebase_app() -> firebase_admin.App:
    global _FIREBASE_APP
    if _FIREBASE_APP is not None:
        return _FIREBASE_APP

    service_account_file = os.getenv("FIREBASE_SERVICE_ACCOUNT_FILE")
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")

    if service_account_file:
        caminho = Path(service_account_file)
        if not caminho.is_absolute():
            caminho = Path(__file__).resolve().parents[2] / caminho
        if not caminho.is_file():
            raise RuntimeError(
                f"Arquivo da conta de serviço do Firebase não encontrado: {caminho}"
            )
        cred = credentials.Certificate(str(caminho))
    elif service_account_json:
        cred = credentials.Certificate(json.loads(service_account_json))
    else:
        raise RuntimeError(
            "Credencial Firebase não configurada. Defina FIREBASE_SERVICE_ACCOUNT_FILE "
            "com o caminho do arquivo local ou FIREBASE_SERVICE_ACCOUNT_JSON com o "
            "conteúdo do JSON da conta de serviço."
        )

    # Sem isto a SDK espera até 120 s (com novas tentativas) por resposta do
    # Google: a exclusão de conta estourava o timeout do app e a usuária via
    # erro mesmo com a conta já apagada.
    _FIREBASE_APP = firebase_admin.initialize_app(
        cred, {"httpTimeout": int(os.getenv("FIREBASE_HTTP_TIMEOUT_SECONDS", "10"))}
    )
    return _FIREBASE_APP
