"""
Rotina de cuidados: suplementos, vitaminas, medicamentos e hidratação.

A agenda não é gravada: as doses previstas de um dia saem dos itens cadastrados
(frequência, dias, horários, início e fim). Só o que a usuária tomou vira
linha, em doses_rotina. Assim editar um horário muda a agenda na hora, sem
precisar recriar nada.
"""
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.rotina_models import ConfigHidratacaoRequest, ItemRotinaRequest
from app.models.sqlalchemy_models import (
    AguaRegistro,
    ConfigHidratacao,
    DoseRotina,
    ItemRotina,
    TreinoRealizado,
    Usuario,
)
from app.utils.datas import agora_brasilia, hoje_brasilia

META_AGUA_PADRAO_ML = 2000
LEMBRETES_AGUA_PADRAO = ["09:00", "11:00", "14:00", "16:00", "19:00"]
# Dose que passou do horário há mais que isso aparece como atrasada.
TOLERANCIA_ATRASO = timedelta(minutes=30)
# Quantos dias para trás as sequências ("5 dias seguidos") olham.
JANELA_SEQUENCIA_DIAS = 90


# --------------------------------------------------------------------- itens

def dia_da_semana(dia: date) -> int:
    """0 = domingo ... 6 = sábado, como no app. O date.weekday() começa na segunda."""
    return (dia.weekday() + 1) % 7


def item_previsto_no_dia(item: ItemRotina, dia: date) -> bool:
    """
    Se o item tem dose nesse dia. Não olha `ativo`: um item excluído é
    encerrado ontem, e os dias em que ele valia continuam no histórico.
    """
    if item.data_inicio and dia < item.data_inicio:
        return False
    if item.data_fim and dia > item.data_fim:
        return False
    if item.frequencia == "dias_especificos":
        return dia_da_semana(dia) in (item.dias_semana or [])
    return True


def estoque_baixo(item: ItemRotina) -> bool:
    return bool(
        item.controle_estoque
        and item.estoque_atual is not None
        and item.estoque_atual <= (item.estoque_alerta or 0)
    )


def serializar_item(item: ItemRotina) -> dict:
    return {
        "id": item.id,
        "nome": item.nome,
        "categoria": item.categoria,
        "dosagem": item.dosagem,
        "frequencia": item.frequencia,
        "dias_semana": item.dias_semana or [],
        "horarios": item.horarios or [],
        "data_inicio": item.data_inicio.isoformat() if item.data_inicio else None,
        "data_fim": item.data_fim.isoformat() if item.data_fim else None,
        "observacoes": item.observacoes,
        "indicado_medico": bool(item.indicado_medico),
        "lembrete_ativo": bool(item.lembrete_ativo),
        "controle_estoque": bool(item.controle_estoque),
        "estoque_atual": item.estoque_atual,
        "estoque_alerta": item.estoque_alerta,
        "estoque_baixo": estoque_baixo(item),
    }


def itens_da_usuaria(db: Session, usuario_id: int, incluir_inativos: bool = False) -> List[ItemRotina]:
    query = db.query(ItemRotina).filter(ItemRotina.usuario_id == usuario_id)
    if not incluir_inativos:
        query = query.filter(ItemRotina.ativo == 1)
    return query.order_by(ItemRotina.id).all()


def _aplicar_dados(item: ItemRotina, dados: ItemRotinaRequest) -> None:
    item.nome = dados.nome
    item.categoria = dados.categoria
    item.dosagem = dados.dosagem
    item.frequencia = dados.frequencia
    item.dias_semana = dados.dias_semana
    item.horarios = dados.horarios
    item.data_inicio = dados.data_inicio
    item.data_fim = dados.data_fim
    item.observacoes = dados.observacoes
    item.indicado_medico = int(dados.indicado_medico)
    item.lembrete_ativo = int(dados.lembrete_ativo)
    item.controle_estoque = int(dados.controle_estoque)
    item.estoque_atual = dados.estoque_atual
    item.estoque_alerta = dados.estoque_alerta


def criar_item(db: Session, usuario: Usuario, dados: ItemRotinaRequest) -> ItemRotina:
    item = ItemRotina(usuario_id=usuario.id, ativo=1, created_at=agora_brasilia())
    _aplicar_dados(item, dados)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def atualizar_item(db: Session, item: ItemRotina, dados: ItemRotinaRequest) -> ItemRotina:
    _aplicar_dados(item, dados)
    db.commit()
    db.refresh(item)
    return item


def excluir_item(db: Session, item: ItemRotina) -> None:
    ontem = hoje_brasilia() - timedelta(days=1)
    item.ativo = 0
    item.data_fim = min(item.data_fim, ontem) if item.data_fim else ontem
    db.commit()


# --------------------------------------------------------------------- doses

def _doses_tomadas(db: Session, usuario_id: int, inicio: date, fim: date) -> Set[Tuple[int, date, str]]:
    doses = db.query(DoseRotina).filter(
        DoseRotina.usuario_id == usuario_id,
        DoseRotina.data >= inicio,
        DoseRotina.data <= fim,
    ).all()
    return {(dose.item_id, dose.data, dose.horario) for dose in doses}


def _momento(dia: date, horario: str) -> datetime:
    hora, minuto = map(int, horario.split(":"))
    return datetime.combine(dia, time(hora, minuto))


def _status_dose(tomada: bool, dia: date, horario: str, agora: datetime) -> str:
    if tomada:
        return "tomado"
    if agora - _momento(dia, horario) > TOLERANCIA_ATRASO:
        return "atrasado"
    return "pendente"


def agenda_do_dia(db: Session, usuario: Usuario, dia: date) -> List[dict]:
    """Doses previstas no dia, em ordem de horário, com o status de cada uma."""
    itens = [
        item for item in itens_da_usuaria(db, usuario.id, incluir_inativos=True)
        if item_previsto_no_dia(item, dia)
    ]
    tomadas = _doses_tomadas(db, usuario.id, dia, dia)
    agora = agora_brasilia()

    doses = []
    for item in itens:
        for horario in item.horarios or []:
            tomada = (item.id, dia, horario) in tomadas
            doses.append({
                "item_id": item.id,
                "nome": item.nome,
                "categoria": item.categoria,
                "dosagem": item.dosagem,
                "horario": horario,
                "status": _status_dose(tomada, dia, horario, agora),
                "estoque_baixo": estoque_baixo(item),
            })
    doses.sort(key=lambda dose: (dose["horario"], dose["nome"]))
    return doses


def resumo_do_dia(db: Session, usuario: Usuario, dia: Optional[date] = None) -> dict:
    dia = dia or hoje_brasilia()
    doses = agenda_do_dia(db, usuario, dia)

    # Próxima: a primeira pendente; se só sobraram atrasadas, a primeira delas.
    proxima = next((d for d in doses if d["status"] == "pendente"), None)
    proxima = proxima or next((d for d in doses if d["status"] == "atrasado"), None)
    if proxima:
        minutos = (_momento(dia, proxima["horario"]) - agora_brasilia()).total_seconds() // 60
        proxima = {**proxima, "minutos": int(minutos)}

    return {
        "data": dia.isoformat(),
        "doses": doses,
        "total": len(doses),
        "tomadas": sum(1 for dose in doses if dose["status"] == "tomado"),
        "proxima": proxima,
        "agua": agua_do_dia(db, usuario, dia),
    }


def _validar_dose(item: ItemRotina, dia: date, horario: str) -> None:
    if dia > hoje_brasilia():
        raise ValueError("Não dá para marcar uma dose de um dia que ainda não chegou.")
    if not item_previsto_no_dia(item, dia) or horario not in (item.horarios or []):
        raise ValueError("Esse item não tem dose nesse dia e horário.")


def registrar_dose(db: Session, usuario: Usuario, item: ItemRotina, dia: date, horario: str) -> bool:
    """Marca a dose como tomada. Devolve False se ela já estava marcada."""
    _validar_dose(item, dia, horario)
    existente = db.query(DoseRotina).filter_by(item_id=item.id, data=dia, horario=horario).first()
    if existente:
        return False

    db.add(DoseRotina(
        usuario_id=usuario.id, item_id=item.id, data=dia, horario=horario, tomado_em=agora_brasilia()
    ))
    if item.controle_estoque and item.estoque_atual is not None:
        item.estoque_atual = max(0, item.estoque_atual - 1)
    db.commit()
    return True


def desfazer_dose(db: Session, usuario: Usuario, item: ItemRotina, dia: date, horario: str) -> bool:
    """Desmarca a dose. Devolve False se ela não estava marcada."""
    existente = db.query(DoseRotina).filter_by(
        usuario_id=usuario.id, item_id=item.id, data=dia, horario=horario
    ).first()
    if not existente:
        return False

    db.delete(existente)
    if item.controle_estoque and item.estoque_atual is not None:
        item.estoque_atual += 1
    db.commit()
    return True


# ---------------------------------------------------------------------- água

def meta_sugerida(db: Session, usuario: Usuario, dia: date) -> dict:
    """
    Sugestão de meta: 35 ml por kg (ou 2 L sem peso cadastrado), com 500 ml a
    mais nos dias de treino. É ponto de partida; a usuária pode trocar.
    """
    peso = float(usuario.peso_atual) if usuario.peso_atual else None
    if peso:
        meta = int(peso * 35 / 100 + 0.5) * 100
        motivo = f"35 ml por kg ({peso:g} kg)"
    else:
        meta = META_AGUA_PADRAO_ML
        motivo = "média para adultas; cadastre seu peso para personalizar"
    meta = min(max(meta, 1500), 4000)

    treinou = db.query(TreinoRealizado).filter(
        TreinoRealizado.usuario_id == usuario.id,
        TreinoRealizado.data == dia,
        TreinoRealizado.percentual_concluido > 0,
    ).first() is not None
    if treinou:
        meta += 500
        motivo += " + 500 ml pelo treino de hoje"

    return {"meta_ml": meta, "motivo": motivo}


def _config(db: Session, usuario_id: int) -> Optional[ConfigHidratacao]:
    return db.query(ConfigHidratacao).filter(ConfigHidratacao.usuario_id == usuario_id).first()


def _meta_do_dia(db: Session, usuario: Usuario, dia: date) -> int:
    config = _config(db, usuario.id)
    if config and config.meta_ml:
        return config.meta_ml
    return meta_sugerida(db, usuario, dia)["meta_ml"]


def _totais_agua(db: Session, usuario_id: int, inicio: date, fim: date) -> Dict[date, int]:
    linhas = db.query(AguaRegistro.data, func.sum(AguaRegistro.ml)).filter(
        AguaRegistro.usuario_id == usuario_id,
        AguaRegistro.data >= inicio,
        AguaRegistro.data <= fim,
    ).group_by(AguaRegistro.data).all()
    return {dia: int(total or 0) for dia, total in linhas}


def _sequencia(status_por_dia: List[Tuple[date, Optional[bool]]], hoje: date) -> int:
    """
    Dias seguidos cumpridos, do mais recente para trás.

    `status_por_dia` vem do mais recente ao mais antigo: True cumpriu, False
    não cumpriu, None não havia nada previsto (não conta nem quebra). Hoje só
    conta se já cumpriu - o dia não acabou, então ainda não quebra a sequência.
    """
    sequencia = 0
    for dia, cumpriu in status_por_dia:
        if cumpriu is None:
            continue
        if cumpriu:
            sequencia += 1
        elif dia == hoje:
            continue
        else:
            break
    return sequencia


def sequencia_agua(db: Session, usuario: Usuario, meta_ml: int) -> int:
    hoje = hoje_brasilia()
    inicio = hoje - timedelta(days=JANELA_SEQUENCIA_DIAS - 1)
    totais = _totais_agua(db, usuario.id, inicio, hoje)
    dias = [hoje - timedelta(days=i) for i in range(JANELA_SEQUENCIA_DIAS)]
    return _sequencia([(dia, totais.get(dia, 0) >= meta_ml) for dia in dias], hoje)


def agua_do_dia(db: Session, usuario: Usuario, dia: Optional[date] = None) -> dict:
    dia = dia or hoje_brasilia()
    registros = db.query(AguaRegistro).filter(
        AguaRegistro.usuario_id == usuario.id, AguaRegistro.data == dia
    ).order_by(AguaRegistro.created_at, AguaRegistro.id).all()
    total = sum(registro.ml for registro in registros)

    config = _config(db, usuario.id)
    sugestao = meta_sugerida(db, usuario, dia)
    meta = config.meta_ml if config and config.meta_ml else sugestao["meta_ml"]

    return {
        "data": dia.isoformat(),
        "total_ml": total,
        "meta_ml": meta,
        "faltam_ml": max(meta - total, 0),
        "percentual": min(round(total / meta * 100), 100) if meta else 0,
        "registros": [
            {
                "id": registro.id,
                "ml": registro.ml,
                "hora": registro.created_at.strftime("%H:%M") if registro.created_at else None,
            }
            for registro in registros
        ],
        "lembretes": config.lembretes if config and config.lembretes is not None else LEMBRETES_AGUA_PADRAO,
        "lembretes_ativos": bool(config.lembretes_ativos) if config else True,
        "meta_personalizada": bool(config and config.meta_ml),
        "meta_sugerida": sugestao,
        "sequencia_dias": sequencia_agua(db, usuario, meta),
    }


def registrar_agua(db: Session, usuario: Usuario, ml: int, dia: Optional[date] = None) -> AguaRegistro:
    dia = dia or hoje_brasilia()
    if dia > hoje_brasilia():
        raise ValueError("Não dá para registrar água de um dia que ainda não chegou.")
    registro = AguaRegistro(usuario_id=usuario.id, data=dia, ml=ml, created_at=agora_brasilia())
    db.add(registro)
    db.commit()
    return registro


def salvar_config_hidratacao(db: Session, usuario: Usuario, dados: ConfigHidratacaoRequest) -> ConfigHidratacao:
    config = _config(db, usuario.id)
    if not config:
        config = ConfigHidratacao(usuario_id=usuario.id)
        db.add(config)
    config.meta_ml = dados.meta_ml
    config.lembretes = dados.lembretes
    config.lembretes_ativos = int(dados.lembretes_ativos)
    db.commit()
    return config


# ----------------------------------------------------------------- histórico

def historico(db: Session, usuario: Usuario, dias: int = 7) -> dict:
    """Adesão às doses e hidratação dos últimos `dias`, com as sequências."""
    hoje = hoje_brasilia()
    agora = agora_brasilia()
    janela = max(dias, JANELA_SEQUENCIA_DIAS)
    inicio = hoje - timedelta(days=janela - 1)

    itens = itens_da_usuaria(db, usuario.id, incluir_inativos=True)
    tomadas = _doses_tomadas(db, usuario.id, inicio, hoje)
    totais = _totais_agua(db, usuario.id, inicio, hoje)
    meta = _meta_do_dia(db, usuario, hoje)

    por_dia = []
    status_rotina = []
    por_item = {item.id: {"previstas": 0, "tomadas": 0} for item in itens}

    for i in range(janela):
        dia = hoje - timedelta(days=i)
        previstas = [
            (item, horario)
            for item in itens if item_previsto_no_dia(item, dia)
            for horario in item.horarios or []
        ]
        feitas = [(item, horario) for item, horario in previstas if (item.id, dia, horario) in tomadas]
        status_rotina.append((dia, len(feitas) == len(previstas) if previstas else None))

        if i >= dias:
            continue

        for item, horario in previstas:
            por_item[item.id]["previstas"] += 1
            if (item.id, dia, horario) in tomadas:
                por_item[item.id]["tomadas"] += 1

        agua = totais.get(dia, 0)
        por_dia.append({
            "data": dia.isoformat(),
            "doses_previstas": len(previstas),
            "doses_tomadas": len(feitas),
            "adesao": round(len(feitas) / len(previstas) * 100) if previstas else None,
            # Hoje, só o que já passou da hora conta como esquecido.
            "esquecidas": [
                {"item_id": item.id, "nome": item.nome, "horario": horario}
                for item, horario in previstas
                if _status_dose((item.id, dia, horario) in tomadas, dia, horario, agora) == "atrasado"
            ],
            "agua_ml": agua,
            "bateu_meta_agua": agua >= meta,
        })

    previstas_total = sum(d["doses_previstas"] for d in por_dia)
    tomadas_total = sum(d["doses_tomadas"] for d in por_dia)

    return {
        "dias": por_dia,
        "itens": [
            {
                "item_id": item.id,
                "nome": item.nome,
                "categoria": item.categoria,
                "previstas": por_item[item.id]["previstas"],
                "tomadas": por_item[item.id]["tomadas"],
                "adesao": round(por_item[item.id]["tomadas"] / por_item[item.id]["previstas"] * 100)
                if por_item[item.id]["previstas"] else None,
            }
            for item in itens if por_item[item.id]["previstas"]
        ],
        "resumo": {
            "adesao": round(tomadas_total / previstas_total * 100) if previstas_total else None,
            "doses_previstas": previstas_total,
            "doses_tomadas": tomadas_total,
            "meta_agua_ml": meta,
            "dias_meta_agua": sum(1 for d in por_dia if d["bateu_meta_agua"]),
            "media_agua_ml": round(sum(d["agua_ml"] for d in por_dia) / len(por_dia)) if por_dia else 0,
        },
        "sequencia_rotina": _sequencia(status_rotina, hoje),
        "sequencia_agua": _sequencia(
            [(hoje - timedelta(days=i), totais.get(hoje - timedelta(days=i), 0) >= meta) for i in range(janela)],
            hoje,
        ),
    }
