from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from datetime import date, timedelta
import json
from app.db.database import get_db
from app.services.auth_service import verificar_token
from app.models.sqlalchemy_models import Usuario, TreinoRealizado, DiarioCiclo
from app.services.ciclo_service import calcular_fase_do_ciclo
from app.services.llm_service import gerar_resposta_ia 

router = APIRouter(prefix="/fase-atual")

@router.get("/detalhes")
def detalhes_fase_atual(
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario or not usuario.data_menstruacao:
        raise HTTPException(status_code=404, detail="Usuária não encontrada ou sem menstruação registrada")

    fase_info = calcular_fase_do_ciclo(str(usuario.data_menstruacao), usuario.duracao_ciclo)
    fase_atual = fase_info["fase"]
    hoje = date.today()

    mapeamento_fases = {
        "Menstruação": "fase_menstrual",
        "Folicular": "fase_folicular",
        "Ovulatória": "fase_ovulatoria",
        "Lútea": "fase_lutea"
    }
    fase_chave = mapeamento_fases.get(fase_atual)

    with open("data/fases_completas.json", encoding="utf-8") as f:
        fases_info = json.load(f)

    descricao = fases_info.get(fase_chave, {}).get("descricao", "Sem descrição disponível.")

    def calcular_percentual_por_fase(data_base):
        treinos = db.query(TreinoRealizado).filter(
            TreinoRealizado.usuario_id == usuario.id,
            TreinoRealizado.data >= data_base - timedelta(days=35),
            TreinoRealizado.data <= data_base,
            TreinoRealizado.fase == fase_atual
        ).all()

        if not treinos:
            return 0.0

        return round(
            sum(float(t.percentual_concluido or 0) for t in treinos) / len(treinos), 1
        )

    percentual_atual = calcular_percentual_por_fase(hoje)
    percentual_anterior = calcular_percentual_por_fase(hoje - timedelta(days=30))

    data_inicio_anterior = hoje - timedelta(days=35)
    sentimentos_anteriores = db.query(DiarioCiclo).filter(
        DiarioCiclo.user_id == usuario.id,
        DiarioCiclo.data >= data_inicio_anterior,
        DiarioCiclo.data <= hoje,
        DiarioCiclo.fase == fase_atual
    ).all()

    sentimentos = set()

    for d in sentimentos_anteriores:
        try:
            if d.sentimento and d.sentimento.strip():
                sentimentos.update(json.loads(d.sentimento))
        except json.JSONDecodeError:
            continue  # ignora registros corrompidos

    return {
        "fase_atual": fase_atual,
        "descricao": descricao,
        "percentual_atual": percentual_atual,
        "percentual_anterior": percentual_anterior,
        "sentimentos_anteriores": list(sentimentos)
    }

@router.post("/conversar")
def conversar_com_ia(
    pergunta: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario or not usuario.data_menstruacao:
        raise HTTPException(status_code=404, detail="Usuária não encontrada ou sem menstruação registrada")

    fase_info = calcular_fase_do_ciclo(str(usuario.data_menstruacao), usuario.duracao_ciclo)
    fase_atual = fase_info["fase"]
    hoje = date.today()

    # Treinos da fase atual no mês atual e anterior
    def treinos_por_fase(data_base):
        return db.query(TreinoRealizado).filter(
            TreinoRealizado.usuario_id == usuario.id,
            TreinoRealizado.data >= data_base - timedelta(days=35),
            TreinoRealizado.data <= data_base,
            TreinoRealizado.fase == fase_atual
        ).all()

    treinos_atuais = treinos_por_fase(hoje)
    treinos_anteriores = treinos_por_fase(hoje - timedelta(days=30))

    percentual_atual = round(sum(float(t.percentual_concluido or 0) for t in treinos_atuais) / len(treinos_atuais), 1) if treinos_atuais else 0.0
    percentual_anterior = round(sum(float(t.percentual_concluido or 0) for t in treinos_anteriores) / len(treinos_anteriores), 1) if treinos_anteriores else 0.0

    # Sentimentos anteriores
    sentimentos_query = db.query(DiarioCiclo).filter(
        DiarioCiclo.user_id == usuario.id,
        DiarioCiclo.data >= hoje - timedelta(days=35),
        DiarioCiclo.data <= hoje,
        DiarioCiclo.fase == fase_atual
    ).all()

    sentimentos = set()

    for d in sentimentos_query:
        try:
            if d.sentimento and d.sentimento.strip():
                sentimentos.update(json.loads(d.sentimento))
        except json.JSONDecodeError:
            continue  # ignora valores inválidos

    sentimentos = list(sentimentos)  # converte de volta para lista

    # Carrega conteúdo do eBook da fase
    with open("data/fases_completas.json", encoding="utf-8") as f:
        fases_info = json.load(f)

    mapeamento_fases = {
        "Menstruação": "fase_menstrual",
        "Folicular": "fase_folicular",
        "Ovulatória": "fase_ovulatoria",
        "Lútea": "fase_lutea"
    }
    fase_chave = mapeamento_fases.get(fase_atual)
    conteudo_fase = fases_info.get(fase_chave, {}).get("descricao", "")

    # Prompt para IA
    contexto = {
    "fase_atual": fase_atual,
    "descricao": conteudo_fase,
    "percentual_atual": percentual_atual,
    "percentual_anterior": percentual_anterior,
    "sentimentos_anteriores": sentimentos,
}

    resposta = gerar_resposta_ia(pergunta, contexto)

    return {
        "fase_atual": fase_atual,
        "resposta": resposta
    }