from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.database import get_db
from app.models.sqlalchemy_models import Usuario
from app.schemas.usuario_schemas import (
    UsuarioRegister, UsuarioLogin, ValidarEmailRequest, TokenResponse
)
from app.services.auth_service import (
    criar_token_jwt, hash_senha, verificar_senha,
    gerar_codigo_validacao, verificar_token
)

router = APIRouter(tags=["Autenticação"])


@router.post("/register")
def registrar(usuario: UsuarioRegister, db: Session = Depends(get_db)):
    # Verifica se já existe usuária com o mesmo e-mail
    if db.query(Usuario).filter(Usuario.email == usuario.email).first():
        raise HTTPException(status_code=400, detail="E-mail já cadastrado")

    if usuario.senha != usuario.confirmacao_senha:
        raise HTTPException(status_code=400, detail="Senhas não conferem")

    senha_hash = hash_senha(usuario.senha)
    codigo = gerar_codigo_validacao()

    nova_usuario = Usuario(
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=senha_hash,
        verificado=0,
        codigo_validacao=codigo,
        data_criacao=datetime.utcnow()
    )

    db.add(nova_usuario)
    db.commit()

    print(f"[EMAIL SIMULADO] Código de verificação para {usuario.email}: {codigo}")
    return {"mensagem": "Usuária registrada. Verifique seu e-mail com o código enviado."}


@router.post("/validar-email")
def validar_email(req: ValidarEmailRequest, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    if user.codigo_validacao != req.codigo:
        raise HTTPException(status_code=400, detail="Código inválido")

    user.verificado = 1
    db.commit()
    return {"mensagem": "E-mail verificado com sucesso!"}


@router.post("/login", response_model=TokenResponse)
def login(usuario: UsuarioLogin, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    if not verificar_senha(usuario.senha, user.senha_hash):
        raise HTTPException(status_code=401, detail="Senha incorreta")

    if not user.verificado:
        raise HTTPException(status_code=403, detail="E-mail não verificado")

    token = criar_token_jwt(user.email)
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def get_usuario_logado(email: str = Depends(verificar_token), db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    return {
        "nome": user.nome,
        "email": user.email,
        "verificado": bool(user.verificado)
    }
