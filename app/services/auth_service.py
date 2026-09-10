from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from firebase_admin import auth as firebase_auth

from app.services.firebase_admin_service import get_firebase_app

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/sync")


def verificar_token(token: str = Depends(oauth2_scheme)) -> str:
    """
    Valida um ID token do Firebase e retorna o e-mail do usuário.
    Mantém o mesmo contrato de retorno (string de e-mail) que o antigo
    verificador de JWT, para não exigir mudanças nas rotas protegidas.
    """
    try:
        get_firebase_app()
        decoded = firebase_auth.verify_id_token(token)
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
