from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql+psycopg2://ciclo_db_user:p4NwWjkTVPYEAKwnKhXBiq5NIPm9YYsl@dpg-cvhvlcjv2p9s738n1qog-a.ohio-postgres.render.com/ciclo_db?sslmode=require"

try:
    engine = create_engine(DATABASE_URL, echo=True)  # echo=True para mostrar queries no terminal
    print("✅ Conexão com o banco criada com sucesso.")
except Exception as e:
    print("❌ Erro ao conectar com o banco:", e)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
