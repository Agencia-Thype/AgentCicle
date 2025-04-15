from fastapi import FastAPI
from app.routes import auth, ciclo, diario, fase_atual, perfil, pontuacao, usuario
from app.routes import treino

app = FastAPI(title="API Ciclo Menstrual")

# Incluir rotas
app.include_router(ciclo.router)
app.include_router(treino.router)
app.include_router(auth.router)
app.include_router(perfil.router)
app.include_router(usuario.router)
app.include_router(diario.router)
app.include_router(pontuacao.router)
app.include_router(fase_atual.router)

