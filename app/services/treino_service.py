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
    if not usuario:
        return {"erro": "Usuária não encontrada"}
    
    if not usuario.data_menstruacao:
        return {"erro": "Usuária sem data de menstruação cadastrada"}

    # Usar a mesma função que a IA usa para calcular a fase
    # Nota: Sempre fazemos uma nova consulta à base para garantir que temos os dados mais recentes
    db.refresh(usuario)  # Garante que temos os dados mais atualizados do usuário
    
    fase_info = calcular_fase_do_ciclo(str(usuario.data_menstruacao), usuario.duracao_ciclo or 28)
    fase = fase_info["fase"]
    print(f"DEBUG: Fase calculada: '{fase}'")
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
        # Adicionando versões sem acento para garantir compatibilidade
        "Menstruacao": "fase_1_menstruacao",
        "Ovulatoria": "fase_3_ovulatoria",
        "Lutea": "fase_4_tpm",
    }
    
    nome_tabela = tabela_por_fase.get(fase)
    print(f"DEBUG: Fase: '{fase}', Tabela mapeada: '{nome_tabela}'")
    if not nome_tabela:
        return {"erro": f"Tabela não encontrada para a fase '{fase}'"}

    # Consulta flexível: buscar por tipo_treino usando ILIKE e busca parcial
    query = text(f"""
        SELECT * FROM {nome_tabela}
        WHERE tipo_treino ILIKE :tipo
        ORDER BY exercicio
    """)
    try:
        resultados = db.execute(query, {"tipo": f"%{proximo_treino}%"}).fetchall()
        print(f"DEBUG: Número de resultados obtidos: {len(resultados)}")
        if resultados:
            primeiro_resultado = dict(resultados[0]._mapping)
            print(f"DEBUG: Exemplo de resultado - Colunas disponíveis: {list(primeiro_resultado.keys())}")
            print(f"DEBUG: Exemplo de resultado - Valores: {primeiro_resultado}")
    except Exception as e:
        print(f"ERRO na consulta SQL: {str(e)}")
        return {"erro": f"Erro ao consultar treinos: {str(e)}"}
    def limpar_unicode(texto):
        import unicodedata
        if isinstance(texto, str):
            try:
                return unicodedata.normalize("NFKC", texto)
            except Exception:
                return texto
        return texto
    exercicios = []
    for row in resultados:
        linha = {}
        for chave, valor in row._mapping.items():
            linha[chave] = limpar_unicode(valor)
        exercicios.append(linha)

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

def usuario_tem_treino_concluido_hoje(db: Session, usuario_id: int) -> bool:
    """
    Verifica se a usuária já concluiu algum treino no dia atual.
    Um treino é considerado concluído quando percentual_concluido > 0.
    
    Args:
        db: Session do banco de dados
        usuario_id: ID da usuária
        
    Returns:
        bool: True se a usuária já concluiu algum treino hoje, False caso contrário
    """
    hoje = date.today()
    treino_hoje = db.query(TreinoRealizado).filter(
        TreinoRealizado.usuario_id == usuario_id,
        TreinoRealizado.data == hoje,
        TreinoRealizado.percentual_concluido > 0  # Verifica se realmente concluiu alguma parte do treino
    ).first()
    
    return treino_hoje is not None
