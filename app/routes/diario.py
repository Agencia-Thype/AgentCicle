# app/routes/diario.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, datetime
from app.db.database import get_db
from app.services.auth_service import verificar_token
from app.models.sqlalchemy_models import Usuario, DiarioCiclo
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
        # Atualiza registro existente
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

    db.commit()

    return {
        "mensagem": "Sintomas registrados com sucesso!",
        "pontos": 2 if is_hoje else 0
    }
