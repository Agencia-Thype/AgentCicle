from fastapi import APIRouter, Depends, HTTPException, Body
from app.services.treino_service import calcular_percentual_por_fase
from app.utils.constantes import MAPEAMENTO_FASES
from sqlalchemy.orm import Session
from datetime import date, timedelta
import json
import traceback
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

    hoje = date.today()
    fase_info = calcular_fase_do_ciclo(str(usuario.data_menstruacao), usuario.duracao_ciclo)
    fase_atual = fase_info["fase"]
    fase_chave = MAPEAMENTO_FASES.get(fase_atual)

    # Descrição da fase
    with open("data/fases_completas.json", encoding="utf-8") as f:
        fases_info = json.load(f)
    descricao = fases_info.get(fase_chave, {}).get("descricao", "Sem descrição disponível.")

    # Cálculo de percentuais
    percentual_atual = calcular_percentual_por_fase(db, usuario.id, fase_atual, hoje)
    percentual_anterior = calcular_percentual_por_fase(db, usuario.id, fase_atual, hoje - timedelta(days=30))

    # Sentimentos registrados
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
            continue

    return {
        "fase_atual": fase_atual,
        "descricao": descricao,
        "percentual_atual": percentual_atual,
        "percentual_anterior": percentual_anterior,
        "sentimentos_anteriores": list(sentimentos)
    }


