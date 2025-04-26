from sqlalchemy.orm import Session
from datetime import datetime
from app.models.sqlalchemy_models import Usuario
from app.models.conversaIA_models import ConversaIA
from app.services.llm_service import gerar_resposta_ia
from sqlalchemy import text
import json

def buscar_treinos_por_fase(db: Session, fase: str):
    tabela_por_fase = {
        "Menstruação": "fase_1_menstruacao",
        "Folicular": "fase_2_folicular",
        "Ovulatória": "fase_3_ovulatoria",
        "Lútea": "fase_4_tpm",
    }

    nome_tabela = tabela_por_fase.get(fase)
    if not nome_tabela:
        return []

    query = text(f"SELECT exercicio, tipo_treino FROM {nome_tabela}")
    resultados = db.execute(query).fetchall()
    return [dict(row._mapping) for row in resultados]


def responder_com_RAG(db: Session, user_id: int, pergunta: str, contexto: dict) -> str:
    fase = contexto.get("fase_atual", "fase desconhecida")
    exercicios = buscar_treinos_por_fase(db, fase)

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


def gerar_mensagem_entrada_com_ia(db: Session, user_id: int, contexto: dict, tipo: str = "boas_vindas") -> str:
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
        return gerar_resposta_ia(prompt, contexto)

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
        return gerar_resposta_ia(prompt, contexto)

    else:
        return "🌙 Estou me ajustando para te dar a melhor mensagem. Tente novamente!"
