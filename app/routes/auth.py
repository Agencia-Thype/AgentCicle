import os

from fastapi import Body
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.db.database import get_db
from app.models.sqlalchemy_models import Usuario
from app.schemas.usuario_schemas import AuthSyncRequest
from app.services.auth_service import verificar_token, obter_uid_firebase

router = APIRouter(tags=["Autenticação"])


def somente_desenvolvimento():
    """
    Bloqueia rotas auxiliares de teste fora do ambiente de desenvolvimento.

    Estas rotas manipulam assinatura por e-mail, sem autenticação. Expostas em
    produção, permitiriam a qualquer pessoa liberar premium de graça ou cancelar
    a assinatura de outra usuária.
    """
    if os.getenv("ENVIRONMENT", "production").lower() != "development":
        raise HTTPException(status_code=404, detail="Not Found")


@router.post("/auth/sync")
def sincronizar_usuario(
    dados: AuthSyncRequest,
    email: str = Depends(verificar_token),
    db: Session = Depends(get_db),
):
    """
    Cria (ou confirma) a linha de domínio do usuário logo após o cadastro/login
    via Firebase. Idempotente: seguro chamar em todo login, não só no primeiro.
    """
    usuario = db.query(Usuario).filter(Usuario.email == email).first()

    if usuario:
        if not usuario.firebase_uid:
            usuario.firebase_uid = obter_uid_firebase(email)
            db.commit()
        return {"mensagem": "Usuária já sincronizada", "novo": False}

    hoje = datetime.now(timezone.utc)
    usuario = Usuario(
        nome=dados.nome,
        email=email,
        firebase_uid=obter_uid_firebase(email),
        verificado=1,
        data_criacao=hoje,
        data_criacao_conta=hoje,
        data_fim_trial=hoje + timedelta(days=7),
    )
    db.add(usuario)
    db.commit()

    return {"mensagem": "Usuária criada com sucesso", "novo": True}


@router.get("/me")
def get_usuario_logado(email: str = Depends(verificar_token), db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    return {
        "nome": user.nome,
        "email": user.email,
        "verificado": bool(user.verificado),
    }


@router.post("/teste/ativar-premium", dependencies=[Depends(somente_desenvolvimento)])
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

    from app.services.assinatura_service import ativar_assinatura

    resultado = ativar_assinatura(db, usuario.id, duracao_meses)

    return {
        "mensagem": f"Assinatura premium ativada para {usuario.nome} por {duracao_meses} {'mês' if duracao_meses == 1 else 'meses'}",
        "status_assinatura": resultado
    }

@router.post("/teste/cancelar-premium", dependencies=[Depends(somente_desenvolvimento)])
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

    from app.services.assinatura_service import cancelar_assinatura

    resultado = cancelar_assinatura(db, usuario.id)

    return {
        "mensagem": f"Assinatura premium cancelada para {usuario.nome}",
        "status_assinatura": resultado
    }

@router.get("/teste/status-assinatura", dependencies=[Depends(somente_desenvolvimento)])
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
            count = db.query(Usuario).count()
            return {
                "erro": "Usuário não encontrado",
                "email_buscado": email,
                "total_usuarios_cadastrados": count,
                "dica": "Verifique se o email existe ou use outros endpoints de teste"
            }

        from app.services.assinatura_service import verificar_status_usuario

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
