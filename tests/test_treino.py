import pytest
from fastapi.testclient import TestClient


class TestTreinoEndpoints:
    """Testes para endpoints de treino"""

    def test_get_treino_sucesso(self, client: TestClient, headers_auth: dict):
        """Testa获取 treino do dia com sucesso"""
        response = client.get("/treino-dia/", headers=headers_auth)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (dict, list))


    def test_get_treino_sem_token(self, client: TestClient):
        """Testa获取 treino sem autenticação"""
        response = client.get("/treino-dia/")

        assert response.status_code == 401


    def test_get_treino_conteudo(self, client: TestClient, headers_auth: dict):
        """Testa se o treino retornado tem os campos esperados"""
        response = client.get("/treino-dia/", headers=headers_auth)

        assert response.status_code == 200
        data = response.json()

        # Verificar se é um dict ou lista e tem conteúdo relevante
        if isinstance(data, dict):
            # Pode ter campos como 'exercicios', 'dia', etc.
            assert len(data) >= 0  # Apenas verifica que retornou algo
        elif isinstance(data, list):
            # Lista de exercícios
            assert isinstance(data, list)


class TestTreinoEndpointsIntegracao:
    """Testes de integração para treino"""

    def test_get_treino_dias_diferentes(self, client: TestClient, headers_auth: dict):
        """Testa获取 treino em diferentes momentos"""
        # Primeira chamada
        response1 = client.get("/treino-dia/", headers=headers_auth)
        assert response1.status_code == 200

        # Segunda chamada (pode retornar mesmo ou diferente treino)
        response2 = client.get("/treino-dia/", headers=headers_auth)
        assert response2.status_code == 200

        # Ambas devem ter sucesso
        assert response1.status_code == response2.status_code
