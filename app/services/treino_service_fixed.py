from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.sqlalchemy_models import Usuario, TreinoRealizado
from app.services.ciclo_service import calcular_fase_do_ciclo

def calcular_percentual_por_fase(db: Session, user_id: int, fase: str, data_base: date) -> float:
    treinos = db.query(TreinoRealizado).filter(
        TreinoRealizado.usuario_id == user_id,
        TreinoRealizado.data >= data_base - timedelta(days=35),
        TreinoRealizado.data <= data_base,
        TreinoRealizado.fase == fase
    ).all()

    if not treinos:
        return 0.0

    return round(
        sum(float(t.percentual_concluido or 0) for t in treinos) / len(treinos), 1
    )

def obter_treino_por_fase(email: str, db: Session):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario or not usuario.data_menstruacao:
        return {"erro": "Usuária sem data de menstruação cadastrada"}

    # Usar a mesma função que a IA usa para calcular a fase
    fase_info = calcular_fase_do_ciclo(str(usuario.data_menstruacao), usuario.duracao_ciclo or 28)
    fase = fase_info["fase"]
    sequencia_treinos = ["A", "B", "C", "D", "E"]

    treinos_feitos = (
        db.query(TreinoRealizado)
        .filter(TreinoRealizado.usuario_id == usuario.id)
        .filter(TreinoRealizado.fase == fase)
        .order_by(TreinoRealizado.data.desc())
        .all()
    )

    hoje = date.today()
    treino_hoje = next((t for t in treinos_feitos if t.data == hoje), None)

    if treino_hoje:
        proximo_treino = treino_hoje.treino
    else:
        if not treinos_feitos:
            proximo_treino = "A"
        else:
            ultimo = treinos_feitos[0].treino
            idx = sequencia_treinos.index(ultimo)
            proximo_treino = sequencia_treinos[(idx + 1) % len(sequencia_treinos)]

    tabela_por_fase = {
        "Menstruação": "fase_1_menstruacao",
        "Folicular": "fase_2_folicular",
        "Ovulatória": "fase_3_ovulatoria",
        "Lútea": "fase_4_tpm",
    }
    
    nome_tabela = tabela_por_fase.get(fase)
    if not nome_tabela:
        return {"erro": f"Tabela não encontrada para a fase '{fase}'"}

    # CORREÇÃO: Usar comparação exata em vez de ILIKE com %
    query = text(f"""
        SELECT * FROM {nome_tabela}
        WHERE tipo_treino = :tipo
        ORDER BY exercicio
    """)

    # CORREÇÃO: Passar apenas o valor exato, sem % no início e fim
    resultados = db.execute(query, {"tipo": proximo_treino}).fetchall()
    exercicios = [dict(row._mapping) for row in resultados]

    # Remover duplicados pelo nome do exercício
    exercicios_unicos = {}
    for ex in exercicios:
        nome = ex.get("exercicio")
        if nome and nome not in exercicios_unicos:
            exercicios_unicos[nome] = ex

    exercicios = list(exercicios_unicos.values())

    return {
        "fase": fase,
        "tipo_treino": proximo_treino,
        "exercicios": exercicios,
        "fase_info": fase_info  # Incluir informações completas da fase
    }
