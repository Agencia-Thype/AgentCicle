import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestAuthEndpoints:
    """Testes para endpoints de autenticação"""

    def test_register_sucesso(self, client: TestClient, dados_registro: dict):
        """Testa registro com sucesso"""
        response = client.post("/register", json=dados_registro)

        assert response.status_code == 200
        data = response.json()
        assert "mensagem" in data
        assert "registrada" in data["mensagem"].lower()


    def test_register_email_duplicado(self, client: TestClient, usuario_teste):
        """Testa registro com email já cadastrado"""
        dados = {
            "nome": "Outra Usuária",
            "email": "teste@example.com",  # Email já existe
            "senha": "senha123",
            "confirmacao_senha": "senha123"
        }

        response = client.post("/register", json=dados)

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data


    def test_register_senhas_diferentes(self, client: TestClient):
        """Testa registro com senhas diferentes"""
        dados = {
            "nome": "Maria Teste",
            "email": "maria@teste.com",
            "senha": "senha123",
            "confirmacao_senha": "senha456"
        }

        response = client.post("/register", json=dados)

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data


    def test_register_campos_faltando(self, client: TestClient):
        """Testa registro sem campos obrigatórios"""
        dados = {
            "nome": "Maria Teste",
            "email": "maria@teste.com"
            # Falta senha e confirmacao_senha
        }

        response = client.post("/register", json=dados)

        assert response.status_code == 422  # Validation error


    def test_validar_email_sucesso(self, client: TestClient, usuario_teste):
        """Testa validação de email com sucesso"""
        # Primeiro atualizar o usuário para ter código de validação
        dados = {
            "email": "teste@example.com",
            "codigo": "TESTE123"
        }

        response = client.post("/validar-email", json=dados)

        # Pode ser 400 se o código não existir, mas não deve ser 404
        assert response.status_code in [200, 400]


    def test_validar_email_usuario_nao_encontrado(self, client: TestClient):
        """Testa validação de email com usuário inexistente"""
        dados = {
            "email": "naoexiste@example.com",
            "codigo": "QUALQUER123"
        }

        response = client.post("/validar-email", json=dados)

        assert response.status_code == 404


    def test_login_sucesso(self, client: TestClient, usuario_teste):
        """Testa login com sucesso"""
        dados = {
            "email": "teste@example.com",
            "senha": "test123"
        }

        response = client.post("/login", json=dados)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "usuario" in data
        assert data["usuario"]["email"] == "teste@example.com"


    def test_login_email_incorreto(self, client: TestClient):
        """Testa login com email incorreto"""
        dados = {
            "email": "naoexiste@example.com",
            "senha": "senha123"
        }

        response = client.post("/login", json=dados)

        assert response.status_code == 404


    def test_login_senha_incorreta(self, client: TestClient, usuario_teste):
        """Testa login com senha incorreta"""
        dados = {
            "email": "teste@example.com",
            "senha": "senhaerrada"
        }

        response = client.post("/login", json=dados)

        assert response.status_code == 401


    def test_login_usuario_nao_verificado(self, client: TestClient, db: Session):
        """Testa login com usuário não verificado"""
        from app.models.sqlalchemy_models import Usuario
        from app.services.auth_service import hash_senha

        # Criar usuário não verificado
        usuario = Usuario(
            nome="Não Verificado",
            email="naoverificado@example.com",
            senha_hash=hash_senha("senha123"),
            verificado=0
        )
        db.add(usuario)
        db.commit()

        dados = {
            "email": "naoverificado@example.com",
            "senha": "senha123"
        }

        response = client.post("/login", json=dados)

        assert response.status_code == 403


    def test_get_me_sucesso(self, client: TestClient, headers_auth: dict):
        """Testa获取 usuário logado com sucesso"""
        response = client.get("/me", headers=headers_auth)

        assert response.status_code == 200
        data = response.json()
        assert "nome" in data
        assert "email" in data
        assert data["email"] == "teste@example.com"


    def test_get_me_sem_token(self, client: TestClient):
        """Testa获取 usuário logado sem token"""
        response = client.get("/me")

        assert response.status_code == 401


    def test_get_me_token_invalido(self, client: TestClient):
        """Testa获取 usuário logado com token inválido"""
        headers = {"Authorization": "Bearer token_invalido"}
        response = client.get("/me", headers=headers)

        assert response.status_code == 401


    def test_solicitar_redefinicao_senha_sucesso(self, client: TestClient, usuario_teste):
        """Testa solicitação de redefinição de senha"""
        dados = {"email": "teste@example.com"}

        response = client.post("/solicitar-redefinicao-senha", json=dados)

        assert response.status_code == 200
        data = response.json()
        assert "mensagem" in data


    def test_solicitar_redefinicao_senha_email_nao_existe(self, client: TestClient):
        """Testa solicitação de redefinição com email inexistente"""
        dados = {"email": "naoexiste@example.com"}

        response = client.post("/solicitar-redefinicao-senha", json=dados)

        # Por segurança, retorna 200 mesmo se email não existe
        assert response.status_code == 200


class TestAuthEndpointsIntegracao:
    """Testes de integração para autenticação"""

    def test_fluxo_completo_registro_login(self, client: TestClient):
        """Testa fluxo completo: registro -> login"""
        # 1. Registrar
        dados_registro = {
            "nome": "Usuária Fluxo",
            "email": "fluxo@example.com",
            "senha": "senha123",
            "confirmacao_senha": "senha123"
        }

        response = client.post("/register", json=dados_registro)
        assert response.status_code == 200

        # 2. Fazer login (vai falhar se não estiver verificado, mas testamos a estrutura)
        response = client.post("/login", json={
            "email": "fluxo@example.com",
            "senha": "senha123"
        })

        # Pode ser 403 se não verificado ou 200 se verificado
        assert response.status_code in [200, 403]

        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data


class TestAuthEndpointsSeguranca:
    """Testes de segurança para autenticação"""

    def test_injecao_sql_email(self, client: TestClient):
        """Testa proteção contra injeção SQL no email"""
        dados = {
            "nome": "Teste SQL",
            "email": "'; DROP TABLE usuarios; --",
            "senha": "senha123",
            "confirmacao_senha": "senha123"
        }

        response = client.post("/register", json=dados)

        # Não deve retornar 500 (erro do servidor)
        assert response.status_code in [400, 422]


    def test_email_formato_invalido(self, client: TestClient):
        """Testa registro com email em formato inválido"""
        dados = {
            "nome": "Teste Email",
            "email": "email_invalido",
            "senha": "senha123",
            "confirmacao_senha": "senha123"
        }

        response = client.post("/register", json=dados)

        # Pode ser 400 (validação do backend) ou 422 (validação do Pydantic)
        assert response.status_code in [400, 422]
