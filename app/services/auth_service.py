from datetime import datetime, timedelta, timezone
import os
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
from dotenv import load_dotenv
load_dotenv()

# Configurações de JWT e criptografia
SECRET_KEY = os.getenv("SECRET_KEY", "supersegredo123")
ALGORITHM = "HS256"
EXPIRA_MINUTOS = 60
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Autenticação do token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

def criar_token_jwt(email: str):
    expira = datetime.now(timezone.utc) + timedelta(minutes=EXPIRA_MINUTOS)
    payload = {"sub": email, "exp": expira}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

def hash_senha(senha: str):
    # Limitar senha para evitar problemas com bcrypt (max 72 bytes)
    senha_limitada = senha[:72]
    return pwd_context.hash(senha_limitada)

def verificar_senha(senha: str, senha_hash: str):
    return pwd_context.verify(senha, senha_hash)

def gerar_codigo_validacao():
    return str(random.randint(100000, 999999))

def verificar_token(token: str = Depends(oauth2_scheme)):
    try:
        print(f"🔐 Verificando token: {token[:15]}...")  # Mostra apenas parte do token para segurança
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            print("❌ Token decodificado, mas não contém campo 'sub'")
            raise HTTPException(status_code=401, detail="Token inválido (sem email)")
        print(f"✅ Token válido para: {email}")
        return email
    except JWTError as e:
        print(f"❌ Erro ao decodificar token: {str(e)}")
        raise HTTPException(status_code=401, detail=f"Token inválido: {str(e)}")
    except Exception as e:
        print(f"❌ Erro inesperado ao verificar token: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar token: {str(e)}")

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

    if usuario.validade_codigo and datetime.now(timezone.utc) > usuario.validade_codigo:
        raise HTTPException(status_code=400, detail="O código expirou. Solicite um novo.")

    if usuario.codigo_validacao != request.codigo:
        usuario.tentativas_codigo += 1
        db.commit()
        raise HTTPException(status_code=400, detail="Código inválido.")

    # Validar requisitos de senha
    if request.nova_senha != request.confirmacao_senha:
        raise HTTPException(status_code=400, detail="As senhas não conferem")
    
    # Atualize a senha
    usuario.senha_hash = hash_senha(request.nova_senha)
    usuario.codigo_validacao = None
    usuario.validade_codigo = None
    usuario.tentativas_codigo = 0

    db.commit()
    return {"mensagem": "Senha alterada com sucesso!"}
