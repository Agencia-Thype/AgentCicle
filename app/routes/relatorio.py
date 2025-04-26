from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.database import get_db
from app.services.auth_service import verificar_token
from app.models.sqlalchemy_models import Usuario, DiarioCiclo, TreinoRealizado

router = APIRouter(prefix="/relatorio", tags=["Relatórios"])

@router.get("/mensal")
def relatorio_mensal(
    mes: str = Query(..., regex="^\\d{4}-\\d{2}$"),  # Ex: 2025-04
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter_by(email=email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    ano, mes_num = map(int, mes.split("-"))
    inicio = datetime(ano, mes_num, 1)
    fim = datetime(ano + 1, 1, 1) if mes_num == 12 else datetime(ano, mes_num + 1, 1)

    fases = ["menstruacao", "folicular", "ovulatoria", "lutea"]
    resultado = {}

    for fase in fases:
        treinos = db.query(TreinoRealizado).filter(
            TreinoRealizado.usuario_id == usuario.id,
            TreinoRealizado.data >= inicio,
            TreinoRealizado.data < fim,
            TreinoRealizado.fase.ilike(fase)
        ).all()

        diarios = db.query(DiarioCiclo).filter(
            DiarioCiclo.user_id == usuario.id,
            DiarioCiclo.data >= inicio,
            DiarioCiclo.data < fim,
            DiarioCiclo.fase.ilike(fase)
        ).all()

        percentual_total = sum([t.percentual_concluido or 0 for t in treinos])
        percentual_medio = round(percentual_total / len(treinos), 1) if treinos else 0

        sentimentos = []
        for d in diarios:
            if d.sentimento:
                sentimentos += d.sentimento.split(", ")

        mais_comuns = list({s: sentimentos.count(s) for s in sentimentos}.items())
        mais_comuns.sort(key=lambda x: x[1], reverse=True)
        top_sentimentos = [s[0] for s in mais_comuns[:3]]

        # 🆕 Lista de treinos para gráfico
        grafico = [
            {
                "dia": t.data.day,
                "percentual": round(t.percentual_concluido or 0, 1)
            }
            for t in treinos
        ]

        resultado[fase] = {
            "dias_com_treino": len(treinos),
            "percentual_medio": percentual_medio,
            "sentimentos_frequentes": top_sentimentos,
            "dias_com_registro": len(diarios),
            "grafico": grafico  # ⬅️ Adicionado aqui
        }

    return resultado
