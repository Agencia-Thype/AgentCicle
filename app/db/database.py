from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Obter a URL do banco de dados do ambiente - usando a URL interna do Render
DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql+psycopg2://ciclo_db_user:p4NwWjkTVPYEAKwnKhXBiq5NIPm9YYsl@dpg-cvhvlcjv2p9s738n1qog-a.ohio-postgres.render.com/ciclo_db"

# Simplificando para usar a conexão direta interna do Render
connect_args = {
    "connect_timeout": 60,  # Aumentar o timeout de conexão para 60 segundos
}

try:
    engine = create_engine(
        DATABASE_URL, 
        echo=True,  # echo=True para mostrar queries no terminal
        pool_pre_ping=True,  # Verificar conexão antes de usar
        pool_recycle=1800,   # Reciclar conexões a cada 30 minutos
        pool_size=5,         # Limitar o número de conexões no pool
        max_overflow=10,     # Máximo de conexões extras além do pool_size
        connect_args=connect_args
    )
    print("✅ Conexão com o banco criada com sucesso.")
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
except Exception as e:
    print("❌ Erro ao conectar com o banco:", e)
    # Criar um engine SQLite como fallback para evitar erros de importação
    fallback_url = "sqlite:///./test.db"
    engine = create_engine(fallback_url)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    print("⚠️ Usando SQLite como fallback")

Base = declarative_base()

def get_db():
    if SessionLocal is None:
        raise Exception("Banco de dados não inicializado")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
