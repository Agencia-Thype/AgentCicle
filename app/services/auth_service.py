from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from firebase_admin import auth as firebase_auth
import hashlib
import os
import time

from app.services.firebase_admin_service import get_firebase_app
from app.utils.cache import get_from_cache, set_in_cache

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/sync")
TOKEN_CACHE_MAX_TTL_SECONDS = int(os.getenv("FIREBASE_TOKEN_CACHE_TTL_SECONDS", "300"))


def _cache_key_token(token: str) -> str:
    return "firebase_token:" + hashlib.sha256(token.encode("utf-8")).hexdigest()


def _cache_decoded_token(token: str, decoded: dict) -> None:
    exp = decoded.get("exp")
    ttl = TOKEN_CACHE_MAX_TTL_SECONDS
    if exp:
        ttl = min(ttl, max(0, int(exp - time.time())))
    if ttl > 0:
        set_in_cache(_cache_key_token(token), decoded, ttl)


def verificar_token(token: str = Depends(oauth2_scheme)) -> str:
    """
    Valida um ID token do Firebase e retorna o e-mail do usuário.
    Mantém o mesmo contrato de retorno (string de e-mail) que o antigo
    verificador de JWT, para não exigir mudanças nas rotas protegidas.
    """
    cached_decoded = get_from_cache(_cache_key_token(token))
    if cached_decoded:
        email = cached_decoded.get("email")
        if email:
            return email

    try:
        get_firebase_app()
        decoded = firebase_auth.verify_id_token(token)
        _cache_decoded_token(token, decoded)
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Token expirado")
    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Erro ao validar token: {str(e)}")

    email = decoded.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Token inválido (sem e-mail)")

    return email


def obter_uid_firebase(email: str) -> str:
    """Busca o UID do Firebase correspondente a um e-mail já autenticado."""
    try:
        get_firebase_app()
        return firebase_auth.get_user_by_email(email).uid
    except firebase_auth.UserNotFoundError:
        raise HTTPException(status_code=404, detail="Usuária não encontrada no Firebase")


def excluir_usuario_firebase(email: str) -> bool:
    """
    Remove a conta do usuário no Firebase Authentication.
    Retorna True se removeu, False se a conta já não existia lá.
    """
    try:
        get_firebase_app()
        uid = firebase_auth.get_user_by_email(email).uid
        firebase_auth.delete_user(uid)
        return True
    except firebase_auth.UserNotFoundError:
        return False
