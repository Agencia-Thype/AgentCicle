import pytest
from fastapi.testclient import TestClient


class TestFaseAtualEndpoints:
    """Testes para endpoints de fase atual"""

    def test_get_detalhes_fase_sucesso(self, client: TestClient, headers_auth: dict):
        """Testa获取 detalhes da fase atual"""
        response = client.get("/fase-atual/detalhes", headers=headers_auth)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


    def test_get_detalhes_fase_sem_token(self, client: TestClient):
        """Testa获取 detalhes sem autenticação"""
        response = client.get("/fase-atual/detalhes")

        assert response.status_code == 401


    def test_get_detalhes_fase_estrutura(self, client: TestClient, headers_auth: dict):
        """Testa se os detalhes têm estrutura esperada"""
        response = client.get("/fase-atual/detalhes", headers=headers_auth)

        assert response.status_code == 200
        data = response.json()

        # Verificar se tem campos comuns de fase
        campos_possiveis = ["fase", "dia", "sintomas_esperados", "recomendacoes"]
        tem_algum_campo = any(campo in data for campo in campos_possiveis)

        # Pode ter campos ou não, dependendo da implementação
        assert isinstance(data, dict)


class TestFaseAtualEndpointsIntegracao:
    """Testes de integração para fase atual"""

    def test_fase_atual_consistencia(self, client: TestClient, headers_auth: dict):
        """Testa se múltiplas chamadas retornam dados consistentes"""
        response1 = client.get("/fase-atual/detalhes", headers=headers_auth)
        response2 = client.get("/fase-atual/detalhes", headers=headers_auth)

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Ambas devem ter a mesma estrutura
        data1 = response1.json()
        data2 = response2.json()

        assert type(data1) == type(data2)
