# app/routes/treino.py
from fastapi import APIRouter, Query
from app.services.treino_service import obter_treino_por_fase

router = APIRouter(prefix="/treino-dia", tags=["Treino"])

@router.get("")
def treino_do_dia(data_menstruacao: str = Query(..., description="Data da última menstruação (YYYY-MM-DD)")):
    return obter_treino_por_fase(data_menstrucao=data_menstruacao)
