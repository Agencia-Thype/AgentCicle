# app/routes/diario.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import date, datetime

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

    data_registro = dados.data or date.today()
    is_hoje = data_registro == date.today()

    registro = db.query(DiarioCiclo).filter_by(user_id=usuario.id, data=data_registro).first()

    if registro:
        registro.sentimento = ", ".join(dados.sentimentos)
        registro.observacao = dados.observacao
        registro.fase = dados.fase or registro.fase
    else:
        novo_registro = DiarioCiclo(
            user_id=usuario.id,
            data=data_registro,
            sentimento=", ".join(dados.sentimentos),
            observacao=dados.observacao,
            fase=dados.fase,
            created_at=datetime.now()
        )
        db.add(novo_registro)

        if is_hoje:
            usuario.pontos_totais = (usuario.pontos_totais or 0) + 2

    # Novo: registrar ou atualizar peso
    if dados.peso is not None:
        peso_existente = db.query(HistoricoPeso).filter_by(
            user_id=usuario.id,
            data_registro=data_registro
        ).first()

        if peso_existente:
            peso_existente.peso = dados.peso
        else:
            novo_peso = HistoricoPeso(
                user_id=usuario.id,
                peso=dados.peso,
                data_registro=data_registro
            )
            db.add(novo_peso)

    db.commit()

    return {
        "mensagem": "Sintomas registrados com sucesso!",
        "pontos": 2 if is_hoje else 0
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
