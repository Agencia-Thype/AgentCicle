from app.models.sqlalchemy_models import Usuario
from sqlalchemy.orm import Session
from app.utils.cache import invalidate_cache


def atualizar_campos_status():
    """
    Atualiza todos os caches e formatos relacionados ao status de usuário.
    Deve ser chamada quando houver alteração no formato do dicionário de status.
    """
    # Limpar qualquer cache relacionado a status de usuário
    invalidate_cache_pattern("status_usuario_*")


def invalidate_cache_pattern(pattern: str):
    """
    Invalidar todos os caches que correspondem a um padrão.
    
    Args:
        pattern: Padrão para invalidação (por exemplo, "status_usuario_*")
    """
    invalidate_cache(pattern)


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
