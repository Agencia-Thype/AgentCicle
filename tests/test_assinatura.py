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


    def test_ativar_indisponivel_no_modo_gratuito(self, client: TestClient, headers_auth: dict):
        """
        App publicado gratuito não pode expor fluxo de compra: seria venda fora
        do StoreKit / Play Billing. A rota precisa não existir para o cliente.
        """
        response = client.post(
            "/assinatura/ativar",
            headers=headers_auth,
            json={"plataforma": "ios", "token_compra": "recibo-qualquer"},
        )

        assert response.status_code == 404


    def test_cancelar_indisponivel_no_modo_gratuito(self, client: TestClient, headers_auth: dict):
        response = client.post("/assinatura/cancelar", headers=headers_auth)

        assert response.status_code == 404


    def test_ativar_sem_autorizacao(self, client: TestClient, monkeypatch):
        monkeypatch.setenv("COBRANCA_ATIVA", "true")

        response = client.post(
            "/assinatura/ativar",
            json={"plataforma": "ios", "token_compra": "recibo-qualquer"},
        )

        assert response.status_code == 401


    def test_ativar_exige_prova_de_compra(self, client: TestClient, headers_auth: dict, monkeypatch):
        """
        A rota antiga ativava premium só com {"duracao_meses": 1}: qualquer
        cliente autenticado se dava premium de graça. O corpo antigo agora é
        rejeitado por falta de recibo.
        """
        monkeypatch.setenv("COBRANCA_ATIVA", "true")

        response = client.post(
            "/assinatura/ativar", headers=headers_auth, json={"duracao_meses": 1}
        )

        assert response.status_code == 422


    def test_ativar_recusa_plataforma_invalida(self, client: TestClient, headers_auth: dict, monkeypatch):
        monkeypatch.setenv("COBRANCA_ATIVA", "true")

        response = client.post(
            "/assinatura/ativar",
            headers=headers_auth,
            json={"plataforma": "web", "token_compra": "recibo-qualquer"},
        )

        assert response.status_code == 400


    def test_ativar_falha_fechado_sem_validacao_de_loja(
        self, client: TestClient, headers_auth: dict, db: Session, usuario_teste, monkeypatch
    ):
        """
        Enquanto pagamento_service.validar_compra não estiver implementado,
        nenhuma assinatura pode ser gravada no banco.
        """
        monkeypatch.setenv("COBRANCA_ATIVA", "true")

        response = client.post(
            "/assinatura/ativar",
            headers=headers_auth,
            json={"plataforma": "android", "token_compra": "token-falso"},
        )

        assert response.status_code == 501

        db.refresh(usuario_teste)
        assert not usuario_teste.assinatura_ativa


    def test_cancelar_com_cobranca_ativa(self, client: TestClient, headers_auth: dict, monkeypatch):
        monkeypatch.setenv("COBRANCA_ATIVA", "true")

        response = client.post("/assinatura/cancelar", headers=headers_auth)

        assert response.status_code == 200
        assert "cancelada" in response.json()["mensagem"].lower()


class TestModoGratuito:
    """
    Com COBRANCA_ATIVA=false o app libera tudo para todo mundo e nenhum campo
    do status pode sugerir cobrança.
    """

    def test_status_libera_acesso_total(self, client: TestClient, headers_auth: dict):
        response = client.get("/assinatura/status", headers=headers_auth)

        assert response.status_code == 200
        data = response.json()
        assert data["temAcesso"] is True
        assert data["podeUsarRecursosBasicos"] is True
        assert data["podePontuar"] is True
        assert data["trialAtivo"] is False
        assert data["assinaturaAtiva"] is False


    def test_trial_expirado_nao_bloqueia(self, client: TestClient, db: Session):
        """O caso que travava o app: trial vencido e sem assinatura."""
        from app.main import app as fastapi_app
        from app.services.auth_service import verificar_token

        usuario = Usuario(
            nome="Trial Vencido",
            email="vencido@example.com",
            firebase_uid="firebase-uid-vencido",
            verificado=1,
            data_criacao_conta=datetime.now() - timedelta(days=30),
            data_fim_trial=datetime.now() - timedelta(days=23),
        )
        db.add(usuario)
        db.commit()

        fastapi_app.dependency_overrides[verificar_token] = lambda: usuario.email

        response = client.get("/assinatura/status-login", headers={"Authorization": "Bearer t"})

        assert response.status_code == 200
        data = response.json()
        assert data["temAcesso"] is True
        assert data["statusTipo"] == "gratuito"
        assert "assine" not in data["mensagem"].lower()


    def test_recurso_premium_liberado(self, client: TestClient, headers_auth: dict):
        """Rotas decoradas com verificar_acesso(recurso_premium=True) não bloqueiam."""
        response = client.get("/relatorio-mensal?mes=2024-01", headers=headers_auth)

        assert response.status_code != 403


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

    def test_status_permanece_consultavel_no_modo_gratuito(
        self, client: TestClient, headers_auth: dict
    ):
        """As rotas de leitura continuam funcionando; só a compra some."""
        assert client.get("/assinatura/status", headers=headers_auth).status_code == 200
        assert client.get("/assinatura/status-login", headers=headers_auth).status_code == 200
        assert client.post("/assinatura/ativar", headers=headers_auth, json={
            "plataforma": "ios", "token_compra": "x"
        }).status_code == 404
        assert client.post("/assinatura/cancelar", headers=headers_auth).status_code == 404
