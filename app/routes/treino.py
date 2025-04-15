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


# @router.post("/registrar")
# def registrar_treino(
#     db: Session = Depends(get_db),
#     email: str = Depends(verificar_token)
# ):
#     usuario = db.query(Usuario).filter(Usuario.email == email).first()
#     if not usuario:
#         raise HTTPException(status_code=404, detail="Usuária não encontrada")

#     fase = calcular_fase(str(usuario.data_menstruacao))

#     treinos_feitos = (
#         db.query(TreinoRealizado)
#         .filter(TreinoRealizado.usuario_id == usuario.id)
#         .filter(TreinoRealizado.fase == fase)
#         .order_by(TreinoRealizado.data.desc())
#         .all()
#     )

#     sequencia = ["A", "B", "C", "D", "E"]
#     if not treinos_feitos:
#         tipo_treino = "A"
#     else:
#         ultimo = treinos_feitos[0].treino
#         idx = sequencia.index(ultimo)
#         tipo_treino = sequencia[(idx + 1) % len(sequencia)]

#     treino_realizado = TreinoRealizado(
#         usuario_id=usuario.id,
#         fase=fase,
#         treino=tipo_treino,
#         data=date.today()
#     )
#     db.add(treino_realizado)
#     db.commit()

#     return {"mensagem": f"Treino {tipo_treino} registrado com sucesso para a fase {fase}!"}

@router.post("/concluir", status_code=200)
def concluir_treino(
    dados: ConcluirTreinoRequest,
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    fase = calcular_fase(str(usuario.data_menstruacao))
    percentual = dados.percentual

    print("✅ Percentual recebido:", percentual)

    treino_existente = db.query(TreinoRealizado).filter_by(
        usuario_id=usuario.id,
        data=date.today(),
        fase=fase,
        treino=dados.tipo_treino
    ).first()

    def calcular_pontos(p):
        if p == 0:
            return 0
        elif p < 25:
            return 3
        elif p < 50:
            return 5
        elif p < 75:
            return 10
        elif p < 100:
            return 15
        else:
            return 20

    if treino_existente:
        percentual_antigo = float(treino_existente.percentual_concluido or 0)
        print(f"📝 Atualizando treino existente ({treino_existente.data}): antes={percentual_antigo}, novo={percentual}")

        if percentual > percentual_antigo:
            pontos_antigos = treino_existente.pontos or 0
            novos_pontos = calcular_pontos(percentual)

            if novos_pontos > pontos_antigos:
                # Ganha apenas a diferença
                ganho_real = novos_pontos - pontos_antigos
                usuario.pontos_totais = (usuario.pontos_totais or 0) + ganho_real
                treino_existente.pontos = novos_pontos

            treino_existente.percentual_concluido = percentual

            db.commit()
            db.refresh(treino_existente)

            print("🎯 CONFIRMAÇÃO SALVO NO BANCO (ATUALIZADO):", treino_existente.percentual_concluido)

            return {
                "mensagem": f"Treino atualizado para {percentual}% de conclusão.",
                "ja_salvo": True,
                "percentual": percentual,
                "pontos": treino_existente.pontos
            }

        # Se percentual for igual ou menor, não muda nada
        return {
            "mensagem": f"Você já concluiu este treino hoje com {percentual_antigo}%. Nenhuma pontuação nova aplicada.",
            "ja_salvo": True,
            "percentual": percentual_antigo,
            "pontos": treino_existente.pontos
        }

    # 🆕 Se não existir, cria normalmente
    novos_pontos = calcular_pontos(percentual)
    novo_treino = TreinoRealizado(
        usuario_id=usuario.id,
        data=date.today(),
        fase=fase,
        treino=dados.tipo_treino,
        percentual_concluido=percentual,
        pontos=novos_pontos
    )
    db.add(novo_treino)
    usuario.pontos_totais = (usuario.pontos_totais or 0) + novos_pontos
    db.commit()
    db.refresh(novo_treino)
    print("🎯 Novo treino persistido com:", novo_treino.percentual_concluido)

    return {
        "mensagem": f"Treino salvo com {percentual}% e {novos_pontos} ponto(s) conquistados.",
        "ja_salvo": False,
        "percentual": percentual,
        "pontos": novos_pontos
    }


FASES = [
    ("Menstruação", 0, 5),
    ("Folicular", 6, 12),
    ("Ovulatória", 13, 16),
    ("Lútea", 17, 28),
]

def fase_do_dia(data_menstruacao: date, dia: date) -> str:
    dias_ciclo = (dia - data_menstruacao).days % 28
    for nome, ini, fim in FASES:
        if ini <= dias_ciclo <= fim:
            return nome
    return "Desconhecida"

@router.get("/marcados-hoje")
def progresso_treino_hoje(
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    fase = calcular_fase(str(usuario.data_menstruacao))

    treino = db.query(TreinoRealizado).filter_by(
        usuario_id=usuario.id,
        data=date.today(),
        fase=fase
    ).order_by(TreinoRealizado.id.desc()).first()

    if not treino:
        return {"percentual": 0, "ja_salvo": False}

    return {
        "percentual": float(treino.percentual_concluido or 0),
        "ja_salvo": True,
        "tipo_treino": treino.treino,
        "pontos": treino.pontos or 0
    }



@router.get("/progresso-semanal")
def progresso_semanal(
    inicio: str = Query(..., description="Data inicial no formato YYYY-MM-DD"),
    fim: str = Query(..., description="Data final no formato YYYY-MM-DD"),
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario or not usuario.data_menstruacao:
        raise HTTPException(status_code=404, detail="Usuária não encontrada ou sem menstruação registrada")

    try:
        data_inicio = datetime.strptime(inicio, "%Y-%m-%d").date()

        data_fim = datetime.strptime(fim, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido")

    dias_da_semana = (data_fim - data_inicio).days + 1
    if dias_da_semana <= 0:
        raise HTTPException(status_code=400, detail="Intervalo inválido")

    # Buscar treinos realizados no período
    treinos_realizados = db.query(TreinoRealizado).filter(
        TreinoRealizado.usuario_id == usuario.id,
        TreinoRealizado.data >= data_inicio,
        TreinoRealizado.data <= data_fim,
    ).all()

    treinos_por_data = {}

    for t in treinos_realizados:
        if isinstance(t.data, datetime):
            dia = t.data.date()
        else:
            dia = t.data

        valor = float(t.percentual_concluido or 0)
        if dia not in treinos_por_data or valor > treinos_por_data[dia]:
            treinos_por_data[dia] = valor

    for dia, valor in treinos_por_data.items():
        print(f"🧾 Dia {dia} → {valor}% concluído")

    soma = 0
    dias_com_treino_esperado = 0

    for i in range(dias_da_semana):
        dia = data_inicio + timedelta(days=i)
        fase = fase_do_dia(usuario.data_menstruacao, dia)

        if fase in ["Menstruação", "Folicular", "Ovulatória", "Lútea"]:
            progresso = treinos_por_data.get(dia, 0)
            print(f"🔎 Verificando dia {dia}: fase={fase}, progresso={progresso}")
            dias_com_treino_esperado += 1
            soma += progresso

    if dias_com_treino_esperado == 0:
        return {"media_percentual": 0}

    media = soma / dias_com_treino_esperado

    print("📅 Treinos por data:", treinos_por_data)
    print(f"✅ Soma: {soma} | Dias com treino esperado: {dias_com_treino_esperado} | Média: {media:.1f}%")

    return {"media_percentual": round(media, 1)}
