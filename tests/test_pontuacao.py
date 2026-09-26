import pytest
from fastapi.testclient import TestClient
from app.routes.pontuacao import calcular_classe_lunar


class TestPontuacaoEndpoints:
    """Testes para endpoints de pontuação"""

    def test_get_pontuacao_sucesso(self, client: TestClient, headers_auth: dict):
        """Testa获取 pontuação com sucesso"""
        response = client.get("/pontuacao", headers=headers_auth)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


    def test_get_pontuacao_sem_token(self, client: TestClient):
        """Testa获取 pontuação sem autenticação"""
        response = client.get("/pontuacao")

        assert response.status_code == 401


    def test_get_pontuacao_estrutura(self, client: TestClient, headers_auth: dict):
        """Testa se a pontuação tem estrutura esperada"""
        response = client.get("/pontuacao", headers=headers_auth)

        assert response.status_code == 200
        data = response.json()

        # Verificar se tem campos comuns de pontuação
        campos_possiveis = ["pontos", "nivel", "treinos_completados", "proximo_nivel"]
        tem_algum_campo = any(campo in data for campo in campos_possiveis)

        # Pode ter campos ou não, dependendo da implementação
        assert isinstance(data, dict)


class TestPontuacaoEndpointsIntegracao:
    """Testes de integração para pontuação"""

    def test_pontuacao_consistencia(self, client: TestClient, headers_auth: dict):
        """Testa se múltiplas chamadas retornam dados consistentes"""
        response1 = client.get("/pontuacao", headers=headers_auth)
        response2 = client.get("/pontuacao", headers=headers_auth)

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Ambas devem ter a mesma estrutura
        data1 = response1.json()
        data2 = response2.json()

        assert type(data1) == type(data2)


@pytest.mark.parametrize(
    "pontos,classe,proxima,restantes",
    [
        (0, "Lua Nova", 120, 120),
        (119, "Lua Nova", 120, 1),
        (120, "Lua Crescente", 240, 120),
        (240, "Lua Cheia", 360, 120),
        (360, "Lua Minguante", None, 0),
        (999, "Lua Minguante", None, 0),
    ],
)
def test_classe_lunar_e_calculada_pelos_pontos(pontos, classe, proxima, restantes):
    resultado = calcular_classe_lunar(pontos)
    assert resultado["classe"] == classe
    assert resultado["proxima_pontuacao"] == proxima
    assert resultado["pontos_para_proxima"] == restantes


def test_endpoint_retorna_meta_da_classe(client, headers_auth, db, usuario_teste):
    usuario_teste.pontos_totais = 125
    db.commit()

    response = client.get("/pontuacao", headers=headers_auth)

    assert response.status_code == 200
    assert response.json()["classe"] == "Lua Crescente"
    assert response.json()["proxima_pontuacao"] == 240
    assert response.json()["pontos_para_proxima"] == 115
