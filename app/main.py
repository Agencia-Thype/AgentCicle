import os
import sys

# Os prints de debug usam emoji. No Windows, quando a saída não é um console
# UTF-8, o Python usa cp1252 e o print lança UnicodeEncodeError - a rota que
# printou responde 500. Forçar UTF-8 (e trocar o que não der) evita isso.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
from app.routes import auth, ciclo, diario, fase_atual, ia_routes, perfil, pontuacao, relatorio, usuario
from app.routes import treino, assinatura, kegel
from dotenv import load_dotenv
from app.utils.logging import log_request, Timer

# Carregar variáveis de ambiente
load_dotenv()

app = FastAPI(title="API Ciclo Menstrual")

# Configurar CORS
# Em produção, defina CORS_ORIGINS com uma lista separada por vírgulas
# (ex: "https://app.agentcicle.com"). CORS só afeta navegadores - o app nativo
# não é impactado por uma lista vazia.
_cors_origins_env = os.getenv("CORS_ORIGINS")
_is_dev = os.getenv("ENVIRONMENT", "production").lower() == "development"

if _cors_origins_env:
    allow_origins = [origin.strip() for origin in _cors_origins_env.split(",") if origin.strip()]
elif _is_dev:
    # Origens do Expo Web / Metro durante o desenvolvimento local.
    allow_origins = [
        "http://localhost:8081",
        "http://localhost:19006",
        "http://127.0.0.1:8081",
        "http://127.0.0.1:19006",
    ]
else:
    # Sem CORS_ORIGINS em produção, nenhum navegador é liberado (fail-safe).
    allow_origins = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware para logging de requisições
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next):
    # Registra o início da requisição
    route = request.url.path
    start_time = time.time()
    
    # Processa a requisição
    response = await call_next(request)
    
    # Calcula a duração
    duration_ms = (time.time() - start_time) * 1000
    
    # Registra detalhes da requisição
    log_request(
        request=request, 
        route=route, 
        status_code=response.status_code,
        duration_ms=duration_ms
    )
    
    return response

# Incluir rotas
app.include_router(ciclo.router)
app.include_router(treino.router)
app.include_router(auth.router)
app.include_router(perfil.router)
app.include_router(usuario.router)
app.include_router(diario.router)
app.include_router(pontuacao.router)
app.include_router(fase_atual.router)
app.include_router(relatorio.router)
app.include_router(ia_routes.router)
app.include_router(assinatura.router)
app.include_router(kegel.router)


@app.get("/health", tags=["Infra"])
def health_check():
    """Verifica se a API está no ar e se o banco responde."""
    from sqlalchemy import text
    from app.db.database import engine

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    return {"status": "ok" if db_ok else "degraded", "database": db_ok}
