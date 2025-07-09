import os
import traceback
from dotenv import load_dotenv
from openai import OpenAI  # novo client

load_dotenv()

# Inicializa o client com a chave e organização
client = OpenAI(
    api_key="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",
    organization=os.getenv("OPENAI_ORG_ID")
)

def formatar_historico_conversas(historico: list) -> str:
    if not historico:
        return "Ainda não houve conversas anteriores com essa usuária."
    return "\n".join([
        f"- Pergunta: {h.get('pergunta', '')}\n  Resposta: {h.get('resposta', '')}"
        for h in historico[-3:]  # últimos 3
    ])

def gerar_resposta_ia(pergunta: str, contexto: dict) -> str:
    fase = contexto.get("fase_atual", "fase desconhecida")
    descricao = contexto.get("descricao", "")
    percentual_atual = contexto.get("percentual_atual", 0)
    percentual_anterior = contexto.get("percentual_anterior", 0)
    sentimentos_lista = contexto.get("sentimentos_anteriores", [])
    sentimentos = ", ".join(sentimentos_lista) if sentimentos_lista else "nenhum registrado"
    historico_formatado = formatar_historico_conversas(contexto.get("historico", []))

    prompt_contexto = f"""
Fase atual: {fase}
Descrição da fase: {descricao}
Treinos concluídos nessa fase (mês atual): {percentual_atual}%
Treinos concluídos nessa fase no mês anterior: {percentual_anterior}%
Sentimentos anteriores registrados nessa fase: {sentimentos}

Histórico recente de conversas com a usuária:
{historico_formatado}
"""

    prompt = f"""
Você é uma coach motivacional focada no bem-estar feminino, treinos e fases do ciclo menstrual.

Use o contexto abaixo para responder à pergunta da usuária de forma acolhedora, clara, inspiradora e prática.

{prompt_contexto}

Regras importantes:
- Se a usuária ainda não treinou (percentual atual = 0), motive com empatia e sugira atividades leves e acessíveis como alongamento, caminhada ou respiração consciente.
- Se o percentual atual estiver maior que o anterior, elogie e destaque a evolução.
- Se os percentuais forem iguais ou baixos, oriente com leveza e reforce o autocuidado.
- Use linguagem amigável, como se estivesse incentivando uma amiga próxima.
- Inclua um emoji relacionado à fase do ciclo (ex: 🌑 🌒 🌕 🌘) se possível.
- A resposta deve ser curta, empática e com no máximo 5 linhas.

Pergunta da usuária:
{pergunta}

Responda como uma coach emocionalmente inteligente, com foco no bem-estar integral.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "Você é uma assistente especialista em treinos e saúde do ciclo menstrual. Seu tom é empático, acolhedor e motivacional."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.75,
            max_tokens=600
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print("❌ ERRO ao gerar resposta da IA:")
        traceback.print_exc()
        return f"Erro ao gerar resposta da IA: {str(e)}"
