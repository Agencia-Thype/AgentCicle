from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, List
from datetime import date, datetime, timedelta

from app.db.database import get_db
from app.services.auth_service import verificar_token
from app.models.sqlalchemy_models import Usuario, TreinoRealizado
from app.services.treino_service import obter_treino_por_fase, definir_treino_do_dia
from app.services.ciclo_service import calcular_fase_do_ciclo
from app.models.treino_models import ConcluirTreinoRequest
from sqlalchemy import func
from app.utils.acesso import verificar_acesso
from app.utils.datas import hoje_brasilia

router = APIRouter(prefix="/treino-dia", tags=["Treino"])

@router.get("")
@verificar_acesso(recurso_premium=False, permite_trial=True)
async def treino_do_dia(
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    return obter_treino_por_fase(email=email, db=db)


def calcular_pontos_treino(percentual: float) -> int:
    """Pontos pela faixa de conclusão do treino do dia."""
    if percentual == 0:
        return 0
    elif percentual < 25:
        return 3
    elif percentual < 50:
        return 5
    elif percentual < 75:
        return 10
    elif percentual < 100:
        return 15
    else:
        return 20


def _treino_de_hoje(db: Session, usuario_id: int) -> Optional[TreinoRealizado]:
    # Um treino por dia: se houver registros duplicados antigos, vale o primeiro.
    return (
        db.query(TreinoRealizado)
        .filter(TreinoRealizado.usuario_id == usuario_id, TreinoRealizado.data == hoje_brasilia())
        .order_by(TreinoRealizado.id)
        .first()
    )


def _progresso_da_semana(db: Session, usuario: Usuario, hoje: date) -> float:
    if not usuario.data_menstruacao:
        return 0

    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)

    treinos_semana = db.query(TreinoRealizado).filter(
        TreinoRealizado.usuario_id == usuario.id,
        TreinoRealizado.data >= inicio_semana,
        TreinoRealizado.data <= fim_semana,
    ).all()

    return calcular_progresso_semana(treinos_semana, usuario.data_menstruacao, inicio_semana, fim_semana)


@router.post("/concluir", status_code=200)
@verificar_acesso(recurso_premium=False, permite_trial=True)
async def concluir_treino(
    dados: ConcluirTreinoRequest,
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    """
    Registra o check-in do treino do dia.

    A pontuação acompanha a conclusão atual nos dois sentidos: marcar mais
    exercícios soma pontos, desmarcar tira. Só o treino do dia é aceito, então
    não há como somar pontos com vários treinos na mesma data.
    """
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    # Verificar status do usuário (assinatura/trial)
    from app.services.assinatura_service import verificar_status_usuario
    status_usuario = verificar_status_usuario(db, usuario.id)

    # Usar o valor de temAcesso como fallback se podePontuar não existir
    pode_pontuar = status_usuario.get("podePontuar", status_usuario.get("temAcesso", False))

    # Se não puder pontuar, mostramos apenas um aviso por enquanto
    if not pode_pontuar:
        print(f"⚠️ Usuário {email} tentou registrar pontos sem trial/assinatura ativa")
        # Quando ativar os bloqueios, comentar a linha abaixo
        pode_pontuar = True
        # E descomentar esta linha:
        # return {"erro": "Seu período de avaliação expirou. Assine para continuar registrando treinos e ganhando pontos."}

    fase_info = calcular_fase_do_ciclo(str(usuario.data_menstruacao), usuario.duracao_ciclo or 28)
    fase = fase_info["fase"]
    percentual = min(max(float(dados.percentual), 0), 100)
    # Sem repetições, mantendo a ordem em que vieram.
    exercicios_concluidos = list(dict.fromkeys(dados.exercicios_concluidos or []))
    hoje = hoje_brasilia()

    treino_do_dia = definir_treino_do_dia(db, usuario.id, fase)
    if dados.tipo_treino != treino_do_dia:
        raise HTTPException(
            status_code=409,
            detail=f"O treino de hoje é o {treino_do_dia}. Só ele conta pontos hoje."
        )

    # Sem db.begin() aqui: no SQLAlchemy 2.0 a sessão já abre a transação na
    # 1ª consulta, e o begin(subtransactions=True) derrubava toda conclusão
    # com 500. O commit/rollback explícito abaixo já garante a atomicidade.
    treino_hoje = _treino_de_hoje(db, usuario.id)
    ja_salvo = treino_hoje is not None

    novos_pontos = calcular_pontos_treino(percentual)
    pontos_antigos = (treino_hoje.pontos or 0) if treino_hoje else 0
    pontos_ganhos = novos_pontos - pontos_antigos

    try:
        if treino_hoje:
            treino_hoje.percentual_concluido = percentual
            treino_hoje.exercicios_concluidos = exercicios_concluidos
            treino_hoje.pontos = novos_pontos
        else:
            treino_hoje = TreinoRealizado(
                usuario_id=usuario.id,
                data=hoje,
                fase=fase,
                treino=dados.tipo_treino,
                percentual_concluido=percentual,
                exercicios_concluidos=exercicios_concluidos,
                pontos=novos_pontos
            )
            db.add(treino_hoje)

        usuario.pontos_totais = max(0, (usuario.pontos_totais or 0) + pontos_ganhos)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"❌ ERRO AO SALVAR TREINO: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao salvar treino: {str(e)}")

    print(f"✅ Check-in do treino {dados.tipo_treino}: {percentual}% | pontos {pontos_antigos} → {novos_pontos} ({pontos_ganhos:+}) | total {usuario.pontos_totais}")

    if pontos_ganhos > 0:
        mensagem = f"Treino salvo com {percentual}%: +{pontos_ganhos} ponto(s)."
    elif pontos_ganhos < 0:
        mensagem = f"Treino atualizado para {percentual}%: {pontos_ganhos} ponto(s)."
    else:
        mensagem = f"Treino salvo com {percentual}%. Sua pontuação não mudou."

    return {
        "mensagem": mensagem,
        "ja_salvo": ja_salvo,
        "percentual": percentual,
        "exercicios_concluidos": exercicios_concluidos,
        "pontos_treino": novos_pontos,
        "pontos_ganhos": pontos_ganhos,
        "pontos_totais": usuario.pontos_totais,
        "progresso_semana": _progresso_da_semana(db, usuario, hoje),
        "redirecionar_para": "/home",  # Instrução para o frontend redirecionar para a home
        "atualizar_pontuacao": pontos_ganhos != 0
    }


def calcular_progresso_semana(treinos, data_menstruacao, data_inicio, data_fim):
    """
    Calcula o progresso semanal baseado nos treinos realizados.

    Args:
        treinos: Lista de treinos realizados
        data_menstruacao: Data de menstruação do usuário
        data_inicio: Data de início da semana
        data_fim: Data de fim da semana

    Returns:
        float: Porcentagem média de progresso na semana
    """
    treinos_por_data = {}

    for t in treinos:
        if isinstance(t.data, datetime):
            dia = t.data.date()
        else:
            dia = t.data

        valor = float(t.percentual_concluido or 0)
        if dia not in treinos_por_data or valor > treinos_por_data[dia]:
            treinos_por_data[dia] = valor

    soma = 0
    dias_com_treino_esperado = 0

    dias_da_semana = (data_fim - data_inicio).days + 1
    for i in range(dias_da_semana):
        dia = data_inicio + timedelta(days=i)
        fase = fase_do_dia(data_menstruacao, dia)

        if fase in ["Menstruação", "Folicular", "Ovulatória", "Lútea"]:
            progresso = treinos_por_data.get(dia, 0)
            dias_com_treino_esperado += 1
            soma += progresso

    if dias_com_treino_esperado == 0:
        return 0

    media = soma / dias_com_treino_esperado
    return round(media, 1)


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
    """Check-in do treino de hoje, com os exercícios exatos que foram marcados."""
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    treino = _treino_de_hoje(db, usuario.id)
    if not treino:
        return {"percentual": 0, "ja_salvo": False, "exercicios_concluidos": []}

    return {
        "percentual": float(treino.percentual_concluido or 0),
        "ja_salvo": True,
        "tipo_treino": treino.treino,
        "pontos": treino.pontos or 0,
        # Registros de antes da migração não têm a lista: o app cai no percentual.
        "exercicios_concluidos": treino.exercicios_concluidos or [],
        "id": treino.id,  # Adicionando ID para facilitar diagnóstico no frontend
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


@router.get("/diagnostico")
@verificar_acesso(recurso_premium=False, permite_trial=True)
def diagnostico_treinos(
    data_inicio: Optional[str] = Query(None, description="Data inicial no formato YYYY-MM-DD (opcional)"),
    data_fim: Optional[str] = Query(None, description="Data final no formato YYYY-MM-DD (opcional)"),
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    """
    Endpoint para diagnóstico dos treinos registrados.
    Retorna informações detalhadas sobre os treinos para ajudar na identificação de problemas.
    """
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    # Se não informar datas, usa últimos 30 dias
    hoje = hoje_brasilia()
    try:
        if data_inicio:
            inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
        else:
            inicio = hoje - timedelta(days=30)

        if data_fim:
            fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
        else:
            fim = hoje
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD.")

    # Buscar todos os treinos no período
    treinos = db.query(TreinoRealizado).filter(
        TreinoRealizado.usuario_id == usuario.id,
        TreinoRealizado.data >= inicio,
        TreinoRealizado.data <= fim
    ).order_by(TreinoRealizado.data.desc(), TreinoRealizado.id.desc()).all()

    # Organizar treinos por data
    treinos_por_data = {}
    for t in treinos:
        data_key = t.data.isoformat() if isinstance(t.data, date) else str(t.data)
        if data_key not in treinos_por_data:
            treinos_por_data[data_key] = []

        treinos_por_data[data_key].append({
            "id": t.id,
            "fase": t.fase,
            "tipo": t.treino,
            "percentual": float(t.percentual_concluido or 0),
            "pontos": t.pontos or 0
        })

    # Informações de resumo
    resumo = {
        "total_treinos": len(treinos),
        "dias_com_treino": len(treinos_por_data),
        "media_percentual": round(sum(float(t.percentual_concluido or 0) for t in treinos) / len(treinos), 1) if treinos else 0,
        "pontos_totais": usuario.pontos_totais,
        "dias_no_periodo": (fim - inicio).days + 1
    }

    # Análise de duplicidades e possíveis problemas
    dias_com_multiplos_treinos = {
        data: treinos for data, treinos in treinos_por_data.items()
        if len(treinos) > 1
    }

    problemas = []

    # Verificar dias com múltiplos treinos do mesmo tipo
    for data, treinos_dia in dias_com_multiplos_treinos.items():
        tipos = {}
        for t in treinos_dia:
            if t["tipo"] not in tipos:
                tipos[t["tipo"]] = []
            tipos[t["tipo"]].append(t)

        for tipo, treinos_tipo in tipos.items():
            if len(treinos_tipo) > 1:
                problemas.append({
                    "tipo": "duplicidade_mesmo_tipo",
                    "data": data,
                    "tipo_treino": tipo,
                    "registros": treinos_tipo
                })

    return {
        "periodo": {
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat()
        },
        "resumo": resumo,
        "treinos_por_data": treinos_por_data,
        "dias_com_multiplos_treinos": len(dias_com_multiplos_treinos),
        "problemas_detectados": problemas
    }
