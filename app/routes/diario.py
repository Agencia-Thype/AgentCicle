# app/routes/diario.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date

from app.db.database import get_db
from app.services.auth_service import verificar_token
from app.models.sqlalchemy_models import Usuario, DiarioCiclo, TreinoRealizado, HistoricoPeso
from app.models.diario_models import SintomasRequest
from app.services.diario_service import registrar_sintomas as registrar_service

router = APIRouter(prefix="/diario", tags=["Diário do Ciclo"])

@router.post("/registrar-sintomas")
def registrar_sintomas(
    dados: SintomasRequest,
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    pontos = registrar_service(db, usuario, dados)

    return {
        "mensagem": "Sintomas registrados com sucesso!",
        "pontos": pontos
    }



@router.get("/resumo-do-dia")
def obter_resumo_do_dia(
    data: date = Query(..., description="Data no formato YYYY-MM-DD"),
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    resumo = {
        "data": data.isoformat(),
        "fase": None,
        "sentimentos": [],
        "observacao": None,
        "peso": None,
        "treino": None
    }

    # Diário do ciclo
    diario = db.query(DiarioCiclo).filter_by(user_id=usuario.id, data=data).first()
    if diario:
        resumo["fase"] = diario.fase
        resumo["sentimentos"] = diario.sentimento.split(", ") if diario.sentimento else []
        resumo["observacao"] = diario.observacao

    # Peso registrado
    peso_registro = db.query(HistoricoPeso).filter(
        HistoricoPeso.user_id == usuario.id,
        HistoricoPeso.data_registro == data
    ).first()
    if peso_registro:
        resumo["peso"] = peso_registro.peso

    # Treino realizado
    treino = db.query(TreinoRealizado).filter(
    TreinoRealizado.usuario_id == usuario.id,
    TreinoRealizado.data == data
    ).first()
    if treino:
        resumo["treino"] = {
            "fase": treino.fase,
            "tipo": treino.treino,
            "percentual_conclusao": treino.percentual_concluido
        }

        

    return resumo
