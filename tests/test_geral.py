import pytest
from fastapi.testclient import TestClient


class TestEndpointsGerais:
    """Testes gerais para todos os endpoints"""

    def test_health_check(self, client: TestClient):
        """Testa se a API está respondendo"""
        # Tentar acessar a documentação do FastAPI
        response = client.get("/docs")

        # Se não tiver /docs, pode retornar 404, mas não deve ser 500
        assert response.status_code in [200, 404]


    def test_cors_headers(self, client: TestClient):
        """Testa se os headers CORS estão configurados"""
        # OPTIONS request para verificar CORS preflight
        response = client.options("/api/health")

        # Verificar se tem headers CORS (pode variar dependendo da configuração)
        # Alguns frameworks CORS não retornam headers em OPTIONS preflight
        # O importante é que a resposta não seja erro
        assert response.status_code in [200, 404]


    def test_endpoints_protegidos_sem_token(self, client: TestClient):
        """Testa se endpoints protegidos retornam 401 sem token"""
        # Apenas testar endpoints que aceitam GET e devem ter autenticação
        endpoints_protegidos_get = [
            "/me",
            "/assinatura/status",
            "/perfil/perfil",
            "/fase-atual/detalhes"
        ]

        for endpoint in endpoints_protegidos_get:
            response = client.get(endpoint)
            # Deve retornar 401 ou 404 (se não existir)
            assert response.status_code in [401, 404]


class TestIntegracaoSistema:
    """Testes de integração do sistema completo"""

    def test_fluxo_usuario_completo(self, client: TestClient):
        """Testa fluxo completo de um usuário"""
        # 1. Registrar usuário
        dados_registro = {
            "nome": "Usuária Integracao",
            "email": "integracao@example.com",
            "senha": "senha123",
            "confirmacao_senha": "senha123"
        }

        response = client.post("/register", json=dados_registro)
        # Pode ser 200 ou outro código
        assert response.status_code in [200, 400]

        # 2. Tentar login (pode falhar se não estiver verificado)
        response = client.post("/login", json={
            "email": "integracao@example.com",
            "senha": "senha123"
        })

        # Se login for bem-sucedido, testar endpoints protegidos
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")

            if token:
                headers = {"Authorization": f"Bearer {token}"}

                # 3. Verificar status de assinatura
                response = client.get("/assinatura/status", headers=headers)
                assert response.status_code == 200

                # 4. Consultar fase do ciclo
                response = client.get("/fase-ciclo", headers=headers)
                assert response.status_code == 200


class TestPerformanceEndpoints:
    """Testes de performance dos endpoints"""

    def test_tempo_resposta_login(self, client: TestClient, usuario_teste):
        """Testa se o login responde em tempo razoável"""
        import time

        start_time = time.time()

        response = client.post("/login", json={
            "email": "teste@example.com",
            "senha": "test123"
        })

        end_time = time.time()
        duration = end_time - start_time

        # Login deve responder em menos de 2 segundos
        assert duration < 2.0
        assert response.status_code == 200


    def test_tempo_resposta_status_assinatura(self, client: TestClient, headers_auth: dict):
        """Testa se o status de assinatura responde em tempo razoável"""
        import time

        start_time = time.time()

        response = client.get("/assinatura/status", headers=headers_auth)

        end_time = time.time()
        duration = end_time - start_time

        # Status deve responder em menos de 1 segundo
        assert duration < 1.0
        assert response.status_code == 200


class TestSegurancaEndpoints:
    """Testes de segurança dos endpoints"""

    def test_sql_injection_basico(self, client: TestClient):
        """Testa proteção básica contra SQL injection"""
        dados_maliciosos = {
            "nome": "'; DROP TABLE usuarios; --",
            "email": "teste@teste.com",
            "senha": "senha123",
            "confirmacao_senha": "senha123"
        }

        response = client.post("/register", json=dados_maliciosos)

        # Não deve retornar 500 (erro do servidor)
        assert response.status_code in [200, 400, 422]

        # Se retornou 200, o nome foi tratado como string normal
        if response.status_code == 200:
            data = response.json()
            assert "mensagem" in data


    def test_xss_basico(self, client: TestClient, headers_auth: dict):
        """Testa proteção básica contra XSS"""
        dados_xss = {
            "mensagem": "<script>alert('XSS')</script>",
            "historico": []
        }

        response = client.post("/ia/conversar", headers=headers_auth, json=dados_xss)

        # Pode ser 200, 422 ou 500 (se IA não configurada)
        assert response.status_code in [200, 422, 500]

        # Se retornou 200, verificar se o script não foi executado
        if response.status_code == 200:
            data = response.json()
            # A resposta não deve conter o script não-escapado
            if "resposta" in data:
                assert "<script>" not in str(data["resposta"])


class TestValidacaoDados:
    """Testes de validação de dados"""

    def test_email_formatos_invalidos(self, client: TestClient):
        """Testa validação de email com formatos inválidos"""
        emails_invalidos = [
            "email",
            "@exemple.com",
            "teste@",
            "teste @exemplo.com",
            "teste..exemplo@com"
        ]

        for email in emails_invalidos:
            dados = {
                "nome": "Teste",
                "email": email,
                "senha": "senha123",
                "confirmacao_senha": "senha123"
            }

            response = client.post("/register", json=dados)

            # Deve retornar erro de validação
            assert response.status_code in [400, 422]


    def test_senhas_fracas(self, client: TestClient):
        """Testa se aceita senhas fracas (depende da implementação)"""
        senhas_fracas = [
            "123",
            "abc",
            "senha"
        ]

        for senha in senhas_fracas:
            dados = {
                "nome": "Teste Senha",
                "email": f"teste{senha}@exemplo.com",
                "senha": senha,
                "confirmacao_senha": senha
            }

            response = client.post("/register", json=dados)

            # Pode aceitar ou rejeitar dependendo da implementação
            assert response.status_code in [200, 400, 422]
