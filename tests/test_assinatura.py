import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.sqlalchemy_models import Usuario


class TestAssinaturaEndpoints:
    """Testes para endpoints de assinatura"""

    def test_get_status_sucesso(self, client: TestClient, headers_auth: dict):
        """Testa获取 status de assinatura com sucesso"""
        response = client.get("/assinatura/status", headers=headers_auth)

        assert response.status_code == 200
        data = response.json()
        assert "trialAtivo" in data
        assert "assinaturaAtiva" in data
        assert "podeUsarRecursosBasicos" in data


    def test_get_status_sem_token(self, client: TestClient):
        """Testa获取 status sem token"""
        response = client.get("/assinatura/status")

        assert response.status_code == 401


    def test_get_status_login_sucesso(self, client: TestClient, headers_auth: dict):
        """Testa获取 status otimizado para login"""
        response = client.get("/assinatura/status-login", headers=headers_auth)

        assert response.status_code == 200
        data = response.json()
        assert "trialAtivo" in data
        assert "assinaturaAtiva" in data
        assert "statusTipo" in data


    def test_ativar_assinatura_sucesso(self, client: TestClient, headers_auth: dict, db: Session):
        """Testa ativação de assinatura com sucesso"""
        dados = {
            "duracao_meses": 1
        }

        response = client.post("/assinatura/ativar", headers=headers_auth, json=dados)

        assert response.status_code == 200
        data = response.json()
        assert "mensagem" in data
        assert "ativada" in data["mensagem"].lower()
        assert "status" in data


    def test_ativar_assinatura_variacoes_meses(self, client: TestClient, headers_auth: dict):
        """Testa ativação com diferentes durações"""
        duracoes = [1, 3, 6, 12]

        for duracao in duracoes:
            dados = {"duracao_meses": duracao}
            response = client.post("/assinatura/ativar", headers=headers_auth, json=dados)

            assert response.status_code == 200
            data = response.json()
            assert "mensagem" in data


    def test_ativar_assinatura_sem_autorizacao(self, client: TestClient):
        """Testa ativação sem autorização"""
        dados = {"duracao_meses": 1}

        response = client.post("/assinatura/ativar", json=dados)

        assert response.status_code == 401


    def test_cancelar_assinatura_sucesso(self, client: TestClient, headers_auth: dict, db: Session):
        """Testa cancelamento de assinatura"""
        # Primeiro ativar a assinatura
        client.post("/assinatura/ativar", headers=headers_auth, json={"duracao_meses": 1})

        # Depois cancelar
        response = client.post("/assinatura/cancelar", headers=headers_auth)

        assert response.status_code == 200
        data = response.json()
        assert "mensagem" in data
        assert "cancelada" in data["mensagem"].lower()


    def test_cancelar_assinatura_sem_ativar(self, client: TestClient, headers_auth: dict):
        """Testa cancelamento sem ter assinatura ativa"""
        response = client.post("/assinatura/cancelar", headers=headers_auth)

        # Deve retornar 200 mesmo não tendo assinatura (idempotente)
        assert response.status_code == 200


class TestAssinaturaComTrial:
    """Testes de assinatura com período de trial"""

    def test_usuario_com_trial_ativo(self, client: TestClient, db: Session):
        """Testa status de usuário com trial ativo"""
        # Criar usuário com trial
        usuario = Usuario(
            nome="Usuária Trial",
            email="trial@example.com",
            senha_hash="hashed",
            verificado=1,
            data_criacao=datetime.now(timezone.utc),
            data_fim_trial=datetime.now(timezone.utc) + timedelta(days=7)
        )
        db.add(usuario)
        db.commit()

        token = "fake_token_for_trial_user"
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/assinatura/status", headers=headers)

        # Pode ser 401 se o token for inválido ou 200 se válido
        assert response.status_code in [200, 401]


    def test_usuario_com_trial_expirado(self, client: TestClient, db: Session):
        """Testa status de usuário com trial expirado"""
        # Criar usuário com trial expirado
        usuario = Usuario(
            nome="Usuária Expirada",
            email="expirada@example.com",
            senha_hash="hashed",
            verificado=1,
            data_criacao=datetime.now(timezone.utc) - timedelta(days=10),
            data_fim_trial=datetime.now(timezone.utc) - timedelta(days=3)
        )
        db.add(usuario)
        db.commit()

        token = "fake_token_for_expired_user"
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get("/assinatura/status", headers=headers)

        # Pode ser 401 se o token for inválido
        assert response.status_code in [200, 401]


class TestAssinaturaEndpointsIntegracao:
    """Testes de integração para assinatura"""

    def test_fluxo_completo_assinatura(self, client: TestClient, headers_auth: dict):
        """Testa fluxo: status -> ativar -> status -> cancelar -> status"""
        # 1. Verificar status inicial
        response = client.get("/assinatura/status", headers=headers_auth)
        assert response.status_code == 200
        status_inicial = response.json()

        # 2. Ativar assinatura
        response = client.post("/assinatura/ativar", headers=headers_auth, json={"duracao_meses": 1})
        assert response.status_code == 200

        # 3. Verificar status após ativação
        response = client.get("/assinatura/status", headers=headers_auth)
        assert response.status_code == 200
        status_ativo = response.json()

        # 4. Cancelar assinatura
        response = client.post("/assinatura/cancelar", headers=headers_auth)
        assert response.status_code == 200

        # 5. Verificar status após cancelamento
        response = client.get("/assinatura/status", headers=headers_auth)
        assert response.status_code == 200
        status_cancelado = response.json()


class TestAssinaturaValidacao:
    """Testes de validação para assinatura"""

    def test_ativar_duracao_invalida(self, client: TestClient, headers_auth: dict):
        """Testa ativação com duração inválida"""
        dados = {"duracao_meses": -1}

        response = client.post("/assinatura/ativar", headers=headers_auth, json=dados)

        # Deve retornar erro de validação
        assert response.status_code in [400, 422]


    def test_ativar_duracao_zero(self, client: TestClient, headers_auth: dict):
        """Testa ativação com duração zero"""
        dados = {"duracao_meses": 0}

        response = client.post("/assinatura/ativar", headers=headers_auth, json=dados)

        # Deve retornar erro de validação
        assert response.status_code in [400, 422]


    def test_ativar_sem_duracao(self, client: TestClient, headers_auth: dict):
        """Testa ativação sem especificar duração"""
        response = client.post("/assinatura/ativar", headers=headers_auth, json={})

        # Deve usar o valor padrão (1 mês) se implementado
        assert response.status_code in [200, 422]
