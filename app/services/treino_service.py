from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
import re
from typing import List, Optional
from sqlalchemy import inspect, text
from app.models.sqlalchemy_models import Usuario, TreinoRealizado
from app.services.ciclo_service import calcular_fase_do_ciclo
from app.utils.datas import hoje_brasilia

SEQUENCIA_TREINOS = ["A", "B", "C", "D", "E"]

TABELA_POR_FASE = {
    "Menstruação": "fase_1_menstruacao",
    "Folicular": "fase_2_folicular",
    "Ovulatória": "fase_3_ovulatoria",
    "Lútea": "fase_4_tpm",
    # Versões sem acento, por compatibilidade
    "Menstruacao": "fase_1_menstruacao",
    "Ovulatoria": "fase_3_ovulatoria",
    "Lutea": "fase_4_tpm",
}

# "A", "TREINO A/quadríceps", "TREINO B - membros..." -> letra do treino.
_LETRA_DO_TREINO = re.compile(r"^\s*(?:treino\s*)?([a-e])(?![a-zà-ÿ])", re.IGNORECASE)


def letra_do_treino(tipo_treino: Optional[str]) -> Optional[str]:
    """Extrai a letra (A-E) do começo do tipo_treino das tabelas de fase."""
    if not tipo_treino:
        return None
    encontrado = _LETRA_DO_TREINO.match(tipo_treino)
    return encontrado.group(1).upper() if encontrado else None


def treinos_da_fase(db: Session, fase: str) -> List[str]:
    """
    Letras dos treinos cadastrados na tabela da fase, em ordem.

    Cada fase tem a sua quantidade: Menstruação e Lútea têm A-C, Folicular e
    Ovulatória A-E. Sem a tabela (ex.: banco de testes), vale a sequência A-E.
    """
    nome_tabela = TABELA_POR_FASE.get(fase)
    if not nome_tabela or not inspect(db.get_bind()).has_table(nome_tabela):
        return SEQUENCIA_TREINOS

    tipos = db.execute(text(f"SELECT DISTINCT tipo_treino FROM {nome_tabela}")).scalars().all()
    letras = sorted({letra for letra in map(letra_do_treino, tipos) if letra})
    return letras or SEQUENCIA_TREINOS


def definir_treino_do_dia(db: Session, usuario_id: int, fase: str) -> str:
    """
    Treino que a usuária deve fazer hoje - é um só por dia.

    Se já houve check-in hoje, é esse treino (mesmo que a fase tenha virado);
    senão, o próximo entre os treinos cadastrados da fase atual. /treino-dia e
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
    # A sequência é a da fase: em Menstruação/Lútea, depois do C vem o A (antes
    # vinham D e E, que nessas fases não existem - treino vazio ou tabela toda).
    sequencia = treinos_da_fase(db, fase)
    if not ultimo or ultimo.treino not in sequencia:
        return sequencia[0]

    idx = sequencia.index(ultimo.treino)
    return sequencia[(idx + 1) % len(sequencia)]


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
    proximo_treino = definir_treino_do_dia(db, usuario.id, fase)

    
    nome_tabela = TABELA_POR_FASE.get(fase)
    print(f"DEBUG: Fase: '{fase}', Tabela mapeada: '{nome_tabela}'")
    if not nome_tabela:
        return {"erro": f"Tabela não encontrada para a fase '{fase}'"}

    # Só as linhas do treino do dia, pela letra exata. O ILIKE '%A%' de antes
    # casava qualquer tipo com a letra no nome ("membros superiores" tem "e"),
    # e o app recebia exercícios de vários treinos misturados.
    query = text(f"SELECT * FROM {nome_tabela} ORDER BY exercicio")
    try:
        resultados = [
            row for row in db.execute(query).fetchall()
            if letra_do_treino(row._mapping.get("tipo_treino")) == proximo_treino
        ]
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
