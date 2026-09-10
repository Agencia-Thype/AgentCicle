from fastapi import APIRouter, Depends, HTTPException, Response, Request, Body
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
import time

from app.config import cobranca_ativa
from app.db.database import get_db
from app.services.auth_service import verificar_token
from app.models.sqlalchemy_models import Usuario
from app.services.assinatura_service import (
    verificar_status_usuario,
    ativar_assinatura,
    cancelar_assinatura,
    get_status_por_email,
    obter_status_login,
    obter_status_resumido
)
from app.services.pagamento_service import validar_compra
from app.utils.logging import log_info, log_warning, Timer
from app.utils.cache import get_from_cache, set_in_cache, invalidate_cache

router = APIRouter(prefix="/assinatura", tags=["Assinatura"])


def exigir_cobranca_ativa():
    """
    Esconde as rotas de compra enquanto o app é gratuito.

    Publicado sem paywall, o app não pode expor nenhum fluxo de compra: seria
    uma venda fora do StoreKit / Play Billing. Responde 404 para que a rota
    simplesmente não exista do ponto de vista do cliente.
    """
    if not cobranca_ativa():
        raise HTTPException(status_code=404, detail="Not Found")

@router.get("/status")
def get_status_assinatura(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    """
    Endpoint DEPRECADO - Use o status retornado no login ou /assinatura/status-login quando necessário.
    Implementa cache forte e limite de uso para incentivar a nova abordagem.
    """
    # Extrai o parâmetro _t da query para verificar se é polling do frontend
    query_params = request.query_params
    is_frontend_polling = "_t" in query_params
    
    # Registra detalhes sobre o cliente
    client_info = {
        "ip": request.client.host,
        "port": request.client.port,
        "user_agent": request.headers.get("user-agent", "unknown"),
        "query_params": dict(query_params),
        "is_frontend_polling": is_frontend_polling
    }
    log_info(f"DEPRECATED - Consulta de status para {email}", client_info)
    
    # Verifica a data da última chamada deste endpoint pelo usuário
    cache_key = f"last_status_call_{email}"
    last_call = get_from_cache(cache_key)
    now = time.time()
    
    # Define um tempo mínimo entre chamadas (30 segundos)
    min_interval = 30  # segundos
    
    if is_frontend_polling and last_call and (now - last_call < min_interval):
        # Se estiver chamando muito frequentemente, retorna uma resposta com instruções
        log_warning(f"Chamadas muito frequentes para /status de {email}, sugerindo nova abordagem")
        
        # Adiciona cabeçalhos de cache muito fortes
        response.headers["Cache-Control"] = f"private, max-age={min_interval}"
        response.headers["X-Rate-Limited"] = "true"
        
        return {
            "mensagem": "Por favor, use os dados do login ou a rota /assinatura/status-login",
            "devInfo": "Chamadas frequentes a esta rota são desencorajadas. Verifique o status apenas quando necessário.",
            "useLoginData": True,
            "nextAllowedCheck": int(now + min_interval)
        }
    
    # Atualiza a hora da última chamada
    set_in_cache(cache_key, now, 600)  # Guarda por 10 minutos
    
    # Define um cache forte para o cliente
    response.headers["Cache-Control"] = "private, max-age=300"  # 5 minutos de cache no cliente
    response.headers["ETag"] = f"W/\"{hash(email + str(int(now / 300)))}\"" 
    
    # Usa a função que já implementa cache do serviço
    with Timer("get_status_por_email"):
        status = get_status_por_email(db, email)
        
    if "erro" in status and status["erro"] == "Usuário não encontrado":
        log_warning(f"Usuário não encontrado: {email}")
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Busca informações do usuário para complementar o status
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    
    # Adiciona metadados para melhor controle no frontend
    status_completo = obter_status_resumido(db, usuario.id)
    
    # Adiciona informação se o usuário já teve assinatura anteriormente
    status_completo["jaTeveAssinatura"] = usuario.data_inicio_assinatura is not None
    
    # Adiciona informações sobre a conta
    status_completo["nome"] = usuario.nome
    status_completo["email"] = usuario.email
    
    # Adiciona mensagem incentivando uso do status do login
    status_completo["mensagemDev"] = "Use os dados de status retornados no login para melhor performance."
    
    return status_completo


@router.post("/ativar", dependencies=[Depends(exigir_cobranca_ativa)])
def ativar_plano(
    plataforma: str = Body(..., embed=True),
    token_compra: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    """
    Ativa a assinatura a partir de uma compra feita na loja.

    A versão anterior desta rota ativava premium só com a duração no corpo, sem
    nenhuma prova de pagamento: qualquer cliente autenticado se dava premium de
    graça. Agora a compra é obrigatoriamente validada junto à loja antes de
    qualquer escrita no banco.
    """
    if plataforma not in ("ios", "android"):
        raise HTTPException(status_code=400, detail="Plataforma inválida")

    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    # Falha fechado enquanto a integração com as lojas não existir.
    compra = validar_compra(plataforma, token_compra)

    resultado = ativar_assinatura(db, usuario.id, compra.duracao_meses)
    log_info(
        "Assinatura ativada por compra validada",
        {"usuario_id": usuario.id, "plataforma": compra.plataforma, "transacao": compra.id_transacao},
    )

    return {
        "mensagem": "Assinatura ativada com sucesso!",
        "status": resultado
    }


@router.post("/cancelar", dependencies=[Depends(exigir_cobranca_ativa)])
def cancelar_plano(
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    """
    Endpoint para cancelar a assinatura.
    """
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    resultado = cancelar_assinatura(db, usuario.id)
    
    return {
        "mensagem": "Assinatura cancelada com sucesso.",
        "status": resultado
    }


@router.get("/status-login")
def get_status_login(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    """
    Endpoint otimizado para uso durante login.
    Retorna o status completo com metadados para cache no frontend.
    """
    log_info(f"Verificação de status no login para: {email}")
    
    # Busca o usuário
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Obtém o status completo otimizado para login
    with Timer("obter_status_login"):
        status = obter_status_login(db, usuario.id)
    
    # Configura cabeçalhos para cache de longo prazo
    # O frontend decidirá quando buscar novamente com base nos metadados
    max_age = status.get("tempoValidoSegundos", 86400)  # 1 dia padrão
    response.headers["Cache-Control"] = f"private, max-age={max_age}"
    
    return status
