import time
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Obter a URL do banco de dados do ambiente
DATABASE_URL = os.getenv("DATABASE_URL")
print(f"Tentando conectar ao banco de dados com URL: {DATABASE_URL}")

# Tentar conexão
try:
    # Criar engine com timeout maior
    engine = create_engine(
        DATABASE_URL,
        connect_args={"connect_timeout": 60},
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=5,
        max_overflow=10
    )
    
    print("Engine criada, tentando conectar...")
    
    # Testar conexão executando uma consulta simples
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print(f"Conexão bem-sucedida! Resultado: {result.scalar()}")
    
    print("Teste de conexão concluído com sucesso!")
    
except Exception as e:
    print(f"Erro ao conectar ao banco de dados: {e}")
    print("Tipo de erro:", type(e))
    print("Detalhes completos:", repr(e))
