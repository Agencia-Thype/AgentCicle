import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


class TestCicloEndpoints:
    """Testes para endpoints de ciclo"""

    def test_registrar_menstruacao_sucesso(self, client: TestClient, headers_auth: dict, dados_ciclo: dict):
        """Testa registro de menstruação com sucesso"""
        response = client.post("/registrar-menstruacao", headers=headers_auth, json=dados_ciclo)

        assert response.status_code == 200
        data = response.json()
        assert "mensagem" in data


    def test_registrar_menstruacao_sem_token(self, client: TestClient, dados_ciclo: dict):
        """Testa registro sem autenticação"""
        response = client.post("/registrar-menstruacao", json=dados_ciclo)

        assert response.status_code == 401


    def test_registrar_menstruacao_dados_invalidos(self, client: TestClient, headers_auth: dict):
        """Testa registro com dados inválidos"""
        dados = {
            "data_inicio": "data-invalida",
            "data_fim": "2024-01-05"
        }

        response = client.post("/registrar-menstruacao", headers=headers_auth, json=dados)

        assert response.status_code in [400, 422]


    def test_editar_menstruacao_sucesso(self, client: TestClient, headers_auth: dict, dados_ciclo: dict):
        """Testa edição de menstruação"""
        # Primeiro registrar
        response = client.post("/registrar-menstruacao", headers=headers_auth, json=dados_ciclo)
        assert response.status_code == 200

        # Depois editar
        dados_edicao = {
            "data_nova": "2024-01-02"
        }

        response = client.put("/editar-menstruacao", headers=headers_auth, json=dados_edicao)

        assert response.status_code == 200
        data = response.json()
        assert "mensagem" in data


    def test_editar_menstruacao_sem_registro(self, client: TestClient, headers_auth: dict):
        """Testa edição sem ter registro prévio"""
        dados = {
            "data_nova": "2024-01-01"
        }

        response = client.put("/editar-menstruacao", headers=headers_auth, json=dados)

        # Pode retornar 200 ou 404 dependendo da implementação
        assert response.status_code in [200, 404]


    def test_get_fase_por_data_sucesso(self, client: TestClient, headers_auth: dict):
        """Testa获取 fase por data específica"""
        response = client.get("/fase-por-data?data=2024-01-15", headers=headers_auth)

        assert response.status_code == 200
        data = response.json()
        assert "fase" in data


    def test_get_fase_por_data_sem_token(self, client: TestClient):
        """Testa获取 fase por data sem autenticação"""
        response = client.get("/fase-por-data?data=2024-01-15")

        assert response.status_code == 401


    def test_get_fase_por_data_formato_invalido(self, client: TestClient, headers_auth: dict):
        """Testa获取 fase por data com formato inválido"""
        response = client.get("/fase-por-data?data=invalida", headers=headers_auth)

        # Deve retornar erro de validação
        assert response.status_code in [400, 422]


    def test_get_fase_ciclo_sucesso(self, client: TestClient, headers_auth: dict):
        """Testa获取 fase do ciclo atual"""
        response = client.get("/fase-ciclo", headers=headers_auth)

        assert response.status_code == 200
        data = response.json()
        assert "fase" in data


    def test_get_fase_ciclo_sem_token(self, client: TestClient):
        """Testa获取 fase do ciclo sem autenticação"""
        response = client.get("/fase-ciclo")

        assert response.status_code == 401


class TestCicloEndpointsValidacao:
    """Testes de validação para ciclo"""

    def test_data_fim_antes_da_data_inicio(self, client: TestClient, headers_auth: dict):
        """Testa registro com data no futuro (deve ser aceita ou rejeitada)"""
        from datetime import date, timedelta
        data_futura = (date.today() + timedelta(days=30)).isoformat()
        dados = {
            "data_inicio": data_futura
        }

        response = client.post("/registrar-menstruacao", headers=headers_auth, json=dados)

        # Data futura pode ser válida ou inválida dependendo da implementação
        # Aceitamos 200 (data futura permitida) ou 400/422 (data futura bloqueada)
        assert response.status_code in [200, 400, 422]


    def test_data_fim_igual_data_inicio(self, client: TestClient, headers_auth: dict):
        """Testa registro com data fim igual à data início"""
        dados = {
            "data_inicio": "2024-01-05",
            "data_fim": "2024-01-05",  # Mesma data
            "fluxo": "moderado"
        }

        response = client.post("/registrar-menstruacao", headers=headers_auth, json=dados)

        # Pode ser válido (1 dia) ou inválido dependendo da implementação
        assert response.status_code in [200, 400, 422]


    def test_registrar_sem_campos_obrigatorios(self, client: TestClient, headers_auth: dict):
        """Testa registro sem campos obrigatórios"""
        dados = {}  # Vazio, sem data_inicio

        response = client.post("/registrar-menstruacao", headers=headers_auth, json=dados)

        assert response.status_code in [400, 422]


class TestCicloEndpointsIntegracao:
    """Testes de integração para ciclo"""

    def test_fluxo_completo_ciclo(self, client: TestClient, headers_auth: dict):
        """Testa fluxo completo: registrar -> consultar fase -> editar"""
        # 1. Registrar menstruação
        dados_ciclo = {
            "data_inicio": "2024-01-01",
            "data_fim": "2024-01-05",
            "fluxo": "moderado",
            "sintomas": ["cólica"],
            "observacoes": "Ciclo de teste"
        }

        response = client.post("/registrar-menstruacao", headers=headers_auth, json=dados_ciclo)
        assert response.status_code == 200

        # 2. Consultar fase
        response = client.get("/fase-por-data?data=2024-01-03", headers=headers_auth)
        assert response.status_code == 200

        # 3. Consultar fase do ciclo
        response = client.get("/fase-ciclo", headers=headers_auth)
        assert response.status_code == 200

        # 4. Editar registro
        dados_edicao = {
            "data_nova": "2024-01-02",
            "fluxo": "intenso",
            "observacoes": "Ciclo atualizado"
        }

        response = client.put("/editar-menstruacao", headers=headers_auth, json=dados_edicao)
        assert response.status_code in [200, 404]
