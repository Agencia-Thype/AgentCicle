from datetime import datetime, timedelta
import re
import random
from jose import jwt
from jose.exceptions import JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.models.sqlalchemy_models import Usuario
from app.schemas.usuario_schemas import RedefinirSenhaRequest

# Configurações de JWT e criptografia
SECRET_KEY = "supersegredo123"
ALGORITHM = "HS256"
EXPIRA_MINUTOS = 60
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Autenticação do token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

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

def verificar_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Token inválido")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

# Função principal de redefinição com código
MAX_TENTATIVAS = 5

def processar_redefinicao_senha(request: RedefinirSenhaRequest, db: Session):
    usuario = db.query(Usuario).filter(Usuario.email == request.email).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    if usuario.codigo_validacao is None:
        raise HTTPException(status_code=400, detail="Nenhum código foi gerado para esse usuário.")

    if usuario.tentativas_codigo >= MAX_TENTATIVAS:
        raise HTTPException(status_code=403, detail="Número máximo de tentativas excedido. Solicite um novo código.")

    if usuario.validade_codigo and datetime.utcnow() > usuario.validade_codigo:
        raise HTTPException(status_code=400, detail="O código expirou. Solicite um novo.")

    if usuario.codigo_validacao != request.codigo:
        usuario.tentativas_codigo += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Código inválido.")

    usuario.senha_hash = hash_senha(request.nova_senha)
    usuario.codigo_validacao = None
    usuario.validade_codigo = None
    usuario.tentativas_codigo = 0

    db.commit()
    return {"mensagem": "Senha alterada com sucesso!"}
