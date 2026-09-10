from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL não configurada. Defina a variável de ambiente antes de iniciar a aplicação."
    )

connect_args = {
    "connect_timeout": 60,  # Aumentar o timeout de conexão para 60 segundos
}

engine = create_engine(
    DATABASE_URL,
    echo=(ENVIRONMENT != "production"),  # nunca logar SQL em produção
    pool_pre_ping=True,  # Verificar conexão antes de usar
    pool_recycle=1800,   # Reciclar conexões a cada 30 minutos
    pool_size=5,         # Limitar o número de conexões no pool
    max_overflow=10,     # Máximo de conexões extras além do pool_size
    connect_args=connect_args
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
