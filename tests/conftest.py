import pytest
import asyncio
import sys
import os
import tempfile
from typing import Generator, AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from unittest.mock import Mock, MagicMock

# Importar o app corretamente
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Mock do JSONB para SQLite - PRECISA ser antes de importar os modelos
class MockJSONB:
    """Mock para JSONB que funciona com SQLite"""
    pass

# Monkey patch do JSONB ANTES de importar os modelos
import app.models.conversaIA_models
app.models.conversaIA_models.JSONB = MockJSONB

from app.main import app as fastapi_app
from app.db.database import Base, get_db
# Importar TODOS os modelos para garantir que estão registrados no Base.metadata
from app.models import sqlalchemy_models, ciclo_models, diario_models, treino_models, conversaIA_models, IaHistoricoMensagem_models
from app.models.sqlalchemy_models import Usuario  # Import explicito para uso nos fixtures
from app.services.auth_service import verificar_token


# Database de teste (SQLite em arquivo para compartilhar entre conexões)
import tempfile
import os

# Criar um arquivo temporário para o banco de teste
test_db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
test_db_path = test_db_file.name
test_db_file.close()

TEST_DATABASE_URL = f"sqlite:///{test_db_path}"

engine_test = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    """Override da função get_db para usar banco de teste"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Cria um banco de dados novo para cada teste"""
    # Criar tabelas
    Base.metadata.create_all(bind=engine_test)
    print(f"✅ Tabelas criadas: {list(Base.metadata.tables.keys())}")
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Limpar tabelas
        Base.metadata.drop_all(bind=engine_test)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """Cria um cliente de teste"""
    def override_get_db_for_test():
        try:
            yield db
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db_for_test
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def async_client(db: Session) -> AsyncGenerator[AsyncClient, None]:
    """Cria um cliente async para testes"""
    def override_get_db_for_test():
        try:
            yield db
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db_for_test

    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app),
        base_url="http://test"
    ) as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def usuario_teste(db: Session) -> Usuario:
    """Cria um usuário de teste"""
    from datetime import date
    usuario = Usuario(
        nome="Usuária Teste",
        email="teste@example.com",
        firebase_uid="firebase-uid-teste",
        verificado=1,
        data_criacao=None,
        data_fim_trial=None,
        data_menstruacao=date(2024, 1, 1),  # Adicionado para testes de fase
        duracao_ciclo=28  # Adicionado para testes de fase
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@pytest.fixture
def headers_auth(usuario_teste: Usuario) -> dict:
    """Sobrescreve verificar_token para simular um usuário autenticado via Firebase"""
    fastapi_app.dependency_overrides[verificar_token] = lambda: usuario_teste.email
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def usuario_admin(db: Session) -> Usuario:
    """Cria um usuário admin para testes"""
    usuario = Usuario(
        nome="Admin Teste",
        email="admin@example.com",
        firebase_uid="firebase-uid-admin",
        verificado=1,
        data_criacao=None,
        data_fim_trial=None
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return usuario


@pytest.fixture
def headers_admin(usuario_admin: Usuario) -> dict:
    """Sobrescreve verificar_token para simular o admin autenticado via Firebase"""
    fastapi_app.dependency_overrides[verificar_token] = lambda: usuario_admin.email
    return {"Authorization": "Bearer test-token"}


# Dados de teste comuns
@pytest.fixture
def dados_ciclo() -> dict:
    """Dados válidos para registro de ciclo"""
    return {
        "data_inicio": "2024-01-01",
        "data_fim": "2024-01-05",
        "fluxo": "moderado",
        "sintomas": ["dor de cabeça", "cólica"],
        "observacoes": "Ciclo normal"
    }


@pytest.fixture
def dados_diario() -> dict:
    """Dados válidos para registro de diário"""
    return {
        "data": "2024-01-15",
        "sentimentos": ["feliz"],
        "observacao": "Dia produtivo"
    }


# Eventos de pytest
def pytest_configure(config):
    """Configuração do pytest"""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )

def pytest_sessionfinish(session, exitstatus):
    """Cleanup após todos os testes"""
    try:
        if os.path.exists(test_db_path):
            os.unlink(test_db_path)
    except:
        pass


@pytest.fixture(scope="session")
def event_loop():
    """Cria um event loop para testes async"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
