from datetime import datetime, date
from typing import Union
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.sqlalchemy_models import Usuario, DiarioCiclo


def calcular_fase_do_ciclo(data_menstruacao: Union[str, date], duracao_ciclo: int = 28):

    """
    Calcula a fase atual do ciclo com base na data da última menstruação.
    """
    # Verificar se a data da menstruação está presente
    if data_menstruacao is None:
        return {
            "fase": "Desconhecida",
            "mensagem": "Data da menstruação não cadastrada",
            "dias_desde_menstruacao": 0,
        }
        
    if duracao_ciclo < 21 or duracao_ciclo > 35:
        duracao_ciclo = 28

    # Define as faixas de dias para cada fase
    fase_menstruacao = (0, round(duracao_ciclo * 0.2))
    fase_folicular = (fase_menstruacao[1] + 1, round(duracao_ciclo * 0.45))
    fase_ovulatoria = (fase_folicular[1] + 1, round(duracao_ciclo * 0.57))
    fase_lutea = (fase_ovulatoria[1] + 1, duracao_ciclo)

    fases = [
        ("Menstruação", *fase_menstruacao, "Fase reflexiva 🌑"),
        ("Folicular", *fase_folicular, "Fase dinâmica 🌒"),
        ("Ovulatória", *fase_ovulatoria, "Fase expansiva 🌕"),
        ("Lútea", *fase_lutea, "Fase criativa 🌘"),
    ]
    
    print(f"DEBUG: Intervalos de dias para fases: Menstruação={fase_menstruacao}, Folicular={fase_folicular}, Ovulatória={fase_ovulatoria}, Lútea={fase_lutea}")

    hoje = datetime.now().date()
    inicio = (
        datetime.strptime(data_menstruacao, "%Y-%m-%d").date()
        if isinstance(data_menstruacao, str)
        else data_menstruacao
    )

    dias_passados = (hoje - inicio).days % duracao_ciclo
    
    # Recuperar a fase com base nos dias passados
    for nome, inicio_dia, fim_dia, msg in fases:
        if inicio_dia <= dias_passados <= fim_dia:
            return {
                "fase": nome,
                "mensagem": msg,
                "dias_desde_menstruacao": dias_passados,
                "inicio_fase": inicio_dia,
                "fim_fase": fim_dia,
            }

    return {
        "fase": "Desconhecida",
        "mensagem": "Não foi possível calcular a fase",
        "dias_desde_menstruacao": dias_passados,
    }

def registrar_nova_menstruacao(db: Session, email: str, data_inicio: date):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise Exception("Usuária não encontrada")

    # Verifica se já existe registro nesta data
    existente = db.query(DiarioCiclo).filter(
        DiarioCiclo.user_id == usuario.id,
        DiarioCiclo.data == data_inicio
    ).first()

    if existente:
        existente.fase = "Menstruação"  # Atualiza a fase
    else:
        novo_registro = DiarioCiclo(
            user_id=usuario.id,
            data=data_inicio,  # Usar apenas data, sem data_inicio
            created_at=datetime.utcnow(),
            fase="Menstruação"
        )
        db.add(novo_registro)

    # Atualiza a data principal do perfil
    usuario.data_menstruacao = data_inicio

    # Recalcula duração média do ciclo com base no histórico
    historico = (
        db.query(DiarioCiclo)
        .filter(DiarioCiclo.user_id == usuario.id)
        .order_by(DiarioCiclo.data.asc())
        .all()
    )

    if len(historico) >= 2:
        duracoes = [
            (historico[i + 1].data - historico[i].data).days
            for i in range(len(historico) - 1)
        ]
        nova_media = round(sum(duracoes) / len(duracoes))
        usuario.duracao_ciclo = nova_media
    elif not usuario.duracao_ciclo:  # Se for o primeiro registro, define duração padrão
        usuario.duracao_ciclo = 28

    # Calcula fase atual
    fase = calcular_fase_do_ciclo(data_inicio, usuario.duracao_ciclo)

    db.commit()

    return {
        "mensagem": "Menstruação registrada com sucesso",
        "data_registrada": data_inicio,
        "nova_duracao_media": usuario.duracao_ciclo,
        "fase_atual": fase
    }