import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestAuthSync:
    """Testes para o endpoint /auth/sync (criação/confirmação do perfil após login via Firebase)"""

    def test_sync_cria_usuario_novo(self, client: TestClient, db: Session, monkeypatch):
        from app.main import app as fastapi_app
        from app.services.auth_service import verificar_token, obter_uid_firebase

        fastapi_app.dependency_overrides[verificar_token] = lambda: "nova@example.com"
        monkeypatch.setattr(
            "app.routes.auth.obter_uid_firebase", lambda email: "firebase-uid-nova"
        )

        response = client.post(
            "/auth/sync",
            json={"nome": "Usuária Nova"},
            headers={"Authorization": "Bearer test-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["novo"] is True

        from app.models.sqlalchemy_models import Usuario
        usuario = db.query(Usuario).filter(Usuario.email == "nova@example.com").first()
        assert usuario is not None
        assert usuario.firebase_uid == "firebase-uid-nova"
        assert usuario.verificado == 1

    def test_sync_e_idempotente(self, client: TestClient, usuario_teste, headers_auth: dict):
        response = client.post(
            "/auth/sync", json={"nome": usuario_teste.nome}, headers=headers_auth
        )

        assert response.status_code == 200
        data = response.json()
        assert data["novo"] is False

    def test_sync_sem_token(self, client: TestClient):
        response = client.post("/auth/sync", json={"nome": "Sem Token"})

        assert response.status_code == 401


class TestGetMe:
    """Testes para GET /me"""

    def test_get_me_sucesso(self, client: TestClient, headers_auth: dict):
        response = client.get("/me", headers=headers_auth)

        assert response.status_code == 200
        data = response.json()
        assert "nome" in data
        assert "email" in data
        assert data["email"] == "teste@example.com"

    def test_get_me_sem_token(self, client: TestClient):
        response = client.get("/me")

        assert response.status_code == 401

    def test_get_me_token_invalido(self, client: TestClient, monkeypatch):
        from firebase_admin import auth as firebase_auth

        monkeypatch.setattr("app.services.auth_service.get_firebase_app", lambda: None)

        def _raise_invalid(token):
            raise firebase_auth.InvalidIdTokenError("token invalido")

        monkeypatch.setattr(firebase_auth, "verify_id_token", _raise_invalid)

        headers = {"Authorization": "Bearer token_invalido"}
        response = client.get("/me", headers=headers)

        assert response.status_code == 401
