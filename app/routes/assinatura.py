from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta

from app.db.database import get_db
from app.services.auth_service import verificar_token
from app.models.sqlalchemy_models import Usuario
from app.services.assinatura_service import verificar_status_usuario, ativar_assinatura, cancelar_assinatura

router = APIRouter(prefix="/assinatura", tags=["Assinatura"])

@router.get("/status")
def get_status_assinatura(
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    """
    Retorna o status da assinatura do usuário.
    """
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    status = verificar_status_usuario(db, usuario.id)
    
    # Adiciona mensagem informativa sobre o período de teste
    if status["trialAtivo"]:
        status["mensagem"] = f"Você está no período de testes gratuito. Restam {status['diasRestantesTrial']} dias."
    elif status["assinaturaAtiva"]:
        status["mensagem"] = "Você possui uma assinatura ativa. Aproveite todos os recursos!"
    else:
        status["mensagem"] = "O período de testes expirou. Assine agora para continuar usando o app."
    
    # Adiciona informações sobre a conta
    status["nome"] = usuario.nome
    status["email"] = usuario.email
    if usuario.data_fim_trial:
        status["dataFimTrial"] = usuario.data_fim_trial.isoformat()
    if usuario.data_fim_assinatura:
        status["dataFimAssinatura"] = usuario.data_fim_assinatura.isoformat()
    
    return status


@router.post("/ativar")
def ativar_plano(
    duracao_meses: int = 1,
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    """
    Endpoint para ativar a assinatura (simulação, sem integração com pagamentos reais).
    """
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    resultado = ativar_assinatura(db, usuario.id, duracao_meses)
    
    return {
        "mensagem": f"Assinatura ativada com sucesso por {duracao_meses} meses!",
        "status": resultado
    }


@router.post("/cancelar")
def cancelar_plano(
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    """
    Endpoint para cancelar a assinatura.
    """
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    resultado = cancelar_assinatura(db, usuario.id)
    
    return {
        "mensagem": "Assinatura cancelada com sucesso.",
        "status": resultado
    }
