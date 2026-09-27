from sqlalchemy.orm import Session
from datetime import datetime
import os
from app.models.sqlalchemy_models import Usuario
from app.models.conversaIA_models import ConversaIA
from app.services.llm_service import gerar_resposta_ia
from sqlalchemy import text
import json
from app.services.treino_service import definir_treino_do_dia, TABELA_POR_FASE
from app.utils.cache import get_from_cache, set_in_cache

def buscar_treinos_por_fase(db: Session, fase: str, tipo_treino: str | None = None):
    nome_tabela = TABELA_POR_FASE.get(fase)
    if not nome_tabela:
        return []

    if tipo_treino:
        tipo = tipo_treino.strip().upper()
        query = text(f"""
            SELECT exercicio, tipo_treino FROM {nome_tabela}
            WHERE UPPER(TRIM(tipo_treino)) = :tipo
               OR UPPER(TRIM(tipo_treino)) LIKE :tipo_descritivo
               OR UPPER(TRIM(tipo_treino)) LIKE :tipo_barra
            ORDER BY exercicio
        """)
        resultados = db.execute(
            query,
            {
                "tipo": tipo,
                "tipo_descritivo": f"TREINO {tipo} -%",
                "tipo_barra": f"TREINO {tipo}/%",
            },
        ).fetchall()
    else:
        query = text(f"SELECT exercicio, tipo_treino FROM {nome_tabela} ORDER BY exercicio")
        resultados = db.execute(query).fetchall()
    return [dict(row._mapping) for row in resultados]


def responder_com_RAG(db: Session, user_id: int, pergunta: str, contexto: dict) -> str:
    fase = contexto.get("fase_atual", "fase desconhecida")
    tipo_treino = definir_treino_do_dia(db, user_id, fase)
    exercicios = buscar_treinos_por_fase(db, fase, tipo_treino)

    lista_exercicios = "\n".join([
        f"- {ex['exercicio']}" for ex in exercicios
    ]) or "Nenhum exercício disponível."

    prompt = f"""
Você é uma coach motivacional especializada em bem-estar feminino e treinos adaptados ao ciclo menstrual.

A usuária está atualmente na fase: {fase}.
Estes são os treinos disponíveis para ela neste momento:
{lista_exercicios}

Sua missão é acolher, orientar e motivar essa mulher com base nos treinos reais acima e no contexto da fase atual do ciclo.

Regras importantes:
- Fale **apenas** sobre assuntos relacionados ao ciclo menstrual, treinos, bem-estar e autocuidado.
- Baseie suas sugestões **somente nos exercícios listados acima** — nunca crie treinos novos.
- Sua linguagem deve ser leve, inspiradora e empática, como de uma amiga que acompanha de perto a jornada da usuária.
- Use emojis com carinho (🌙✨💪💕) quando fizer sentido.
- A resposta deve ter **no máximo 5 linhas** e soar como um incentivo verdadeiro.

Pergunta da usuária:
{pergunta}

Responda com carinho e inteligência emocional, como uma coach que entende profundamente o ciclo e as necessidades da mulher.
"""

    contexto["prompt"] = prompt
    resposta = gerar_resposta_ia(pergunta, contexto)
    return resposta


def registrar_conversa(
    db: Session,
    user_id: int,
    pergunta: str,
    resposta: str,
    contexto: dict,
    fase: str = "",
    tema: str = "",
    emocional: bool = False,
    treino_recomendado: str = ""
):
    nova = ConversaIA(
        user_id=user_id,
        data=datetime.utcnow(),
        pergunta=pergunta,
        resposta=resposta,
        contexto=contexto,
        fase=fase,
        tema=tema,
        resposta_emocional=emocional,
        treino_recomendado=treino_recomendado
    )
    db.add(nova)
    db.commit()


def buscar_historico_conversas(db: Session, user_id: int, limite: int = 5):
    return db.query(ConversaIA) \
        .filter(ConversaIA.user_id == user_id) \
        .order_by(ConversaIA.data.desc()) \
        .limit(limite).all()


def _mensagem_entrada_local(contexto: dict, tipo: str) -> str:
    fase_atual = contexto.get("fase_atual") or "atual"
    percentual_atual = contexto.get("percentual_atual", 0)

    if tipo == "balao":
        if percentual_atual:
            return "Vamos manter seu ritmo hoje?"
        return "Como você está se sentindo hoje?"

    if percentual_atual:
        return (
            f"Bem-vinda à sua fase {fase_atual}. "
            f"Você já concluiu {percentual_atual}% dos treinos desta fase; siga no seu ritmo."
        )
    return (
        f"Bem-vinda à sua fase {fase_atual}. "
        "Hoje pode começar leve: um passo pequeno já conta."
    )


def gerar_mensagem_entrada_com_ia(db: Session, user_id: int, contexto: dict, tipo: str = "boas_vindas") -> str:
    cache_key = (
        f"ia_mensagem_entrada:{user_id}:{tipo}:"
        f"{contexto.get('fase_atual')}:{contexto.get('percentual_atual')}:{contexto.get('percentual_anterior')}"
    )
    cached = get_from_cache(cache_key)
    if cached:
        return cached

    cache_seconds = int(os.getenv("IA_MENSAGEM_ENTRADA_CACHE_SECONDS", "21600"))
    live_enabled = os.getenv("IA_MENSAGEM_ENTRADA_LIVE", "false").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
        "sim",
    )
    if not live_enabled:
        mensagem = _mensagem_entrada_local(contexto, tipo)
        set_in_cache(cache_key, mensagem, cache_seconds)
        return mensagem

    fase_atual = contexto.get("fase_atual")
    percentual_atual = contexto.get("percentual_atual", 0)
    percentual_anterior = contexto.get("percentual_anterior", 0)
    sentimentos = contexto.get("sentimentos_anteriores", [])
    descricao = contexto.get("descricao", "")

    if tipo == "boas_vindas":
        prompt = f"""
Você é uma coach motivacional especializada em bem-estar feminino.

A usuária está na fase: {fase_atual}.
Na fase anterior, ela concluiu {percentual_anterior}% dos treinos.
Nesta fase, já completou {percentual_atual}% dos treinos.

Sentimentos registrados recentemente: {', '.join(sentimentos) if sentimentos else 'nenhum'}.

Descrição da fase: {descricao}

Com base nisso, escreva uma **mensagem de boas-vindas curta e motivacional**.

🌸 Regras:
- Use uma linguagem inspiradora, feminina e acolhedora.
- Reconheça o progresso da usuária.
- Use emojis com leveza.
- Limite: **até 3 linhas**.
"""
        resposta = gerar_resposta_ia(prompt, contexto)
        set_in_cache(cache_key, resposta, cache_seconds)
        return resposta

    elif tipo == "balao":
        prompt = f"""
Você é uma coach carismática e afetuosa que acompanha a jornada da usuária no aplicativo.

Ela está na fase do ciclo: {fase_atual}.
Treinos recentes concluídos: {percentual_atual}%.
Sentimentos recentes: {', '.join(sentimentos) if sentimentos else 'nenhum'}.

Escreva uma frase **curta**, como um **balão de convite simpático**, com até **50 caracteres**, para chamar a usuária com doçura e leveza.

Exemplos:
- "Vamos treinar um pouquinho hoje? 💪✨"
- "Oi! Como você está se sentindo? 🌸"
- "Sua energia é linda. Vamos juntas? 💕"

🌙 Regras:
- Use linguagem acolhedora e amigável.
- Seja breve e gentil.
- Pode usar emojis se fizer sentido.
"""
        resposta = gerar_resposta_ia(prompt, contexto)
        set_in_cache(cache_key, resposta, cache_seconds)
        return resposta

    else:
        return "🌙 Estou me ajustando para te dar a melhor mensagem. Tente novamente!"
