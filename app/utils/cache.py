"""
Utilitário para implementar cache simples no backend.
Isso reduz a carga no banco de dados para consultas frequentes.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, Optional

# Cache simples em memória
# { 'chave': (dados, timestamp_expiracao) }
_cache: Dict[str, Tuple[Any, datetime]] = {}

def get_from_cache(key: str) -> Optional[Any]:
    """
    Obtém um valor do cache se ainda for válido.
    
    Args:
        key: Chave do cache
        
    Returns:
        O valor armazenado ou None se não existir ou estiver expirado
    """
    if key not in _cache:
        return None
        
    valor, expira_em = _cache[key]
    if datetime.now() > expira_em:
        # Expirado, remove do cache
        del _cache[key]
        return None
        
    return valor

def set_in_cache(key: str, value: Any, ttl_seconds: int = 30) -> None:
    """
    Armazena um valor no cache com tempo de vida.
    
    Args:
        key: Chave do cache
        value: Valor a ser armazenado
        ttl_seconds: Tempo de vida em segundos (padrão: 30s)
    """
    expira_em = datetime.now() + timedelta(seconds=ttl_seconds)
    _cache[key] = (value, expira_em)

def invalidate_cache(key: str) -> None:
    """
    Invalida uma entrada específica do cache.
    
    Args:
        key: Chave do cache a ser invalidada
    """
    if key in _cache:
        del _cache[key]
