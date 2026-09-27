import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import declarative_base, sessionmaker


load_dotenv()

ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL nao configurada. Defina a variavel de ambiente antes de iniciar a aplicacao."
    )

url_info = make_url(DATABASE_URL)
drivername = url_info.drivername.lower()
is_sqlite = drivername.startswith("sqlite")
is_postgres = drivername.startswith("postgresql")

connect_args = {}
if not is_sqlite:
    # Fail fast: se o banco estiver lento/fora, nao deixe o app preso por 60s.
    connect_args["connect_timeout"] = int(os.getenv("DB_CONNECT_TIMEOUT_SECONDS", "5"))

if is_postgres:
    statement_timeout_ms = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "15000"))
    connect_args["options"] = f"-c statement_timeout={statement_timeout_ms}"

pool_args = {}
if not is_sqlite:
    pool_args = {
        "pool_pre_ping": True,
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE_SECONDS", "1800")),
        "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT_SECONDS", "5")),
    }

engine = create_engine(
    DATABASE_URL,
    echo=(ENVIRONMENT != "production"),
    connect_args=connect_args,
    **pool_args,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
