import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app as fastapi_app
from app.models.sqlalchemy_models import Usuario, HistoricoPeso, TreinoRealizado


class TestRotasVulneraveisRemovidas:
    """
    As rotas antigas de /listar-usuarios e /excluir-usuario/{id} não exigiam
    autenticação: expunham o e-mail de todas as usuárias e permitiam apagar
    qualquer conta. Devem ter deixado de existir.
    """

    def test_listar_usuarios_nao_existe_mais(self, client: TestClient):
        assert client.get("/listar-usuarios").status_code == 404

    def test_excluir_usuario_por_id_nao_existe_mais(self, client: TestClient, usuario_teste):
        response = client.delete(f"/excluir-usuario/{usuario_teste.id}")
        assert response.status_code == 404


class TestExclusaoDeConta:
    """DELETE /usuario/me - exigência da App Store 5.1.1(v) e do Google Play."""

    def test_exige_autenticacao(self, client: TestClient):
        assert client.delete("/usuario/me").status_code == 401

    def test_exclui_a_propria_conta(
        self, client: TestClient, db: Session, usuario_teste, headers_auth, monkeypatch
    ):
        monkeypatch.setattr("app.routes.usuario.excluir_usuario_firebase", lambda email: True)
        usuario_id = usuario_teste.id

        response = client.delete("/usuario/me", headers=headers_auth)

        assert response.status_code == 200
        assert db.query(Usuario).filter(Usuario.id == usuario_id).first() is None

    def test_remove_dados_dependentes(
        self, client: TestClient, db: Session, usuario_teste, headers_auth, monkeypatch
    ):
        """Sem isso a exclusão quebra: metade das tabelas filhas é NO ACTION no Postgres."""
        monkeypatch.setattr("app.routes.usuario.excluir_usuario_firebase", lambda email: True)
        usuario_id = usuario_teste.id

        db.add(HistoricoPeso(user_id=usuario_id, peso=60.0))
        db.add(TreinoRealizado(usuario_id=usuario_id))
        db.commit()

        response = client.delete("/usuario/me", headers=headers_auth)

        assert response.status_code == 200
        assert db.query(HistoricoPeso).filter(HistoricoPeso.user_id == usuario_id).count() == 0
        assert db.query(TreinoRealizado).filter(TreinoRealizado.usuario_id == usuario_id).count() == 0

    def test_falha_no_firebase_nao_impede_exclusao_local(
        self, client: TestClient, db: Session, usuario_teste, headers_auth, monkeypatch
    ):
        def explode(email):
            raise RuntimeError("Firebase indisponível")

        monkeypatch.setattr("app.routes.usuario.excluir_usuario_firebase", explode)
        usuario_id = usuario_teste.id

        response = client.delete("/usuario/me", headers=headers_auth)

        assert response.status_code == 200
        assert db.query(Usuario).filter(Usuario.id == usuario_id).first() is None


class TestRotasDeTesteBloqueadasEmProducao:
    """
    /teste/ativar-premium e /teste/cancelar-premium alteram assinatura por e-mail,
    sem token. Fora de desenvolvimento precisam responder 404.
    """

    @pytest.mark.parametrize(
        "metodo,rota,payload",
        [
            ("post", "/teste/ativar-premium", {"email": "alvo@example.com"}),
            ("post", "/teste/cancelar-premium", {"email": "alvo@example.com"}),
            ("get", "/teste/status-assinatura?email=alvo@example.com", None),
        ],
    )
    def test_bloqueadas_fora_de_desenvolvimento(
        self, client: TestClient, monkeypatch, metodo, rota, payload
    ):
        monkeypatch.setenv("ENVIRONMENT", "production")

        if metodo == "post":
            response = client.post(rota, json=payload)
        else:
            response = client.get(rota)

        assert response.status_code == 404

    def test_bloqueadas_quando_environment_nao_definida(self, client: TestClient, monkeypatch):
        monkeypatch.delenv("ENVIRONMENT", raising=False)

        response = client.post("/teste/ativar-premium", json={"email": "alvo@example.com"})

        assert response.status_code == 404

    def test_liberadas_em_desenvolvimento(
        self, client: TestClient, usuario_teste, monkeypatch
    ):
        monkeypatch.setenv("ENVIRONMENT", "development")

        response = client.post(
            "/teste/ativar-premium",
            json={"email": usuario_teste.email, "duracao_meses": 1},
        )

        assert response.status_code == 200
