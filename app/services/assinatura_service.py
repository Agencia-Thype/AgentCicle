from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.config import cobranca_ativa
from app.models.sqlalchemy_models import Usuario
from app.utils.cache import get_from_cache, set_in_cache, invalidate_cache

# Constante para TTL do cache
CACHE_TTL_SECONDS = 30  # 30 segundos de cache para status de assinatura


def garantir_chave_pode_pontuar(status: dict) -> dict:
    """
    Garantir que o status retornado pela verificação tenha a chave 'podePontuar'.
    Se não tiver, usa 'temAcesso' como valor padrão.
    
    Args:
        status: Dicionário com status do usuário
        
    Returns:
        dict: Status atualizado garantindo a presença da chave 'podePontuar'
    """
    if "podePontuar" not in status:
        status["podePontuar"] = status.get("temAcesso", False)
    return status


def status_acesso_livre() -> dict:
    """
    Status devolvido enquanto COBRANCA_ATIVA=false: acesso total, sem trial e
    sem assinatura. Nenhum campo sugere cobrança, porque o frontend não pode
    exibir preço nem paywall nesse modo (App Store 3.1.1 / Google Play).
    """
    return {
        "trialAtivo": False,
        "assinaturaAtiva": False,
        "temAcesso": True,
        "podePontuar": True,
        "podeUsarRecursosBasicos": True,
        "podeUsarPremium": True,
        "diasRestantesTrial": 0,
        "dataFimTrial": None,
        "dataFimAssinatura": None,
        "jaTeveAssinatura": False,
        "cobrancaAtiva": False,
        "statusTipo": "gratuito",
    }


def verificar_status_usuario(db: Session, usuario_id: int) -> dict:
    """
    Verifica o status de trial e assinatura do usuário.
    Implementa cache para reduzir consultas ao banco de dados.
    
    Args:
        db: Sessão do banco de dados
        usuario_id: ID do usuário
        
    Returns:
        dict: Status completo do usuário com informações de trial e assinatura
    """
    # App gratuito: ninguém perde acesso pelo fim do trial. Verificado antes do
    # cache para que um status salvo antes de desligar a cobrança não bloqueie.
    if not cobranca_ativa():
        return status_acesso_livre()

    # Verifica se já existe em cache
    cache_key = f"status_usuario_{usuario_id}"
    cached_status = get_from_cache(cache_key)
    if cached_status:
        # Retorna do cache se disponível (garantindo que tem a chave podePontuar)
        return garantir_chave_pode_pontuar(cached_status)
    
    # Busca do banco de dados se não estiver em cache
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        status = {
            "trialAtivo": False,
            "assinaturaAtiva": False,
            "temAcesso": False,
            "diasRestantesTrial": 0,
            "erro": "Usuário não encontrado"
        }
        return garantir_chave_pode_pontuar(status)
    
    agora = datetime.now()
    
    # Verifica se o usuário já teve assinatura anteriormente
    ja_teve_assinatura = usuario.data_inicio_assinatura is not None
    
    # Verifica se o trial está ativo (apenas se nunca teve assinatura)
    trial_ativo = False
    dias_restantes_trial = 0
    
    if not ja_teve_assinatura and usuario.data_fim_trial:
        if agora <= usuario.data_fim_trial:
            trial_ativo = True
            dias_restantes_trial = (usuario.data_fim_trial - agora).days
    
    # Verifica se a assinatura está ativa
    assinatura_ativa = False
    if usuario.assinatura_ativa and usuario.data_fim_assinatura:
        if agora <= usuario.data_fim_assinatura:
            assinatura_ativa = True
    
    # Usuário tem acesso se trial está ativo OU assinatura está ativa
    tem_acesso = trial_ativo or assinatura_ativa

    # Usuário pode usar recursos básicos se tiver qualquer tipo de acesso
    pode_usar_recursos_basicos = tem_acesso

    status = {
        "trialAtivo": trial_ativo,
        "assinaturaAtiva": assinatura_ativa,
        "temAcesso": tem_acesso,
        "podePontuar": tem_acesso,  # Usuário pode pontuar se tiver acesso ativo
        "podeUsarRecursosBasicos": pode_usar_recursos_basicos,  # Pode usar recursos básicos do app
        "diasRestantesTrial": dias_restantes_trial,
        "dataFimTrial": usuario.data_fim_trial.isoformat() if usuario.data_fim_trial else None,
        "dataFimAssinatura": usuario.data_fim_assinatura.isoformat() if usuario.data_fim_assinatura else None,
        "jaTeveAssinatura": ja_teve_assinatura  # Adicionado campo para informar se já teve assinatura
    }
    
    # Armazena em cache
    set_in_cache(cache_key, status, CACHE_TTL_SECONDS)
    
    return status


def ativar_trial(db: Session, usuario_id: int, dias: int = 7) -> dict:
    """
    Ativa o trial de X dias para o usuário.
    
    Args:
        db: Sessão do banco de dados
        usuario_id: ID do usuário
        dias: Número de dias do trial (padrão: 7)
        
    Returns:
        dict: Status após ativação do trial
    """
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        return {"sucesso": False, "erro": "Usuário não encontrado"}
    
    agora = datetime.now()
    data_fim_trial = agora + timedelta(days=dias)
    
    # Atualiza o usuário com as datas do trial
    usuario.data_criacao_conta = agora
    usuario.data_fim_trial = data_fim_trial
    
    db.commit()
    db.refresh(usuario)
    
    # Invalida o cache após alteração
    invalidate_cache(f"status_usuario_{usuario_id}")
    
    return {
        "sucesso": True,
        "mensagem": f"Trial de {dias} dias ativado com sucesso",
        "dataFimTrial": data_fim_trial.isoformat(),
        "status": verificar_status_usuario(db, usuario_id)
    }


def ativar_assinatura(db: Session, usuario_id: int, duracao_meses: int = 1) -> dict:
    """
    Ativa a assinatura premium para o usuário.
    Após a primeira assinatura, o trial nunca mais será considerado.
    
    Args:
        db: Sessão do banco de dados
        usuario_id: ID do usuário
        duracao_meses: Duração da assinatura em meses
        
    Returns:
        dict: Status após ativação da assinatura
    """
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        return {"sucesso": False, "erro": "Usuário não encontrado"}
    
    agora = datetime.now()
    
    # Se já tem data de fim, estender a partir dela se ainda estiver no futuro
    if usuario.data_fim_assinatura and usuario.data_fim_assinatura > agora:
        data_fim_assinatura = usuario.data_fim_assinatura + timedelta(days=30 * duracao_meses)
    else:
        # Caso contrário, começar a partir de agora
        data_fim_assinatura = agora + timedelta(days=30 * duracao_meses)
    
    # Ativa a assinatura
    usuario.assinatura_ativa = 1
    
    # Define a data de início da assinatura apenas se for a primeira vez
    primeira_assinatura = usuario.data_inicio_assinatura is None
    if primeira_assinatura:
        usuario.data_inicio_assinatura = agora
    
    usuario.data_fim_assinatura = data_fim_assinatura
    
    db.commit()
    db.refresh(usuario)
    
    # Invalida o cache após alteração
    invalidate_cache(f"status_usuario_{usuario_id}")
    
    return {
        "sucesso": True,
        "mensagem": f"Assinatura de {duracao_meses} meses ativada com sucesso",
        "dataFimAssinatura": data_fim_assinatura.isoformat(),
        "primeiraAssinatura": primeira_assinatura,
        "status": verificar_status_usuario(db, usuario_id)
    }


def cancelar_assinatura(db: Session, usuario_id: int) -> dict:
    """
    Cancela a assinatura premium do usuário.
    
    Args:
        db: Sessão do banco de dados
        usuario_id: ID do usuário
        
    Returns:
        dict: Status após cancelamento da assinatura
    """
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        return {"sucesso": False, "erro": "Usuário não encontrado"}
    
    # Cancela a assinatura
    usuario.assinatura_ativa = 0
    usuario.data_fim_assinatura = datetime.now()  # Define data fim como agora
    
    db.commit()
    db.refresh(usuario)
    
    # Invalida o cache após alteração
    invalidate_cache(f"status_usuario_{usuario_id}")
    
    return {
        "sucesso": True,
        "mensagem": "Assinatura cancelada com sucesso",
        "status": verificar_status_usuario(db, usuario_id)
    }


def verificar_se_pode_usar_recurso_premium(db: Session, usuario_id: int) -> bool:
    """
    Verifica se o usuário pode usar recursos premium.
    
    Args:
        db: Sessão do banco de dados
        usuario_id: ID do usuário
        
    Returns:
        bool: True se pode usar recursos premium, False caso contrário
    """
    status = verificar_status_usuario(db, usuario_id)
    return status["temAcesso"]


def get_status_por_email(db: Session, email: str) -> dict:
    """
    Obtém o status de assinatura do usuário pelo email.
    Implementa cache para evitar consultas frequentes.
    
    Args:
        db: Sessão do banco de dados
        email: Email do usuário
        
    Returns:
        dict: Status completo do usuário
    """
    # Verifica se já existe em cache
    cache_key = f"status_email_{email}"
    cached_status = get_from_cache(cache_key)
    if cached_status:
        # Retorna do cache se disponível
        return cached_status
    
    # Busca do banco de dados se não estiver em cache
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        return {
            "trialAtivo": False,
            "assinaturaAtiva": False,
            "temAcesso": False,
            "diasRestantesTrial": 0,
            "erro": "Usuário não encontrado"
        }
    
    status = verificar_status_usuario(db, usuario.id)
    
    # Armazena em cache
    set_in_cache(cache_key, status, CACHE_TTL_SECONDS)
    
    return status


def ativar_premium_por_email(db: Session, email: str, duracao_meses: int = 1) -> dict:
    """
    Ativa assinatura premium pelo email (para rotas de teste).
    
    Args:
        db: Sessão do banco de dados
        email: Email do usuário
        duracao_meses: Duração da assinatura em meses
        
    Returns:
        dict: Resultado da ativação
    """
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        return {"sucesso": False, "erro": "Usuário não encontrado"}
    
    return ativar_assinatura(db, usuario.id, duracao_meses)


def cancelar_premium_por_email(db: Session, email: str) -> dict:
    """
    Cancela assinatura premium pelo email (para rotas de teste).
    
    Args:
        db: Sessão do banco de dados
        email: Email do usuário
        
    Returns:
        dict: Resultado do cancelamento
    """
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        return {"sucesso": False, "erro": "Usuário não encontrado"}
    
    return cancelar_assinatura(db, usuario.id)


def calcular_proxima_verificacao(status: dict) -> datetime:
    """
    Calcula quando o status deve ser verificado novamente.
    
    Args:
        status: Status atual do usuário
        
    Returns:
        datetime: Data e hora para próxima verificação
    """
    agora = datetime.now()
    
    # Se tiver assinatura ativa, verificar semanalmente
    if status["assinaturaAtiva"]:
        return agora + timedelta(days=7)
    
    # Se estiver no trial, verificar diariamente
    if status["trialAtivo"]:
        return agora + timedelta(days=1)
    
    # Se já teve assinatura mas está expirada, verificar a cada 3 dias
    if status.get("jaTeveAssinatura", False):
        return agora + timedelta(days=3)
    
    # Se não tiver acesso e nunca teve assinatura, verificar a cada login (retorna agora mesmo)
    return agora


def obter_status_resumido(db: Session, usuario_id: int) -> dict:
    """
    Obtém um status resumido e otimizado para armazenamento no frontend.
    Inclui metadados para controle de expiração.
    
    Args:
        db: Sessão do banco de dados
        usuario_id: ID do usuário
        
    Returns:
        dict: Status resumido com metadados para controle de cache
    """
    status = verificar_status_usuario(db, usuario_id)
    
    # Adiciona metadados para controle de cache
    agora = datetime.now()
    proxima_verificacao = calcular_proxima_verificacao(status)
    
    status.update({
        "verificadoEm": agora.isoformat(),
        "proximaVerificacao": proxima_verificacao.isoformat(),
        "tempoValidoSegundos": int((proxima_verificacao - agora).total_seconds())
    })
    
    return status


def obter_status_login(db: Session, usuario_id: int) -> dict:
    """
    Função otimizada para uso durante login.
    Verifica o status e retorna informações completas com metadados para cache no frontend.
    
    Args:
        db: Sessão do banco de dados
        usuario_id: ID do usuário
        
    Returns:
        dict: Status completo com metadados de cache e informações adicionais
    """
    # Invalida qualquer cache existente para garantir dados atualizados no login
    invalidate_cache(f"status_usuario_{usuario_id}")
    
    # Obtém o status atualizado do banco de dados
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        return {
            "trialAtivo": False,
            "assinaturaAtiva": False,
            "temAcesso": False,
            "diasRestantesTrial": 0,
            "erro": "Usuário não encontrado",
            "verificadoEm": datetime.now().isoformat(),
            "proximaVerificacao": datetime.now().isoformat()
        }
    
    # Obtém o status resumido com metadados de cache
    status = obter_status_resumido(db, usuario_id)
    
    # Adiciona informações complementares para o frontend
    status.update({
        "nome": usuario.nome,
        "email": usuario.email,
        "ultimoLogin": datetime.now().isoformat(),
        "jaTeveAssinatura": usuario.data_inicio_assinatura is not None
    })
    
    # Adiciona mensagem informativa sobre o período baseado no status
    if not cobranca_ativa():
        status["mensagem"] = "Acesso completo liberado. Bom treino!"
        status["statusTipo"] = "gratuito"
        return status

    if status["assinaturaAtiva"]:
        status["mensagem"] = "Você possui uma assinatura ativa. Aproveite todos os recursos!"
        status["statusTipo"] = "premium"
    elif status["trialAtivo"]:
        status["mensagem"] = f"Você está no período de testes gratuito. Restam {status['diasRestantesTrial']} dias."
        status["statusTipo"] = "trial"
    else:
        if status["jaTeveAssinatura"]:
            status["mensagem"] = "Sua assinatura expirou. Renove agora para continuar usando todos os recursos!"
            status["statusTipo"] = "expirado"
        else:
            status["mensagem"] = "O período de testes expirou. Assine agora para continuar usando o app."
            status["statusTipo"] = "trial_expirado"
    
    return status
