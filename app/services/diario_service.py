# app/services/diario_service.py
from sqlalchemy.orm import Session
from datetime import date, datetime
from app.models.sqlalchemy_models import Usuario, DiarioCiclo
from app.models.diario_models import SintomasRequest

def registrar_sintomas(db: Session, usuario: Usuario, dados: SintomasRequest) -> int:
    data_registro = dados.data or date.today()
    is_hoje = data_registro == date.today()

    registro = db.query(DiarioCiclo).filter_by(user_id=usuario.id, data=data_registro).first()

    if registro:
        registro.sentimento = ", ".join(dados.sentimentos)
        registro.observacao = dados.observacao
        registro.fase = dados.fase or registro.fase
    else:
        novo = DiarioCiclo(
            user_id=usuario.id,
            data=data_registro,
            sentimento=", ".join(dados.sentimentos),
            observacao=dados.observacao,
            fase=dados.fase,
            created_at=datetime.now()
        )
        db.add(novo)
        if is_hoje:
            usuario.pontos_totais = (usuario.pontos_totais or 0) + 2

    db.commit()
    return 2 if is_hoje else 0
