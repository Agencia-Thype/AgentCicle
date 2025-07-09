import os
import time
from dotenv import load_dotenv
import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Carregar variáveis de ambiente
load_dotenv()

# Imprimir informações de debug
print("=== Teste de Conexão com o Banco de Dados ===")
print(f"Python working directory: {os.getcwd()}")

# URL do banco de dados
DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql+psycopg2://ciclo_db_user:p4NWwjkTVPYEAKwnKhXBiq5NlPm9YYsl@dpg-cvhlcjv2p9s738n1qog-a.ohio-postgres.render.com/ciclo_db"

print(f"DATABASE_URL: {DATABASE_URL}")

# Tentar conexão direta com psycopg2 primeiro
print("\n=== Tentando conexão com psycopg2 ===")
try:
    # Extrair parâmetros da URL
    db_params = {}
    if "@" in DATABASE_URL:
        userpass, hostdbname = DATABASE_URL.split("@", 1)
        if "://" in userpass:
            _, userpass = userpass.split("://", 1)
        if ":" in userpass:
            user, password = userpass.split(":", 1)
            db_params["user"] = user
            db_params["password"] = password
        
        if "/" in hostdbname:
            host_port, dbname = hostdbname.split("/", 1)
            if ":" in host_port:
                host, port = host_port.split(":", 1)
                db_params["host"] = host
                db_params["port"] = port
            else:
                db_params["host"] = host_port
            
            if "?" in dbname:
                dbname, params = dbname.split("?", 1)
            db_params["dbname"] = dbname

    print(f"Parâmetros extraídos: {db_params}")
    
    # Adicionar opções SSL
    db_params["sslmode"] = "prefer"  # Testar com: require, prefer, disable
    
    # Configurações adicionais
    db_params["connect_timeout"] = "30"
    db_params["keepalives"] = "1"
    db_params["keepalives_idle"] = "30"
    db_params["keepalives_interval"] = "10"
    db_params["keepalives_count"] = "5"
    
    print("Tentando conectar com psycopg2...")
    conn = psycopg2.connect(**db_params)
    print("Conexão com psycopg2 bem-sucedida!")
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"Versão do PostgreSQL: {version}")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"Erro na conexão psycopg2: {e}")

# Agora tentar com SQLAlchemy
print("\n=== Tentando conexão com SQLAlchemy ===")

# Diferentes configurações para testar
configs = [
    # Configuração 1: SSL modo prefer
    {
        "url": DATABASE_URL.replace("sslmode=require", "sslmode=prefer") if "sslmode=require" in DATABASE_URL else f"{DATABASE_URL}?sslmode=prefer",
        "connect_args": {
            "connect_timeout": 30,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5
        },
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "name": "SSL Prefer com Keepalives"
    },
    # Configuração 2: SSL modo verify-full
    {
        "url": DATABASE_URL.replace("sslmode=require", "sslmode=verify-full") if "sslmode=require" in DATABASE_URL else f"{DATABASE_URL}?sslmode=verify-full",
        "connect_args": {
            "connect_timeout": 30
        },
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "name": "SSL Verify-Full"
    },
    # Configuração 3: SSL desativado (apenas para teste)
    {
        "url": DATABASE_URL.replace("sslmode=require", "sslmode=disable") if "sslmode=require" in DATABASE_URL else f"{DATABASE_URL}?sslmode=disable",
        "connect_args": {
            "connect_timeout": 30
        },
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "name": "SSL Desativado"
    },
    # Configuração 4: Retry de conexão
    {
        "url": DATABASE_URL,
        "connect_args": {
            "connect_timeout": 60
        },
        "pool_pre_ping": True,
        "pool_recycle": 1800,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "name": "Com Retry e Timeout Maior"
    }
]

# Função para testar uma conexão
def test_connection(config):
    print(f"\nTestando configuração: {config['name']}")
    print(f"URL: {config['url']}")
    
    try:
        # Criar engine
        engine_args = {k: v for k, v in config.items() if k not in ["url", "name"]}
        engine = create_engine(config["url"], **engine_args)
        
        # Criar sessão
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        # Testar conexão
        result = session.execute(text("SELECT 1")).fetchone()
        print(f"Conexão bem-sucedida! Resultado: {result}")
        
        # Testar consulta mais complexa
        print("Tentando consulta mais complexa...")
        try:
            result = session.execute(text("SELECT COUNT(*) FROM usuario")).fetchone()
            print(f"Consulta bem-sucedida! Total de usuários: {result}")
        except Exception as e:
            print(f"Erro na consulta: {e}")
        
        # Fechar sessão
        session.close()
        return True
    except Exception as e:
        print(f"Erro na conexão: {e}")
        return False

# Testar cada configuração
successful_configs = []
for config in configs:
    if test_connection(config):
        successful_configs.append(config["name"])
    print("-" * 50)

# Mostrar resultados
print("\n=== Resultados dos Testes ===")
if successful_configs:
    print(f"Configurações bem-sucedidas: {', '.join(successful_configs)}")
    print(f"Recomendação: Use a configuração '{successful_configs[0]}'")
else:
    print("Nenhuma configuração funcionou. Verificar possíveis problemas de rede ou credenciais.")

print("\nFim dos testes.")
