# app/services/treino_service.py
from datetime import datetime

def calcular_fase(data_menstrucao):
    fases = [
        ("Menstruação", 0, 5),
        ("Folicular", 6, 12),
        ("Ovulatória", 13, 16),
        ("Lútea", 17, 28)
    ]
    hoje = datetime.now().date()
    inicio = datetime.strptime(data_menstrucao, "%Y-%m-%d").date()
    dias = (hoje - inicio).days % 28

    for nome, ini, fim in fases:
        if ini <= dias <= fim:
            return nome
    return "Desconhecida"

def obter_treino_por_fase(data_menstrucao: str):
    fase = calcular_fase(data_menstrucao)

    treinos = {
        "Menstruação": {
            "treino": "Treino A",
            "exercicios": ["Alongamento leve", "Respiração diafragmática", "Yoga suave"],
            "video": "https://exemplo.com/video/treinoA"
        },
        "Folicular": {
            "treino": "Treino B",
            "exercicios": ["Agachamento", "Afundo alternado", "Prancha com apoio"],
            "video": "https://exemplo.com/video/treinoB"
        },
        "Ovulatória": {
            "treino": "Treino C",
            "exercicios": ["Polichinelo", "Burpee", "Escalador"],
            "video": "https://exemplo.com/video/treinoC"
        },
        "Lútea": {
            "treino": "Treino D",
            "exercicios": ["Caminhada", "Bicicleta leve", "Alongamento"],
            "video": "https://exemplo.com/video/treinoD"
        }
    }

    return {
        "fase": fase,
        **treinos.get(fase, {"treino": "N/A", "exercicios": [], "video": ""})
    }
