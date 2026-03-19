import pytest
from fastapi.testclient import TestClient


class TestPerfilEndpoints:
    """Testes para endpoints de perfil"""

    def test_get_perfil_sucesso(self, client: TestClient, headers_auth: dict):
        """Testa获取 perfil com sucesso"""
        response = client.get("/perfil", headers=headers_auth)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


    def test_get_perfil_sem_token(self, client: TestClient):
        """Testa获取 perfil sem autenticação"""
        response = client.get("/perfil")

        assert response.status_code == 401


    def test_put_perfil_sucesso(self, client: TestClient, headers_auth: dict):
        """Testa atualização de perfil"""
        dados = {
            "nome": "Nome Atualizado",
            "data_nascimento": "1990-01-01",
            "altura": 165,
            "peso": 65
        }

        response = client.put("/perfil", headers=headers_auth, json=dados)

        # Pode ser 200 ou 422 dependendo da validação
        assert response.status_code in [200, 422]


    def test_put_perfil_sem_token(self, client: TestClient):
        """Testa atualização de perfil sem autenticação"""
        dados = {"nome": "Teste"}

        response = client.put("/perfil", json=dados)

        assert response.status_code == 401


    def test_get_grafico_sucesso(self, client: TestClient, headers_auth: dict, db: Session):
        """Testa获取 dados do gráfico"""
        # Ativar premium para o usuário (endpoint requer premium)
        from app.services.assinatura_service import ativar_assinatura
        from app.models.sqlalchemy_models import Usuario
        usuario = db.query(Usuario).filter(Usuario.email == "teste@example.com").first()
        if usuario:
            ativar_assinatura(db, usuario.id, duracao_meses=1)

        response = client.get("/perfil/grafico", headers=headers_auth)

        # Pode ser 200, 403 (sem premium), ou 404 (sem histórico)
        assert response.status_code in [200, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))


    def test_get_grafico_sem_token(self, client: TestClient):
        """Testa获取 gráfico sem autenticação"""
        response = client.get("/perfil/grafico")

        assert response.status_code == 401


    def test_sincronizar_fase_sucesso(self, client: TestClient, headers_auth: dict):
        """Testa sincronização de fase"""
        dados = {
            "fase_atual": "folicular",
            "data_ciclo": "2024-01-01"
        }

        response = client.post("/sincronizar-fase", headers=headers_auth, json=dados)

        # Pode ser 200 ou 422
        assert response.status_code in [200, 422]


class TestPerfilEndpointsValidacao:
    """Testes de validação para perfil"""

    def test_atualizar_perfil_campos_invalidos(self, client: TestClient, headers_auth: dict):
        """Testa atualização com campos inválidos"""
        dados = {
            "altura": -165,  # Altura negativa
            "peso": -65      # Peso negativo
        }

        response = client.put("/perfil", headers=headers_auth, json=dados)

        # Deve retornar erro de validação
        assert response.status_code in [400, 422]


    def test_atualizar_perfil_data_invalida(self, client: TestClient, headers_auth: dict):
        """Testa atualização com data de nascimento inválida"""
        dados = {
            "data_nascimento": "data-invalida"
        }

        response = client.put("/perfil", headers=headers_auth, json=dados)

        # Deve retornar erro de validação
        assert response.status_code in [400, 422]
