from datetime import datetime

def calcular_fase_do_ciclo(data_menstruacao: str):
    fases = [
        ("Menstruação", 0, 5, "Fase reflexiva 🌑"),
        ("Folicular", 6, 12, "Fase dinâmica 🌒"),
        ("Ovulatória", 13, 16, "Fase expansiva 🌕"),
        ("Lútea", 17, 28, "Fase criativa 🌘")
    ]

    hoje = datetime.now().date()
    inicio = datetime.strptime(data_menstruacao, "%Y-%m-%d").date()
    dias_passados = (hoje - inicio).days % 28

    for nome, inicio_dia, fim_dia, msg in fases:
        if inicio_dia <= dias_passados <= fim_dia:
            return {"fase": nome, "mensagem": msg}

    return {"fase": "Desconhecida", "mensagem": "Não foi possível calcular a fase"}
