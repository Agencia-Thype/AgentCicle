"""
Utilitário para logging avançado na aplicação.
Permite registrar logs estruturados com diferentes níveis de severidade.
"""
import logging
import json
import time
import inspect
from datetime import datetime
import os
import sys
from typing import Any, Dict, Optional

# Configuração básica do logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Logger principal da aplicação
logger = logging.getLogger("app")

# Níveis de log
INFO = logging.INFO
DEBUG = logging.DEBUG
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL

def _get_caller_info():
    """Obtém informações sobre quem chamou a função de log"""
    stack = inspect.stack()
    # O índice 2 representa o chamador da função que chamou _get_caller_info
    caller = stack[2]
    return {
        "file": os.path.basename(caller.filename),
        "line": caller.lineno,
        "function": caller.function
    }

def log_request(request, route: str, status_code: int, duration_ms: Optional[float] = None):
    """
    Registra informações sobre uma requisição HTTP.
    
    Args:
        request: Objeto de requisição do FastAPI
        route: Rota sendo acessada
        status_code: Código de status HTTP da resposta
        duration_ms: Duração da requisição em milissegundos (opcional)
    """
    try:
        # Obtém headers mais relevantes
        headers = {
            "user-agent": request.headers.get("user-agent", ""),
            "x-forwarded-for": request.headers.get("x-forwarded-for", ""),
            "referer": request.headers.get("referer", "")
        }
        
        # Obtém informações sobre o cliente
        client_host = request.client.host if request.client else "unknown"
        client_port = request.client.port if request.client else "unknown"
        
        log_data = {
            "type": "request",
            "timestamp": datetime.now().isoformat(),
            "route": route,
            "method": request.method,
            "path": request.url.path,
            "client": f"{client_host}:{client_port}",
            "status_code": status_code,
            "headers": headers
        }
        
        if duration_ms is not None:
            log_data["duration_ms"] = duration_ms
            
        logger.info(f"REQUEST: {json.dumps(log_data)}")
    except Exception as e:
        logger.error(f"Erro ao registrar log de requisição: {str(e)}")

def log_info(message: str, data: Optional[Dict[str, Any]] = None):
    """
    Registra uma mensagem de informação.
    
    Args:
        message: Mensagem de log
        data: Dados adicionais para o log (opcional)
    """
    caller = _get_caller_info()
    log_entry = {
        "message": message,
        "level": "INFO",
        "timestamp": datetime.now().isoformat(),
        "caller": caller
    }
    
    if data:
        log_entry["data"] = data
        
    logger.info(f"INFO: {json.dumps(log_entry)}")

def log_error(message: str, error: Optional[Exception] = None, data: Optional[Dict[str, Any]] = None):
    """
    Registra uma mensagem de erro.
    
    Args:
        message: Mensagem de erro
        error: Objeto de exceção (opcional)
        data: Dados adicionais para o log (opcional)
    """
    caller = _get_caller_info()
    log_entry = {
        "message": message,
        "level": "ERROR",
        "timestamp": datetime.now().isoformat(),
        "caller": caller
    }
    
    if error:
        log_entry["error"] = {
            "type": error.__class__.__name__,
            "message": str(error)
        }
    
    if data:
        log_entry["data"] = data
        
    logger.error(f"ERROR: {json.dumps(log_entry)}")

def log_warning(message: str, data: Optional[Dict[str, Any]] = None):
    """
    Registra uma mensagem de aviso.
    
    Args:
        message: Mensagem de aviso
        data: Dados adicionais para o log (opcional)
    """
    caller = _get_caller_info()
    log_entry = {
        "message": message,
        "level": "WARNING",
        "timestamp": datetime.now().isoformat(),
        "caller": caller
    }
    
    if data:
        log_entry["data"] = data
        
    logger.warning(f"WARNING: {json.dumps(log_entry)}")

def log_debug(message: str, data: Optional[Dict[str, Any]] = None):
    """
    Registra uma mensagem de debug.
    
    Args:
        message: Mensagem de debug
        data: Dados adicionais para o log (opcional)
    """
    caller = _get_caller_info()
    log_entry = {
        "message": message,
        "level": "DEBUG",
        "timestamp": datetime.now().isoformat(),
        "caller": caller
    }
    
    if data:
        log_entry["data"] = data
        
    logger.debug(f"DEBUG: {json.dumps(log_entry)}")

# Classe para medir tempo de execução
class Timer:
    """Utilitário para medir o tempo de execução de operações."""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.time()
        duration_ms = (end_time - self.start_time) * 1000
        log_info(
            f"Operação {self.operation_name} concluída", 
            {"duration_ms": duration_ms}
        )
