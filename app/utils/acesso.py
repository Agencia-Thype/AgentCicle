from functools import wraps
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional, Callable, Any
import inspect

from app.config import cobranca_ativa
from app.db.database import get_db
from app.services.auth_service import verificar_token
from app.services.assinatura_service import verificar_status_usuario
from app.models.sqlalchemy_models import Usuario


def verificar_acesso(recurso_premium=False, permite_trial=True):
    """
    Decorator para verificar se o usuário tem acesso ao recurso.
    IMPORTANTE: Este decorator só deve ser usado em rotas que já recebem email do verificar_token.
    
    Args:
        recurso_premium: Se True, requer assinatura ativa ou trial ativo
        permite_trial: Se False, apenas assinantes têm acesso (trial não serve)
        
    Returns:
        Decorator que verifica acesso
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # App gratuito: nenhum recurso é bloqueado por assinatura.
            if not cobranca_ativa():
                if inspect.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)

            # O email sempre vem do verificar_token como parâmetro
            db = None
            email = None
            
            # Buscar db e email nos argumentos
            for key, value in kwargs.items():
                if isinstance(value, Session):
                    db = value
                elif isinstance(value, str) and '@' in value:
                    email = value
            
            # Se não encontrou nos kwargs, buscar nos args
            if not db or not email:
                for arg in args:
                    if isinstance(arg, Session) and not db:
                        db = arg
                    elif isinstance(arg, str) and '@' in arg and not email:
                        email = arg
            
            # Se ainda não temos os dados necessários, deixa passar (não bloquear o sistema)
            if not db or not email:
                print("⚠️ verificar_acesso: argumentos insuficientes, permitindo acesso")
                return await func(*args, **kwargs)

            # Buscar usuário
            usuario = db.query(Usuario).filter(Usuario.email == email).first()
            if not usuario:
                print(f"⚠️ Usuário não encontrado: {email}")
                raise HTTPException(status_code=404, detail="Usuário não encontrado")

            # Verificar status do usuário
            status = verificar_status_usuario(db, usuario.id)
            
            # Lógica de bloqueio baseada no status
            if recurso_premium:
                # Para recursos premium, precisa ter trial ativo OU assinatura ativa
                if not status["temAcesso"]:
                    if status["diasRestantesTrial"] == 0 and not status["assinaturaAtiva"]:
                        raise HTTPException(
                            status_code=403, 
                            detail="Período de teste expirado. Assine o plano premium para continuar usando este recurso."
                        )
                    else:
                        raise HTTPException(
                            status_code=403, 
                            detail="Acesso restrito. Este recurso requer assinatura premium ou trial ativo."
                        )
                
                # Se permite_trial=False, bloqueia até usuários em trial
                if not permite_trial and not status["assinaturaAtiva"]:
                    raise HTTPException(
                        status_code=403, 
                        detail="Este recurso é exclusivo para assinantes premium."
                    )
                
            print(f"✅ Usuário {email} autorizado para recurso (premium={recurso_premium}, trial_permitido={permite_trial})")
            
            # Verifica se a função é assíncrona ou síncrona e chama apropriadamente
            if inspect.iscoroutinefunction(func):
                # Se for assíncrona, usa await
                return await func(*args, **kwargs)
            else:
                # Se for síncrona, chama diretamente
                return func(*args, **kwargs)
        return wrapper
    return decorator
