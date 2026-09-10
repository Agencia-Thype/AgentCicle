import json
import os

import firebase_admin
from firebase_admin import credentials

_FIREBASE_APP = None


def get_firebase_app() -> firebase_admin.App:
    global _FIREBASE_APP
    if _FIREBASE_APP is not None:
        return _FIREBASE_APP

    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if not service_account_json:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT_JSON não configurada. Defina a variável de "
            "ambiente com o conteúdo do JSON da service account (Firebase Console "
            "-> Project Settings -> Service accounts -> Generate new private key)."
        )

    cred = credentials.Certificate(json.loads(service_account_json))
    _FIREBASE_APP = firebase_admin.initialize_app(cred)
    return _FIREBASE_APP
