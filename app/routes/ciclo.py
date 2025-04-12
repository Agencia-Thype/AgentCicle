from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, timedelta
from app.db.database import get_db
from app.services.auth_service import verificar_token
from app.models.sqlalchemy_models import Usuario
from app.models.sqlalchemy_models import Usuario, DiarioCiclo
from app.schemas.ciclo_schema import RegistroMenstruacao
from app.services.ciclo_service import registrar_nova_menstruacao

router = APIRouter(tags=["Ciclo"])

FASES_CICLO = [
    ("Menstruação", 0, "Fase reflexiva 🌑"),
    ("Folicular", 0, "Fase dinâmica 🌒"),
    ("Ovulatória", 0, "Fase expansiva 🌕"),
    ("Lútea", 0, "Fase criativa 🌘")
]

@router.post("/registrar-menstruacao")
def registrar_menstruacao(
    registro: RegistroMenstruacao,
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    return registrar_nova_menstruacao(db, email, registro.data_inicio)

@router.get("/fase-ciclo")
def detectar_fase_ciclo(
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario or not usuario.data_menstruacao or not usuario.duracao_ciclo:
        raise HTTPException(status_code=400, detail="Usuária sem dados completos do ciclo")

    hoje = date.today()
    inicio_ciclo = usuario.data_menstruacao
    duracao = usuario.duracao_ciclo
    dias_passados = (hoje - inicio_ciclo).days % duracao

    # Define durações baseadas na duração do ciclo
    duracao_menstruacao = round(duracao * 0.18)  # ~5 dias
    duracao_folicular = round(duracao * 0.32)    # ~9 dias
    duracao_ovulacao = round(duracao * 0.14)     # ~4 dias
    duracao_lutea = duracao - (duracao_menstruacao + duracao_folicular + duracao_ovulacao)

    fases = [
        ("Menstruação", duracao_menstruacao, "Fase reflexiva 🌑"),
        ("Folicular", duracao_folicular, "Fase dinâmica 🌒"),
        ("Ovulatória", duracao_ovulacao, "Fase expansiva 🌕"),
        ("Lútea", duracao_lutea, "Fase criativa 🌘")
    ]

    acumulado = 0
    for nome, dur, mensagem in fases:
        if acumulado <= dias_passados < acumulado + dur:
            return {
                "fase": nome,
                "mensagem": mensagem,
                "dias_desde_menstruacao": dias_passados,
                "duracao_ciclo": duracao,
                "inicio_ciclo": inicio_ciclo,
            }
        acumulado += dur

    return {
        "fase": "Desconhecida",
        "mensagem": "Não foi possível calcular a fase",
        "dias_desde_menstruacao": dias_passados,
    }

@router.get("/fase-por-data")
def fase_por_data(
    data: date,
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()

    if not usuario or not usuario.data_menstruacao or not usuario.duracao_ciclo:
        raise HTTPException(status_code=400, detail="Usuária sem dados completos do ciclo")

    inicio_ciclo = usuario.data_menstruacao
    duracao = usuario.duracao_ciclo
    dias_passados = (data - inicio_ciclo).days % duracao

    # Define durações proporcionais
    duracao_menstruacao = round(duracao * 0.18)  # ~5 dias
    duracao_folicular = round(duracao * 0.32)    # ~9 dias
    duracao_ovulacao = round(duracao * 0.14)     # ~4 dias
    duracao_lutea = duracao - (duracao_menstruacao + duracao_folicular + duracao_ovulacao)

    fases = [
        ("Menstruação", duracao_menstruacao, "Fase reflexiva 🌑"),
        ("Folicular", duracao_folicular, "Fase dinâmica 🌒"),
        ("Ovulatória", duracao_ovulacao, "Fase expansiva 🌕"),
        ("Lútea", duracao_lutea, "Fase criativa 🌘"),
    ]

    acumulado = 0
    for nome, dur, mensagem in fases:
        if acumulado <= dias_passados < acumulado + dur:
            return {
                "data": data,
                "fase": nome,
                "mensagem": mensagem,
                "dias_desde_menstruacao": dias_passados,
                "inicio_ciclo": inicio_ciclo
            }
        acumulado += dur

    return {
        "data": data,
        "fase": "Desconhecida",
        "mensagem": "Não foi possível determinar a fase",
        "dias_desde_menstruacao": dias_passados
    }