from datetime import datetime, date
from statistics import median
from typing import Optional, Union
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.sqlalchemy_models import Usuario, DiarioCiclo
from app.utils.datas import hoje_brasilia


DURACAO_CICLO_PADRAO = 28
DURACAO_MENSTRUACAO_PADRAO = 5
# Do dia seguinte à ovulação até a véspera da próxima menstruação. É a parte
# mais estável do ciclo; quem estica ou encolhe com a duração é a folicular.
DURACAO_FASE_LUTEA = 14
# A gravidez é possível de 5 dias antes da ovulação até 1 dia depois (ACOG).
DIAS_FERTEIS_ANTES_DA_OVULACAO = 5
DIAS_FERTEIS_DEPOIS_DA_OVULACAO = 1

MENSAGENS_DAS_FASES = {
    "Menstruação": "Fase reflexiva 🌑",
    "Folicular": "Fase dinâmica 🌒",
    "Ovulatória": "Fase expansiva 🌕",
    "Lútea": "Fase criativa 🌘",
}


def normalizar_duracao_ciclo(duracao_ciclo) -> int:
    """Duração ausente ou absurda (erro de digitação, média corrompida) vale 28."""
    if not duracao_ciclo or duracao_ciclo < 10 or duracao_ciclo > 60:
        return DURACAO_CICLO_PADRAO
    return duracao_ciclo


def dividir_ciclo_em_fases(
    duracao_ciclo: int = DURACAO_CICLO_PADRAO,
    duracao_menstruacao: int = DURACAO_MENSTRUACAO_PADRAO,
) -> dict:
    """
    Divide o ciclo em fases, em dias contados a partir de 1 (o dia 1 é o
    primeiro dia da menstruação).

    A ovulação é estimada contando 14 dias para trás a partir da próxima
    menstruação (dia = duração - 14), e não por proporção do ciclo:

        ciclo  menstruação  folicular  ovulação  lútea
        21     1-5          6          7         8-21
        28     1-5          6-13       14        15-28
        35     1-5          6-20       21        22-35

    Em ciclos curtos demais para caber menstruação + 14 dias de lútea, a
    ovulação fica no dia seguinte à menstruação e a lútea encurta. Todo dia do
    ciclo pertence a uma fase - os treinos dependem dela.
    """
    duracao_ciclo = normalizar_duracao_ciclo(duracao_ciclo)
    menstruacao = max(1, min(duracao_menstruacao or DURACAO_MENSTRUACAO_PADRAO, duracao_ciclo - 2))
    ovulacao = max(duracao_ciclo - DURACAO_FASE_LUTEA, menstruacao + 1)

    fases = [("Menstruação", 1, menstruacao)]
    if ovulacao - 1 > menstruacao:
        fases.append(("Folicular", menstruacao + 1, ovulacao - 1))
    fases.append(("Ovulatória", ovulacao, ovulacao))
    fases.append(("Lútea", ovulacao + 1, duracao_ciclo))

    return {
        "duracao_ciclo": duracao_ciclo,
        "fases": [{"fase": nome, "inicio": inicio, "fim": fim} for nome, inicio, fim in fases],
        "dia_ovulacao": ovulacao,
        "janela_fertil": {
            "inicio": max(1, ovulacao - DIAS_FERTEIS_ANTES_DA_OVULACAO),
            "fim": min(duracao_ciclo, ovulacao + DIAS_FERTEIS_DEPOIS_DA_OVULACAO),
        },
    }


def calcular_fase_do_ciclo(
    data_menstruacao: Union[str, date, None],
    duracao_ciclo: int = DURACAO_CICLO_PADRAO,
    data_referencia: Optional[date] = None,
    duracao_menstruacao: Optional[int] = None,
):
    """
    Calcula a fase do ciclo em `data_referencia` (hoje, se não informada) com
    base na data da última menstruação.
    """
    duracao_ciclo = normalizar_duracao_ciclo(duracao_ciclo)

    if data_menstruacao is None:
        return {
            "fase": "Desconhecida",
            "mensagem": "Data da menstruação não cadastrada",
            "dias_desde_menstruacao": 0,
            "dia_do_ciclo": None,
            "duracao_ciclo": duracao_ciclo,
        }

    inicio = (
        datetime.strptime(data_menstruacao, "%Y-%m-%d").date()
        if isinstance(data_menstruacao, str)
        else data_menstruacao
    )
    referencia = data_referencia or hoje_brasilia()
    dias_passados = (referencia - inicio).days % duracao_ciclo
    dia_do_ciclo = dias_passados + 1

    divisao = dividir_ciclo_em_fases(
        duracao_ciclo, duracao_menstruacao or DURACAO_MENSTRUACAO_PADRAO
    )
    fases = divisao["fases"]
    indice = next(i for i, f in enumerate(fases) if f["inicio"] <= dia_do_ciclo <= f["fim"])
    atual = fases[indice]
    janela = divisao["janela_fertil"]

    return {
        "fase": atual["fase"],
        "mensagem": MENSAGENS_DAS_FASES[atual["fase"]],
        "dias_desde_menstruacao": dias_passados,
        # Dia do ciclo como a usuária conta: o primeiro dia de menstruação é
        # o dia 1, não o dia 0.
        "dia_do_ciclo": dia_do_ciclo,
        "duracao_ciclo": duracao_ciclo,
        "inicio_fase": atual["inicio"],
        "fim_fase": atual["fim"],
        # Depois da lútea o ciclo recomeça na menstruação.
        "proxima_fase": fases[(indice + 1) % len(fases)]["fase"],
        "dias_para_proxima_fase": atual["fim"] - dia_do_ciclo + 1,
        "duracao_menstruacao": fases[0]["fim"],
        "dia_ovulacao": divisao["dia_ovulacao"],
        "janela_fertil": janela,
        "em_janela_fertil": janela["inicio"] <= dia_do_ciclo <= janela["fim"],
        "fases": fases,
    }


# Registros de menstruação a menos dias que isto um do outro são dias do mesmo
# sangramento (ou diário preenchido durante ele), não um ciclo novo.
INTERVALO_MINIMO_ENTRE_CICLOS = 10
CICLOS_PARA_A_MEDIANA = 6
MINIMO_DE_CICLOS_PARA_APRENDER = 3


def duracao_ciclo_pelo_historico(datas_de_menstruacao) -> Optional[int]:
    """
    Duração típica do ciclo pelos inícios de menstruação registrados: mediana
    dos últimos 6 ciclos. Devolve None com menos de 3 ciclos - aí vale o que a
    usuária informou no Perfil.
    """
    inicios = []
    for data in sorted(set(datas_de_menstruacao)):
        if not inicios or (data - inicios[-1]).days >= INTERVALO_MINIMO_ENTRE_CICLOS:
            inicios.append(data)

    ciclos = [(b - a).days for a, b in zip(inicios, inicios[1:])]
    # Um intervalo enorme é um mês em que ela não registrou, não um ciclo.
    ciclos = [c for c in ciclos if c <= 60][-CICLOS_PARA_A_MEDIANA:]
    if len(ciclos) < MINIMO_DE_CICLOS_PARA_APRENDER:
        return None
    return round(median(ciclos))


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

    # Aprende a duração do ciclo pelo histórico. Só entram registros de
    # menstruação: o diário de sintomas dos outros dias não marca ciclo novo.
    db.flush()
    historico = (
        db.query(DiarioCiclo.data)
        .filter(DiarioCiclo.user_id == usuario.id, DiarioCiclo.fase == "Menstruação")
        .all()
    )
    aprendida = duracao_ciclo_pelo_historico([linha.data for linha in historico])
    if aprendida:
        usuario.duracao_ciclo = aprendida
    elif not usuario.duracao_ciclo:  # Se for o primeiro registro, define duração padrão
        usuario.duracao_ciclo = DURACAO_CICLO_PADRAO

    # Calcula fase atual
    fase = calcular_fase_do_ciclo(data_inicio, usuario.duracao_ciclo, duracao_menstruacao=usuario.duracao_menstruacao)

    db.commit()

    return {
        "mensagem": "Menstruação registrada com sucesso",
        "data_registrada": data_inicio,
        "nova_duracao_media": usuario.duracao_ciclo,
        "fase_atual": fase
    }