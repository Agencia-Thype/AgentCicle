from fastapi import APIRouter, Depends, HTTPException, Body, Query
from app.routes import usuario
from app.schemas.resposta_ia import RespostaIA
from app.services.ia_service import gerar_mensagem_entrada_com_ia, responder_com_RAG
from sqlalchemy.orm import Session
from datetime import date, timedelta
import json
from app.db.database import get_db
from app.services.auth_service import verificar_token
from app.models.sqlalchemy_models import Usuario, DiarioCiclo
from app.services.ciclo_service import calcular_fase_do_ciclo
from app.utils.constantes import MAPEAMENTO_FASES
from app.utils.acesso import verificar_acesso

from app.services.treino_service import calcular_percentual_por_fase

router = APIRouter(prefix="/ia", tags=["IA"])

@router.post("/conversar", response_model=RespostaIA)
@verificar_acesso(recurso_premium=True, permite_trial=False)
def conversar_ia(
    pergunta: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")
    
    # Garantir que temos os dados mais atualizados
    db.refresh(usuario)
    
    if not usuario.data_menstruacao:
        raise HTTPException(status_code=404, detail="Usuária sem menstruação registrada")

    hoje = date.today()
    fase_info = calcular_fase_do_ciclo(str(usuario.data_menstruacao), usuario.duracao_ciclo)
    fase_atual = fase_info["fase"]
    fase_chave = MAPEAMENTO_FASES.get(fase_atual)

    percentual_atual = calcular_percentual_por_fase(db, usuario.id, fase_atual, hoje)
    percentual_anterior = calcular_percentual_por_fase(db, usuario.id, fase_atual, hoje - timedelta(days=30))

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
        except:
            continue

    try:
        with open("data/fases_completas.json", encoding="utf-8") as f:
            fases_info = json.load(f)
        descricao_fase = fases_info.get(fase_chave, {}).get("descricao", "")
    except:
        descricao_fase = ""

    contexto = {
        "fase_atual": fase_atual,
        "descricao": descricao_fase,
        "percentual_atual": percentual_atual,
        "percentual_anterior": percentual_anterior,
        "sentimentos_anteriores": list(sentimentos)
    }

    try:
        # RAG com histórico e prompt empático
        resposta = responder_com_RAG(db, usuario.id, pergunta, contexto)
    except Exception as e:
        print("❌ ERRO ao chamar a IA:", e)
        resposta = "Ainda estou ajustando minha inspiração lunar 🌙. Tente novamente em instantes 💜"

    return {
        "fase_atual": fase_atual,
        "resposta": resposta
    }


@router.get("/mensagem-entrada", response_model=RespostaIA)
@verificar_acesso(recurso_premium=True, permite_trial=False)
def mensagem_entrada_ia(
    tipo: str = Query("boas_vindas", enum=["boas_vindas", "balao"]),
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")
    
    # Garantir que temos os dados mais atualizados
    db.refresh(usuario)
    
    if not usuario.data_menstruacao:
        raise HTTPException(status_code=404, detail="Usuária sem menstruação registrada")

    hoje = date.today()
    fase_info = calcular_fase_do_ciclo(str(usuario.data_menstruacao), usuario.duracao_ciclo)
    fase_atual = fase_info["fase"]
    fase_chave = MAPEAMENTO_FASES.get(fase_atual)

    percentual_atual = calcular_percentual_por_fase(db, usuario.id, fase_atual, hoje)
    percentual_anterior = calcular_percentual_por_fase(db, usuario.id, fase_atual, hoje - timedelta(days=30))

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
        except:
            continue

    try:
        with open("data/fases_completas.json", encoding="utf-8") as f:
            fases_info = json.load(f)
        descricao_fase = fases_info.get(fase_chave, {}).get("descricao", "")
    except:
        descricao_fase = ""

    contexto = {
        "fase_atual": fase_atual,
        "descricao": descricao_fase,
        "percentual_atual": percentual_atual,
        "percentual_anterior": percentual_anterior,
        "sentimentos_anteriores": list(sentimentos)
    }

    try:
        resposta = gerar_mensagem_entrada_com_ia(db, usuario.id, contexto, tipo)
    except Exception as e:
        import traceback
        print(f"❌ ERRO ao gerar mensagem de entrada: {str(e)}")
        traceback.print_exc()
        
        # Mensagens de fallback para cada tipo
        fallback = {
            "boas_vindas": f"Bem-vinda à sua fase {fase_atual}! Estou aqui para te apoiar nessa jornada 💜",
            "balao": "Como posso te ajudar hoje? 🌸"
        }
        resposta = fallback.get(tipo, "Estou aqui para te ajudar! 💕")

    return {"fase_atual": fase_atual, "resposta": resposta}