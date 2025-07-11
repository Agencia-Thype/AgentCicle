from fastapi import Body
from fastapi import APIRouter, HTTPException, Depends
from app.routes.usuario import redefinir_senha
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.db.database import get_db
from app.models.sqlalchemy_models import Usuario
from app.schemas.usuario_schemas import (
    RedefinirSenhaRequest, UsuarioRegister, UsuarioLogin, ValidarEmailRequest, TokenResponse
)
from app.services.auth_service import (
    criar_token_jwt, hash_senha, verificar_senha,
    gerar_codigo_validacao, verificar_token
)
from app.services.assinatura_service import obter_status_login

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
    
    # Definir validade do código (24 horas)
    validade = datetime.now(timezone.utc) + timedelta(hours=24)

    nova_usuario = Usuario(
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=senha_hash,
        verificado=0,
        codigo_validacao=codigo,
        validade_codigo=validade,
        data_criacao=datetime.now(timezone.utc)

    )

    db.add(nova_usuario)
    db.commit()

    # Enviar email de verificação
    from app.services.email_service import enviar_email_verificacao
    enviar_email_verificacao(usuario.email, codigo)
    
    return {"mensagem": "Usuária registrada. Verifique seu e-mail com o código enviado."}


@router.post("/validar-email")
def validar_email(req: ValidarEmailRequest, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.email == req.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    if user.codigo_validacao != req.codigo:
        raise HTTPException(status_code=400, detail="Código inválido")

    user.verificado = 1
    
    # Ativar trial de 7 dias após validação do email
    if not user.data_fim_trial:
        hoje = datetime.now(timezone.utc)
        user.data_criacao_conta = hoje
        user.data_fim_trial = hoje + timedelta(days=7)
    
    db.commit()
    return {"mensagem": "E-mail verificado com sucesso! Seu período de teste gratuito de 7 dias foi ativado."}


@router.post("/login")
def login(usuario: UsuarioLogin, db: Session = Depends(get_db)):
    print(f"🔑 Tentativa de login para email: {usuario.email}")
    try:
        user = db.query(Usuario).filter(Usuario.email == usuario.email).first()
        if not user:
            print(f"❌ Usuária não encontrada: {usuario.email}")
            raise HTTPException(status_code=404, detail="Usuária não encontrada")

        if not verificar_senha(usuario.senha, user.senha_hash):
            print(f"❌ Senha incorreta para: {usuario.email}")
            raise HTTPException(status_code=401, detail="Senha incorreta")

        if not user.verificado:
            print(f"❌ E-mail não verificado: {usuario.email}")
            raise HTTPException(status_code=403, detail="E-mail não verificado")

        # Gerar token JWT
        token = criar_token_jwt(user.email)
        
        # Obter status completo do usuário para o frontend armazenar
        status_assinatura = obter_status_login(db, user.id)
        
        print(f"✅ Login bem-sucedido para: {usuario.email}")
        return {
            "access_token": token, 
            "token_type": "bearer",
            "usuario": {
                "id": user.id,
                "nome": user.nome,
                "email": user.email
            },
            "assinatura": status_assinatura
        }
    except HTTPException:
        # Repassar exceções HTTP normalmente
        raise
    except Exception as e:
        print(f"❌ Erro inesperado no login: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro no login: {str(e)}")


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

@router.post("/redefinir-senha")
def redefinir_senha_endpoint(req: RedefinirSenhaRequest, db: Session = Depends(get_db)):
    return redefinir_senha(req, db)

@router.post("/solicitar-redefinicao-senha")
def solicitar_redefinicao_senha(email: str = Body(..., embed=True), db: Session = Depends(get_db)):
    """Endpoint para solicitar redefinição de senha"""
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        # Por segurança, não revelamos se o email existe ou não
        return {"mensagem": "Se o email estiver cadastrado, enviaremos um código de redefinição."}
      # Gerar novo código e definir validade (30 minutos)
    codigo = gerar_codigo_validacao()
    validade = datetime.now(timezone.utc) + timedelta(minutes=30)
    
    # Atualizar usuário
    usuario.codigo_validacao = codigo
    usuario.validade_codigo = validade
    usuario.tentativas_codigo = 0
    db.commit()
    
    # Enviar email
    from app.services.email_service import enviar_email_redefinicao
    enviar_email_redefinicao(email, codigo)
    
    return {"mensagem": "Se o email estiver cadastrado, enviaremos um código de redefinição."}

@router.post("/teste/ativar-premium")
async def ativar_premium_teste(email: str = Body(..., embed=True), duracao_meses: int = Body(1, embed=True), db: Session = Depends(get_db)):
    """
    SOMENTE PARA TESTES - Ativa a assinatura premium para um usuário
    
    Args:
        email: Email do usuário
        duracao_meses: Duração da assinatura em meses
        
    Returns:
        Status da assinatura atualizado
    """
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Importar o serviço de assinatura
    from app.services.assinatura_service import ativar_assinatura
    
    # Ativar assinatura
    resultado = ativar_assinatura(db, usuario.id, duracao_meses)
    
    return {
        "mensagem": f"Assinatura premium ativada para {usuario.nome} por {duracao_meses} {'mês' if duracao_meses == 1 else 'meses'}",
        "status_assinatura": resultado
    }

@router.post("/teste/cancelar-premium")
async def cancelar_premium_teste(email: str = Body(..., embed=True), db: Session = Depends(get_db)):
    """
    SOMENTE PARA TESTES - Cancela a assinatura premium de um usuário
    
    Args:
        email: Email do usuário
        
    Returns:
        Status da assinatura atualizado
    """
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Importar o serviço de assinatura
    from app.services.assinatura_service import cancelar_assinatura
    
    # Cancelar assinatura
    resultado = cancelar_assinatura(db, usuario.id)
    
    return {
        "mensagem": f"Assinatura premium cancelada para {usuario.nome}",
        "status_assinatura": resultado
    }

@router.get("/teste/status-assinatura")
async def verificar_status_assinatura_teste(email: str = None, db: Session = Depends(get_db)):
    """
    SOMENTE PARA TESTES - Verifica o status de assinatura de um usuário
    
    Args:
        email: Email do usuário
        
    Returns:
        Status da assinatura
    """
    print(f"🔍 Verificando status de assinatura para email: {email}")
    
    if not email:
        return {"erro": "Email não fornecido", "exemplo": "Use /teste/status-assinatura?email=seu@email.com"}
    
    try:
        usuario = db.query(Usuario).filter(Usuario.email == email).first()
        if not usuario:
            print(f"❌ Usuário não encontrado com email: {email}")
            # Verificar se existem usuários no sistema
            count = db.query(Usuario).count()
            return {
                "erro": "Usuário não encontrado",
                "email_buscado": email,
                "total_usuarios_cadastrados": count,
                "dica": "Verifique se o email existe ou use outros endpoints de teste"
            }
        
        # Importar o serviço de assinatura
        from app.services.assinatura_service import verificar_status_usuario
        
        # Verificar status
        status = verificar_status_usuario(db, usuario.id)
        
        return {
            "nome": usuario.nome,
            "email": usuario.email,
            "status_assinatura": status,
            "data_fim_trial": usuario.data_fim_trial,
            "assinatura_ativa": bool(usuario.assinatura_ativa),
            "data_inicio_assinatura": usuario.data_inicio_assinatura,
            "data_fim_assinatura": usuario.data_fim_assinatura
        }
    except Exception as e:
        print(f"❌ Erro ao verificar status: {str(e)}")
        return {"erro": f"Erro ao processar a requisição: {str(e)}"}



