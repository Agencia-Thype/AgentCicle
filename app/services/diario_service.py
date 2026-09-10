# app/services/diario_service.py
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.sqlalchemy_models import Usuario, DiarioCiclo, HistoricoPeso
from app.models.diario_models import SintomasRequest
from app.utils.datas import hoje_brasilia

PONTOS_REGISTRO_DIARIO = 2


def registrar_sintomas(db: Session, usuario: Usuario, dados: SintomasRequest) -> int:
    """
    Cria ou atualiza o registro do diário e devolve os pontos ganhos.

    Só o primeiro registro do próprio dia pontua: editar o registro ou lançar
    dias passados não gera pontos, senão a gamificação vira farm.
    """
    hoje = hoje_brasilia()
    data_registro = dados.data or hoje
    pontos = 0

    registro = db.query(DiarioCiclo).filter_by(user_id=usuario.id, data=data_registro).first()

    if registro:
        registro.sentimento = ", ".join(dados.sentimentos)
        registro.observacao = dados.observacao
        registro.fase = dados.fase or registro.fase
    else:
        db.add(DiarioCiclo(
            user_id=usuario.id,
            data=data_registro,
            sentimento=", ".join(dados.sentimentos),
            observacao=dados.observacao,
            fase=dados.fase,
            created_at=datetime.now()
        ))
        if data_registro == hoje:
            pontos = PONTOS_REGISTRO_DIARIO
            usuario.pontos_totais = (usuario.pontos_totais or 0) + pontos

    if dados.peso is not None:
        peso_existente = db.query(HistoricoPeso).filter_by(
            user_id=usuario.id,
            data_registro=data_registro
        ).first()

        if peso_existente:
            peso_existente.peso = dados.peso
        else:
            db.add(HistoricoPeso(
                user_id=usuario.id,
                peso=dados.peso,
                data_registro=data_registro
            ))

    db.commit()
    return pontos
