from sqlalchemy.orm import Session
from app.models.kegel_models import NivelKegel, ExercicioKegel, TreinoKegelResponse
from app.data.kegel_exercises import get_exercicios_por_nivel, get_all_exercicios
from app.models.sqlalchemy_models import Usuario, ProgressoKegel, KegelDiario
from app.utils.datas import hoje_brasilia
from typing import Optional, List
from datetime import datetime, timedelta

# Um dia completo de Kegel vale isso; cada exercício leva a sua fração.
PONTOS_KEGEL_DIA = 10

def obter_treino_kegel(db: Session, email: str, nivel_override: Optional[NivelKegel] = None) -> dict:
    """
    Retorna o treino de Kegel do dia baseado no nível do usuário.

    Args:
        db: Session do banco de dados
        email: Email do usuário
        nivel_override: Nível opcional para forçar um nível específico

    Returns:
        dict: Dicionário com os exercícios de Kegel do dia
    """
    # Buscar usuário
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        return {"erro": "Usuária não encontrada"}

    # Determinar nível do usuário
    if nivel_override:
        nivel = nivel_override
    elif usuario.nivel_kegel:
        nivel = usuario.nivel_kegel
    else:
        nivel = NivelKegel.INICIANTE

    # Buscar exercícios do nível
    exercicios = get_exercicios_por_nivel(nivel)

    if not exercicios:
        return {"erro": f"Nenhum exercício encontrado para o nível {nivel}"}

    # Buscar progresso do usuário neste nível
    progresso_nivel = verificar_progresso_nivel(db, usuario.id, nivel)

    # Determinar quais exercícios estão concluídos
    exercicios_concluidos = progresso_nivel.get("exercicios_concluidos", [])

    progresso_usuario = {
        "nivel_atual": nivel,
        "total_exercicios": len(exercicios),
        "exercicios_concluidos": exercicios_concluidos,
        "nivel_concluido": progresso_nivel.get("concluido", False),
        "percentual_conclusao": progresso_nivel.get("percentual", 0)
    }

    return {
        "nivel": nivel,
        "exercicios": [ex.dict() for ex in exercicios],
        "progresso_usuario": progresso_usuario
    }

def verificar_progresso_nivel(db: Session, usuario_id: int, nivel: NivelKegel) -> dict:
    """
    Verifica o progresso do usuário em um nível específico.

    Args:
        db: Session do banco de dados
        usuario_id: ID do usuário
        nivel: Nível a ser verificado

    Returns:
        dict: Informações sobre o progresso no nível
    """
    exercicios = get_exercicios_por_nivel(nivel)
    ids_exercicios = [ex.id for ex in exercicios]

    # Buscar registros de progresso para este nível
    progressos = db.query(ProgressoKegel).filter(
        ProgressoKegel.usuario_id == usuario_id,
        ProgressoKegel.nivel == nivel,
        ProgressoKegel.concluido == 1
    ).all()

    exercicios_concluidos = [p.exercicio_id for p in progressos]

    # Calcular percentual de conclusão
    percentual = 0
    if ids_exercicios:
        percentual = (len(exercicios_concluidos) / len(ids_exercicios)) * 100

    # Nível está concluído se todos os exercícios foram completados
    nivel_concluido = len(exercicios_concluidos) >= len(ids_exercicios)

    return {
        "exercicios_concluidos": exercicios_concluidos,
        "percentual": percentual,
        "concluido": nivel_concluido
    }

def verificar_niveis_disponiveis(db: Session, usuario_id: int, nivel_atual: NivelKegel) -> dict:
    """
    Verifica quais níveis estão desbloqueados para o usuário.
    O usuário pode praticar qualquer nível, mas só desbloqueia oficialmente
    o próximo nível se completar pelo menos um exercício do nível atual.

    Args:
        db: Session do banco de dados
        usuario_id: ID do usuário
        nivel_atual: Nível atual do usuário

    Returns:
        dict: Status de desbloqueio de cada nível
    """
    niveis_status = {
        NivelKegel.INICIANTE: {
            "disponivel": True,  # Sempre disponível
            "bloqueado": False,
            "motivo": None
        },
        NivelKegel.INTERMEDIARIO: {
            "disponivel": True,  # Pode praticar, mas pode estar bloqueado para progressão
            "bloqueado": True,
            "motivo": "Complete pelo menos um exercício do nível Iniciante para desbloquear"
        },
        NivelKegel.AVANCADO: {
            "disponivel": True,  # Pode praticar, mas pode estar bloqueado para progressão
            "bloqueado": True,
            "motivo": "Complete pelo menos um exercício do nível Intermediário para desbloquear"
        }
    }

    # Verificar se completou pelo menos um exercício do iniciante
    progresso_iniciante = verificar_progresso_nivel(db, usuario_id, NivelKegel.INICIANTE)
    if len(progresso_iniciante["exercicios_concluidos"]) > 0:
        niveis_status[NivelKegel.INTERMEDIARIO]["bloqueado"] = False
        niveis_status[NivelKegel.INTERMEDIARIO]["motivo"] = None

    # Verificar se completou pelo menos um exercício do intermediário
    progresso_intermediario = verificar_progresso_nivel(db, usuario_id, NivelKegel.INTERMEDIARIO)
    if len(progresso_intermediario["exercicios_concluidos"]) > 0:
        niveis_status[NivelKegel.AVANCADO]["bloqueado"] = False
        niveis_status[NivelKegel.AVANCADO]["motivo"] = None

    return niveis_status

def obter_status_niveis(db: Session, usuario_id: int) -> dict:
    """
    Retorna o status completo de todos os níveis para o usuário.

    Args:
        db: Session do banco de dados
        usuario_id: ID do usuário

    Returns:
        dict: Status detalhado de cada nível
    """
    niveis_status = {}

    for nivel in [NivelKegel.INICIANTE, NivelKegel.INTERMEDIARIO, NivelKegel.AVANCADO]:
        progresso = verificar_progresso_nivel(db, usuario_id, nivel)
        exercicios = get_exercicios_por_nivel(nivel)

        niveis_status[nivel] = {
            "nome": nivel.replace("_", " ").title(),
            "total_exercicios": len(exercicios),
            "exercicios_concluidos": len(progresso["exercicios_concluidos"]),
            "percentual_conclusao": progresso["percentual"],
            "concluido": progresso["concluido"],
            "exercicios_nomes": [ex.nome for ex in exercicios],
            "exercicios_ids": [ex.id for ex in exercicios],
            "exercicios_completados_ids": progresso["exercicios_concluidos"]
        }

    return niveis_status


def pontuar_exercicio_do_dia(db: Session, usuario: Usuario, nivel: NivelKegel, exercicio_id: str) -> int:
    """
    Dá os pontos de um exercício de Kegel concluído hoje. Não faz commit.

    Cada exercício pontua uma vez por dia. O dia vale PONTOS_KEGEL_DIA no total,
    repartido entre os exercícios do nível (3 exercícios: 3 + 3 + 4); passado
    o total, trocar de nível não soma mais nada.
    """
    hoje = hoje_brasilia()
    registros_hoje = db.query(KegelDiario).filter(
        KegelDiario.usuario_id == usuario.id,
        KegelDiario.data == hoje
    ).all()

    if any(r.exercicio_id == exercicio_id for r in registros_hoje):
        return 0

    total_do_nivel = len(get_exercicios_por_nivel(nivel)) or 1
    exercicios_no_dia = len(registros_hoje) + 1
    pontos_ate_agora = sum(r.pontos or 0 for r in registros_hoje)
    alvo = min(PONTOS_KEGEL_DIA, (PONTOS_KEGEL_DIA * exercicios_no_dia) // total_do_nivel)
    pontos = max(0, alvo - pontos_ate_agora)

    db.add(KegelDiario(
        usuario_id=usuario.id,
        data=hoje,
        nivel=NivelKegel(nivel).value,
        exercicio_id=exercicio_id,
        pontos=pontos,
        created_at=datetime.now()
    ))
    usuario.pontos_totais = (usuario.pontos_totais or 0) + pontos
    return pontos


def registrar_conclusao_exercicio(db: Session, email: str, nivel: NivelKegel, exercicio_id: str, percentual: float) -> dict:
    """
    Registra a conclusão de um exercício de Kegel.

    Args:
        db: Session do banco de dados
        email: Email do usuário
        nivel: Nível do exercício
        exercicio_id: ID do exercício concluído
        percentual: Percentual de conclusão (0-100)

    Returns:
        dict: Confirmação do registro
    """
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        return {"erro": "Usuária não encontrada"}

    if exercicio_id not in {ex.id for ex in get_exercicios_por_nivel(nivel)}:
        return {"erro": "Exercício não pertence a este nível"}

    # Pontos do dia antes do progresso: o progresso abaixo é vitalício e não
    # muda ao repetir um exercício já concluído em outro dia.
    pontos_ganhos = pontuar_exercicio_do_dia(db, usuario, nivel, exercicio_id) if percentual >= 100 else 0

    # Verificar se já existe registro
    progresso_existente = db.query(ProgressoKegel).filter(
        ProgressoKegel.usuario_id == usuario.id,
        ProgressoKegel.exercicio_id == exercicio_id,
        ProgressoKegel.nivel == nivel
    ).first()

    agora = datetime.now()

    if progresso_existente:
        # Atualizar registro existente se o percentual for maior
        if percentual > progresso_existente.percentual_conclusao:
            progresso_existente.percentual_conclusao = percentual
            progresso_existente.data_conclusao = agora

            # Marcar como concluído se atingiu 100%
            if percentual >= 100:
                progresso_existente.concluido = 1
    else:
        # Criar novo registro
        novo_progresso = ProgressoKegel(
            usuario_id=usuario.id,
            nivel=nivel,
            exercicio_id=exercicio_id,
            data_conclusao=agora,
            percentual_conclusao=percentual,
            concluido=1 if percentual >= 100 else 0
        )
        db.add(novo_progresso)

    db.commit()

    # Verificar se completou o nível e pode avançar
    progresso_nivel = verificar_progresso_nivel(db, usuario.id, nivel)

    resposta = {
        "mensagem": "Exercício registrado com sucesso",
        "percentual": percentual,
        "pontos_ganhos": pontos_ganhos,
        "pontos_totais": usuario.pontos_totais,
        "nivel_concluido": progresso_nivel["concluido"],
        "exercicios_concluidos": len(progresso_nivel["exercicios_concluidos"]),
        "total_exercicios": len(get_exercicios_por_nivel(nivel))
    }

    # Se completou o nível, verificar se pode avançar
    if progresso_nivel["concluido"]:
        niveis_disponiveis = verificar_niveis_disponiveis(db, usuario.id, nivel)

        if nivel == NivelKegel.INICIANTE and niveis_disponiveis[NivelKegel.INTERMEDIARIO]:
            resposta["proximo_nivel"] = NivelKegel.INTERMEDIARIO
            resposta["mensagem_nivel"] = "Parabéns! Você completou o nível Iniciante e desbloqueou o Intermediário!"
        elif nivel == NivelKegel.INTERMEDIARIO and niveis_disponiveis[NivelKegel.AVANCADO]:
            resposta["proximo_nivel"] = NivelKegel.AVANCADO
            resposta["mensagem_nivel"] = "Parabéns! Você completou o nível Intermediário e desbloqueou o Avançado!"

    return resposta


def atualizar_nivel_kegel(db: Session, email: str, novo_nivel: NivelKegel) -> dict:
    """
    Atualiza o nível de Kegel do usuário.
    O usuário pode escolher qualquer nível para praticar.
    Esta função apenas atualiza a preferência atual do usuário.

    Args:
        db: Session do banco de dados
        email: Email do usuário
        novo_nivel: Novo nível a ser atribuído

    Returns:
        dict: Confirmação da atualização com informações sobre desbloqueio
    """
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        return {"erro": "Usuária não encontrada"}

    nivel_anterior = usuario.nivel_kegel or NivelKegel.INICIANTE
    usuario.nivel_kegel = novo_nivel
    db.commit()
    db.refresh(usuario)

    # Verificar status dos níveis para informar ao usuário
    niveis_status = verificar_niveis_disponiveis(db, usuario.id, novo_nivel)

    resposta = {
        "mensagem": f"Nível atualizado para {novo_nivel.value}",
        "nivel_anterior": nivel_anterior.value if isinstance(nivel_anterior, NivelKegel) else nivel_anterior,
        "novo_nivel": novo_nivel.value,
        "pode_praticar": True,  # Sempre pode praticar
        "info_desbloqueio": {}
    }

    # Adicionar informações sobre desbloqueio de níveis
    for nivel, status in niveis_status.items():
        resposta["info_desbloqueio"][nivel] = {
            "bloqueado": status["bloqueado"],
            "motivo": status["motivo"]
        }

    return resposta



def obter_info_niveis() -> dict:
    """
    Retorna informações sobre os níveis de Kegel disponíveis.

    Returns:
        dict: Informações sobre cada nível
    """
    todos_exercicios = get_all_exercicios()

    info_niveis = {}
    for nivel in NivelKegel:
        exercicios = todos_exercicios.get(nivel, [])
        info_niveis[nivel] = {
            "nome": nivel.replace("_", " ").title(),
            "total_exercicios": len(exercicios),
            "exercicios": [ex.nome for ex in exercicios]
        }

    return info_niveis
