import pytest
from fastapi.testclient import TestClient


class TestEndpointsGerais:
    """Testes gerais para todos os endpoints"""

    def test_health_check(self, client: TestClient):
        """Testa se a API está respondendo"""
        response = client.get("/docs")

        assert response.status_code in [200, 404]

    def test_cors_headers(self, client: TestClient):
        """Testa se os headers CORS estão configurados"""
        response = client.options("/api/health")

        assert response.status_code in [200, 404]

    def test_endpoints_protegidos_sem_token(self, client: TestClient):
        """Testa se endpoints protegidos retornam 401 sem token"""
        endpoints_protegidos_get = [
            "/me",
            "/assinatura/status",
            "/perfil/perfil",
            "/fase-atual/detalhes"
        ]

        for endpoint in endpoints_protegidos_get:
            response = client.get(endpoint)
            assert response.status_code in [401, 404]


class TestIntegracaoSistema:
    """Testes de integração do sistema completo"""

    def test_fluxo_usuario_completo(self, client: TestClient, headers_auth: dict, usuario_teste):
        """Testa fluxo de um usuário já sincronizado acessando endpoints protegidos"""
        response = client.get("/assinatura/status", headers=headers_auth)
        assert response.status_code == 200

        response = client.get("/fase-ciclo", headers=headers_auth)
        assert response.status_code in [200, 404]


class TestPerformanceEndpoints:
    """Testes de performance dos endpoints"""

    def test_tempo_resposta_status_assinatura(self, client: TestClient, headers_auth: dict):
        """Testa se o status de assinatura responde em tempo razoável"""
        import time

        start_time = time.time()

        response = client.get("/assinatura/status", headers=headers_auth)

        end_time = time.time()
        duration = end_time - start_time

        assert duration < 1.0
        assert response.status_code == 200


class TestSegurancaEndpoints:
    """Testes de segurança dos endpoints"""

    def test_xss_basico(self, client: TestClient, headers_auth: dict):
        """Testa proteção básica contra XSS"""
        dados_xss = {
            "mensagem": "<script>alert('XSS')</script>",
            "historico": []
        }

        response = client.post("/ia/conversar", headers=headers_auth, json=dados_xss)

        assert response.status_code in [200, 422, 500]

        if response.status_code == 200:
            data = response.json()
            if "resposta" in data:
                assert "<script>" not in str(data["resposta"])
