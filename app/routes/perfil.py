from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from app.schemas.usuario_schemas import PerfilUsuario
from app.services.auth_service import verificar_token
from app.db.database import get_db
from app.models.sqlalchemy_models import Usuario, HistoricoPeso

router = APIRouter(tags=["Perfil"])

@router.get("/perfil", response_model=PerfilUsuario)
def get_perfil(
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    # Calcular IMC
    imc = None
    if usuario.altura and usuario.peso_atual:
        imc = round(float(usuario.peso_atual) / float(usuario.altura) ** 2, 1)

    # Buscar histórico de peso (últimos 5 registros)
    historico = (
        db.query(HistoricoPeso)
        .filter(HistoricoPeso.user_id == usuario.id)
        .order_by(HistoricoPeso.data_registro.desc())
        .limit(5)
        .all()
    )

    historico_formatado = [
        {
            "peso": float(h.peso),
            "altura": float(h.altura) if h.altura else None,
            "imc": float(h.imc) if h.imc else None,
            "data": h.data_registro
        }
        for h in historico
    ]

    return PerfilUsuario(
        nome=usuario.nome,
        altura=float(usuario.altura) if usuario.altura else None,
        peso_atual=float(usuario.peso_atual) if usuario.peso_atual else None,
        objetivo=usuario.objetivo,
        data_menstruacao=usuario.data_menstruacao,
        imc=imc,
        historico_peso=historico_formatado
    )


@router.put("/perfil")
def atualizar_perfil(
    perfil: PerfilUsuario,
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    if perfil.altura:
        usuario.altura = perfil.altura
    if perfil.peso_atual:
        usuario.peso_atual = perfil.peso_atual
        usuario.data_peso_atual = date.today()

        imc = perfil.peso_atual / (perfil.altura ** 2) if perfil.altura else None
        novo_historico = HistoricoPeso(
            user_id=usuario.id,
            peso=perfil.peso_atual,
            altura=perfil.altura,
            imc=imc,
            data_registro=date.today()
        )
        db.add(novo_historico)

    if perfil.objetivo:
        usuario.objetivo = perfil.objetivo
    if perfil.data_menstruacao:
        usuario.data_menstruacao = perfil.data_menstruacao

    db.commit()
    return {"mensagem": "Perfil atualizado com sucesso"}
