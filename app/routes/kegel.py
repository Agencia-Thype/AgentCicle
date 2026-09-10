from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.services.auth_service import verificar_token
from app.services.kegel_service import (
    obter_treino_kegel,
    atualizar_nivel_kegel,
    obter_info_niveis,
    registrar_conclusao_exercicio,
    verificar_niveis_disponiveis,
    obter_status_niveis
)
from app.models.kegel_models import NivelKegel, ProgressoKegel
from app.models.sqlalchemy_models import Usuario
from pydantic import BaseModel, Field
from app.utils.acesso import verificar_acesso

router = APIRouter(prefix="/kegel", tags=["Kegel"])

class ConcluirExercicioRequest(BaseModel):
    nivel: NivelKegel
    exercicio_id: str
    percentual: float = Field(ge=0, le=100, description="Percentual de conclusão de 0 a 100")

@router.get("/treino-dia")
@verificar_acesso(recurso_premium=False, permite_trial=True)
async def treino_kegel_dia(
    nivel: Optional[NivelKegel] = None,
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    """
    Retorna o treino de Kegel do dia baseado no nível do usuário.
    Opcionalmente, pode receber um nível específico para preview.
    """
    resultado = obter_treino_kegel(db, email, nivel)
    if "erro" in resultado:
        raise HTTPException(status_code=404, detail=resultado["erro"])
    return resultado

@router.get("/niveis")
async def info_niveis_kegel(
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    """
    Retorna informações sobre os níveis de Kegel disponíveis.
    """
    return obter_info_niveis()

@router.post("/atualizar-nivel")
@verificar_acesso(recurso_premium=False, permite_trial=True)
async def atualizar_nivel(
    # Sem Body(), o FastAPI trata um parâmetro escalar como query string: o app
    # envia o nível no corpo e a rota respondia 422 mesmo autenticada.
    novo_nivel: NivelKegel = Body(...),
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    """
    Atualiza o nível de Kegel do usuário.
    """
    resultado = atualizar_nivel_kegel(db, email, novo_nivel)
    if "erro" in resultado:
        raise HTTPException(status_code=404, detail=resultado["erro"])
    return resultado

@router.post("/concluir-exercicio")
@verificar_acesso(recurso_premium=False, permite_trial=True)
async def concluir_exercicio_kegel(
    dados: ConcluirExercicioRequest,
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    """
    Registra a conclusão de um exercício de Kegel.
    """
    resultado = registrar_conclusao_exercicio(
        db, email, dados.nivel, dados.exercicio_id, dados.percentual
    )
    if "erro" in resultado:
        raise HTTPException(status_code=400, detail=resultado["erro"])
    return resultado

@router.get("/status-niveis")
async def status_niveis_kegel(
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    """
    Retorna o status completo de todos os níveis de Kegel do usuário.
    """
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    niveis_status = obter_status_niveis(db, usuario.id)

    # Adicionar informações sobre desbloqueio
    niveis_disponiveis = verificar_niveis_disponiveis(
        db, usuario.id, usuario.nivel_kegel or NivelKegel.INICIANTE
    )

    # Combinar informações
    resposta = {}
    for nivel, status in niveis_status.items():
        resposta[nivel] = {
            **status,
            "bloqueado": niveis_disponiveis[nivel]["bloqueado"],
            "motivo_bloqueio": niveis_disponiveis[nivel]["motivo"]
        }

    return resposta
