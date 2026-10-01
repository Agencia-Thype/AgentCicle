from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.models.sqlalchemy_models import Usuario, TreinoRealizado
from app.services.ciclo_service import calcular_fase_do_ciclo
from app.utils.datas import hoje_brasilia

SEQUENCIA_TREINOS = ["A", "B", "C", "D", "E"]

TABELA_POR_FASE = {
    "Menstruação": "fase_1_menstruacao",
    "Folicular": "fase_2_folicular",
    "Ovulatória": "fase_3_ovulatoria",
    "Lútea": "fase_4_tpm",
    # Versões sem acento para compatibilidade com dados legados.
    "Menstruacao": "fase_1_menstruacao",
    "Ovulatoria": "fase_3_ovulatoria",
    "Lutea": "fase_4_tpm",
}


def _letra_tipo_treino(tipo_treino: str | None) -> str | None:
    """Extrai A-E tanto de ``B`` quanto de ``TREINO B - ...``."""
    if not tipo_treino:
        return None

    valor = tipo_treino.strip().upper()
    if valor in SEQUENCIA_TREINOS:
        return valor
    if valor.startswith("TREINO ") and len(valor) > 7:
        letra = valor[7]
        if letra in SEQUENCIA_TREINOS:
            return letra
    return None


def obter_tipos_treino_disponiveis(db: Session, fase: str) -> list[str]:
    """Retorna somente as letras de treino que realmente existem na fase."""
    nome_tabela = TABELA_POR_FASE.get(fase)
    if not nome_tabela:
        return []

    try:
        # Savepoint: no Postgres uma consulta que falha aborta a transação
        # inteira, e o check-in do treino (que roda na mesma sessão) cairia com
        # 500 logo depois. Assim só esta consulta é desfeita.
        with db.begin_nested():
            resultados = db.execute(
                text(f"SELECT DISTINCT tipo_treino FROM {nome_tabela} WHERE tipo_treino IS NOT NULL")
            ).scalars().all()
    except SQLAlchemyError:
        # Mantém os testes/bancos antigos funcionais enquanto ainda não possuem
        # as tabelas de catálogo. Em produção elas sempre existem.
        return []

    encontrados = {_letra_tipo_treino(tipo) for tipo in resultados}
    return [tipo for tipo in SEQUENCIA_TREINOS if tipo in encontrados]


def definir_treino_do_dia(db: Session, usuario_id: int, fase: str) -> str:
    """
    Treino que a usuária deve fazer hoje - é um só por dia.

    Se já houve check-in hoje, é esse treino (mesmo que a fase tenha virado);
    senão, o próximo da sequência A-E dentro da fase atual. /treino-dia e
    /treino-dia/concluir usam esta mesma regra, para a API não aceitar pontuar
    outro treino no mesmo dia.
    """
    registro_hoje = (
        db.query(TreinoRealizado)
        .filter(TreinoRealizado.usuario_id == usuario_id, TreinoRealizado.data == hoje_brasilia())
        .order_by(TreinoRealizado.id)
        .first()
    )
    if registro_hoje:
        return registro_hoje.treino

    ultimo = (
        db.query(TreinoRealizado)
        .filter(TreinoRealizado.usuario_id == usuario_id, TreinoRealizado.fase == fase)
        .order_by(TreinoRealizado.data.desc(), TreinoRealizado.id.desc())
        .first()
    )
    tipos_disponiveis = obter_tipos_treino_disponiveis(db, fase) or SEQUENCIA_TREINOS

    if not ultimo or ultimo.treino not in tipos_disponiveis:
        return tipos_disponiveis[0]

    idx = tipos_disponiveis.index(ultimo.treino)
    return tipos_disponiveis[(idx + 1) % len(tipos_disponiveis)]


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


def buscar_exercicios_por_tipo(db: Session, nome_tabela: str, tipo_treino: str):
    """Busca somente o grupo A-E solicitado, independentemente do texto descritivo."""
    tipo = tipo_treino.strip().upper()
    query = text(f"""
        SELECT * FROM {nome_tabela}
        WHERE UPPER(TRIM(tipo_treino)) = :tipo
           OR UPPER(TRIM(tipo_treino)) LIKE :tipo_descritivo
           OR UPPER(TRIM(tipo_treino)) LIKE :tipo_barra
        ORDER BY exercicio
    """)
    return db.execute(
        query,
        {
            "tipo": tipo,
            "tipo_descritivo": f"TREINO {tipo} -%",
            "tipo_barra": f"TREINO {tipo}/%",
        },
    ).fetchall()

def obter_treino_por_fase(email: str, db: Session):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        return {"erro": "Usuária não encontrada"}
    
    if not usuario.data_menstruacao:
        return {"erro": "Usuária sem data de menstruação cadastrada"}

    # Usar a mesma função que a IA usa para calcular a fase
    # Nota: Sempre fazemos uma nova consulta à base para garantir que temos os dados mais recentes
    db.refresh(usuario)  # Garante que temos os dados mais atualizados do usuário
    
    fase_info = calcular_fase_do_ciclo(
        str(usuario.data_menstruacao), usuario.duracao_ciclo, duracao_menstruacao=usuario.duracao_menstruacao
    )
    fase = fase_info["fase"]
    print(f"DEBUG: Fase calculada: '{fase}'")
    proximo_treino = definir_treino_do_dia(db, usuario.id, fase)

    nome_tabela = TABELA_POR_FASE.get(fase)
    print(f"DEBUG: Fase: '{fase}', Tabela mapeada: '{nome_tabela}'")
    if not nome_tabela:
        return {"erro": f"Tabela não encontrada para a fase '{fase}'"}

    # Aceita os dois formatos existentes no banco ("B" e "TREINO B - ..."),
    # sem confundir a letra com palavras como "body" ou "membros".
    try:
        resultados = buscar_exercicios_por_tipo(db, nome_tabela, proximo_treino)
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
    hoje = hoje_brasilia()
    treino_hoje = db.query(TreinoRealizado).filter(
        TreinoRealizado.usuario_id == usuario_id,
        TreinoRealizado.data == hoje,
        TreinoRealizado.percentual_concluido > 0  # Verifica se realmente concluiu alguma parte do treino
    ).first()
    
    return treino_hoje is not None
