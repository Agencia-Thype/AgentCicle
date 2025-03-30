from datetime import datetime, timedelta
from jose import jwt
from jose.exceptions import JWTError
from passlib.context import CryptContext
import random
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer


SECRET_KEY = "supersegredo123"
ALGORITHM = "HS256"
EXPIRA_MINUTOS = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# "Banco fake" por enquanto
usuarios_fake_db = {}

def criar_token_jwt(email: str):
    expira = datetime.utcnow() + timedelta(minutes=EXPIRA_MINUTOS)
    payload = {"sub": email, "exp": expira}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

def hash_senha(senha: str):
    return pwd_context.hash(senha)

def verificar_senha(senha: str, senha_hash: str):
    return pwd_context.verify(senha, senha_hash)

def gerar_codigo_validacao():
    return str(random.randint(100000, 999999))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def verificar_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")
