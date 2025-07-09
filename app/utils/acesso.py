from functools import wraps
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.services.auth_service import verificar_token
from app.services.assinatura_service import verificar_status_usuario
from app.models.sqlalchemy_models import Usuario


def verificar_acesso(recurso_premium=False, permite_trial=True):
    """
    Decorator para verificar se o usuário tem acesso ao recurso.
    
    Args:
        recurso_premium: Se True, requer assinatura ativa (não basta trial)
        permite_trial: Se False, mesmo usuários em trial não terão acesso
        
    Returns:
        Decorator que verifica acesso
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Os argumentos podem vir tanto de args quanto de kwargs dependendo de como a função é chamada
            db = None
            email = None
            
            # Verificar se temos os argumentos nos kwargs
            if 'db' in kwargs:
                db = kwargs.get('db')
            if 'email' in kwargs:
                email = kwargs.get('email')
                
            # Se não encontramos nos kwargs, verificar nos args (verificando o tipo dos argumentos)
            if db is None and args:
                for arg in args:
                    if isinstance(arg, Session):
                        db = arg
                        break
                        
            # Buscar email nos argumentos posicionais
            if email is None and len(args) > 1:
                # O email geralmente é o segundo argumento após o db
                potential_email = args[1] if len(args) > 1 else None
                if isinstance(potential_email, str) and '@' in potential_email:
                    email = potential_email
            
            # Garantir que temos os valores necessários
            if not db or not email:
                print("⚠️ Faltando argumentos necessários no verificar_acesso. db:", db, "email:", email)
                # Vamos prosseguir mesmo sem verificação para não bloquear o fluxo
                return await func(*args, **kwargs)

            # Buscar usuário
            usuario = db.query(Usuario).filter(Usuario.email == email).first()
            if not usuario:
                # Por enquanto, não bloqueamos - apenas logamos
                print(f"⚠️ Usuário não encontrado: {email}")
                return await func(*args, **kwargs)

            # Verificar status do usuário
            status = verificar_status_usuario(db, usuario.id)
            
            # IMPORTANTE: Agora estamos bloqueando o acesso efetivamente
            if recurso_premium and not status["podeUsarPremium"]:
                print(f"⚠️ Usuário {email} tentou acessar recurso premium sem assinatura")
                raise HTTPException(status_code=403, detail="Acesso restrito. Assine o plano para continuar usando o app.")

            if not permite_trial and not status["assinaturaAtiva"]:
                print(f"⚠️ Usuário {email} tentou acessar recurso exclusivo para assinantes")
                raise HTTPException(status_code=403, detail="Acesso restrito a assinantes.")

            if not status["podeUsarRecursosBasicos"]:
                print(f"⚠️ Usuário {email} tentou acessar recurso básico com trial expirado")
                raise HTTPException(status_code=403, detail="Período de teste expirado. Assine o plano para continuar usando o app.")
                
            return await func(*args, **kwargs)
        return wrapper
    return decorator
