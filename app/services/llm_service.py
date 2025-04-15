import os
import traceback
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

def gerar_resposta_ia(pergunta: str, contexto: dict) -> str:
    """
    Gera uma resposta empática com base no contexto da fase do ciclo,
    desempenho de treinos e sentimentos anteriores.
    """

    fase = contexto.get("fase_atual", "fase desconhecida")
    descricao = contexto.get("descricao", "")
    percentual_atual = contexto.get("percentual_atual", 0)
    percentual_anterior = contexto.get("percentual_anterior", 0)
    sentimentos = ", ".join(contexto.get("sentimentos_anteriores", [])) or "nenhum registrado"

    prompt_contexto = f"""
Fase atual: {fase}
Descrição da fase: {descricao}
Treinos concluídos nessa fase: {percentual_atual}%
Treinos concluídos nessa fase no mês anterior: {percentual_anterior}%
Sentimentos anteriores nessa fase: {sentimentos}
"""

    prompt = f"""
Você é uma coach motivacional focada no bem-estar feminino, treinos e fases do ciclo menstrual.

Use o contexto abaixo para responder a pergunta da usuária de forma acolhedora, clara, motivacional e prática.

{prompt_contexto}

Pergunta da usuária:
{pergunta}

Responda de forma humana e acolhedora, como se estivesse incentivando uma amiga. Dê sugestões que façam sentido para a fase do ciclo e o histórico dela.
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
