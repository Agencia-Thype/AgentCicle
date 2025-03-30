from fastapi import FastAPI
from app.routes import auth, ciclo, perfil
from app.routes import treino

app = FastAPI(title="API Ciclo Menstrual")

# Incluir rotas
app.include_router(ciclo.router)
app.include_router(treino.router)
app.include_router(auth.router)
app.include_router(perfil.router)
# app.include_router(usuario.router)
