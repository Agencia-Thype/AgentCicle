# app/routes/pontuacao.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from app.db.database import get_db
from app.services.auth_service import verificar_token
from app.models.sqlalchemy_models import Usuario, DiarioCiclo, TreinoRealizado

router = APIRouter(prefix="/pontuacao", tags=["Pontuação"])

@router.get("")
def get_pontuacao(
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    hoje = date.today()
    pontos = usuario.pontos_totais or 0

    # Calcular classe atual
    primeira_data = usuario.data_menstruacao
    dias_uso = (hoje - primeira_data).days if primeira_data else 0

    if dias_uso < 31:
        classe = "Lua Nova"
    elif dias_uso < 61:
        classe = "Lua Crescente"
    elif dias_uso < 91:
        classe = "Lua Cheia"
    else:
        classe = "Lua Minguante"

    dias_restantes = max(0, 30 - (dias_uso % 30))

    return {
        "pontos_mes": pontos,
        "classe": classe,
        "dias_restantes": dias_restantes
    }
