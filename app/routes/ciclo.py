# app/routes/ciclo.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from app.db.database import get_db
from app.services.auth_service import verificar_token
from app.models.sqlalchemy_models import Usuario
from app.schemas.usuario_schemas import PerfilUsuario

router = APIRouter(tags=["Ciclo"])

FASES_CICLO = [
    ("menstruacao", 5),
    ("folicular", 7),
    ("ovulacao", 5),
    ("lutea", 11)
]

def calcular_fase(data_menstruacao: date, hoje: date = date.today()) -> str:
    dias_passados = (hoje - data_menstruacao).days % 28
    contador = 0
    for fase, duracao in FASES_CICLO:
        contador += duracao
        if dias_passados < contador:
            return fase
    return "menstruacao"  # fallback

@router.post("/fase-ciclo")
def detectar_fase_ciclo(
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario or not usuario.data_menstruacao:
        raise HTTPException(status_code=400, detail="Usuária sem data de menstruação registrada")

    fase = calcular_fase(usuario.data_menstruacao)
    return {
        "fase": fase,
        "data_menstruacao": usuario.data_menstruacao.strftime("%Y-%m-%d")
    }
