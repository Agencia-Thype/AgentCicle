from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
from app.routes import auth, ciclo, diario, fase_atual, ia_routes, perfil, pontuacao, relatorio, usuario
from app.routes import treino, assinatura
from dotenv import load_dotenv
from app.utils.logging import log_request, Timer

# Carregar variáveis de ambiente
load_dotenv()

app = FastAPI(title="API Ciclo Menstrual")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, substitua por origens específicas
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

