from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date, datetime, timedelta

from app.db.database import get_db
from app.services.auth_service import verificar_token
from app.models.sqlalchemy_models import Usuario, TreinoRealizado
from app.services.treino_service import obter_treino_por_fase, calcular_fase
from app.models.treino_models import ConcluirTreinoRequest
from sqlalchemy import func

router = APIRouter(prefix="/treino-dia", tags=["Treino"])

@router.get("")
def treino_do_dia(
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    return obter_treino_por_fase(email=email, db=db)


@router.post("/registrar")
def registrar_treino(
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    fase = calcular_fase(str(usuario.data_menstruacao))

    treinos_feitos = (
        db.query(TreinoRealizado)
        .filter(TreinoRealizado.usuario_id == usuario.id)
        .filter(TreinoRealizado.fase == fase)
        .order_by(TreinoRealizado.data.desc())
        .all()
    )

    sequencia = ["A", "B", "C", "D", "E"]
    if not treinos_feitos:
        tipo_treino = "A"
    else:
        ultimo = treinos_feitos[0].treino
        idx = sequencia.index(ultimo)
        tipo_treino = sequencia[(idx + 1) % len(sequencia)]

    treino_realizado = TreinoRealizado(
        usuario_id=usuario.id,
        fase=fase,
        treino=tipo_treino,
        data=date.today()
    )
    db.add(treino_realizado)
    db.commit()

    return {"mensagem": f"Treino {tipo_treino} registrado com sucesso para a fase {fase}!"}

@router.post("/concluir", status_code=201)
def concluir_treino(
    dados: ConcluirTreinoRequest,
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    percentual = dados.percentual

    # Verifica se já existe treino registrado hoje para esse tipo e fase
    treino_existente = db.query(TreinoRealizado).filter_by(
        usuario_id=usuario.id,
        data=date.today(),
        fase=dados.fase,
        treino=dados.tipo_treino
    ).first()

    if treino_existente:
        return {
            "mensagem": f"Você já concluiu este treino hoje com {treino_existente.percentual_concluido}% e ganhou {treino_existente.pontos} ponto(s).",
            "ja_salvo": True,
            "percentual": treino_existente.percentual_concluido,
            "pontos": treino_existente.pontos
        }

    # Calcula pontos com base no percentual (primeira vez salvando)
    if percentual == 0:
        pontos = 0
    elif percentual < 25:
        pontos = 3
    elif percentual < 50:
        pontos = 5
    elif percentual < 75:
        pontos = 10
    elif percentual < 100:
        pontos = 15
    else:
        pontos = 20

    novo_treino = TreinoRealizado(
        usuario_id=usuario.id,
        data=date.today(),
        fase=dados.fase,
        treino=dados.tipo_treino,
        percentual_concluido=percentual,
        pontos=pontos
    )
    db.add(novo_treino)

    # Atualiza a pontuação total da usuária apenas no primeiro registro
    usuario.pontos_totais = (usuario.pontos_totais or 0) + pontos

    db.commit()

    return {
        "mensagem": f"Treino {dados.tipo_treino} salvo com {percentual}% de conclusão.",
        "ja_salvo": False,
        "percentual": percentual,
        "pontos": pontos
    }

@router.get("/progresso-semanal")
def progresso_semanal(
    inicio: str = Query(..., description="Data inicial no formato YYYY-MM-DD"),
    fim: str = Query(..., description="Data final no formato YYYY-MM-DD"),
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    try:
        data_inicio = datetime.strptime(inicio, "%Y-%m-%d").date()
        data_fim = datetime.strptime(fim, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido")

    treinos = db.query(TreinoRealizado).filter(
        TreinoRealizado.usuario_id == usuario.id,
        TreinoRealizado.data >= data_inicio,
        TreinoRealizado.data <= data_fim,
        TreinoRealizado.percentual_concluido.isnot(None)
    ).all()

    if not treinos:
        return {"media_percentual": 0}

    media = sum(t.percentual_concluido for t in treinos) / len(treinos)
    return {"media_percentual": round(media, 1)}

@router.get("/pontuacao")
def obter_pontuacao_e_classe(
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    hoje = date.today()
    primeiro_dia_mes = hoje.replace(day=1)

    pontos_mes = db.query(TreinoRealizado).filter(
        TreinoRealizado.usuario_id == usuario.id,
        TreinoRealizado.data >= primeiro_dia_mes,
        TreinoRealizado.pontos.isnot(None)
    ).with_entities(func.coalesce(func.sum(TreinoRealizado.pontos), 0)).scalar()

    data_inicio = usuario.data_menstruacao or usuario.data_criacao or hoje
    dias_de_uso = (hoje - data_inicio).days

    if dias_de_uso <= 30:
        classe = "Lua Nova"
        dias_restantes = 30 - dias_de_uso
    elif dias_de_uso <= 60:
        classe = "Lua Crescente"
        dias_restantes = 60 - dias_de_uso
    elif dias_de_uso <= 90:
        classe = "Lua Cheia"
        dias_restantes = 90 - dias_de_uso
    else:
        classe = "Lua Minguante"
        dias_restantes = 0

    return {
        "classe": classe,
        "dias_restantes": max(dias_restantes, 0),
        "pontos_mes": pontos_mes
    }
