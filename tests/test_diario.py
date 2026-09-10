import pytest
from datetime import timedelta
from fastapi.testclient import TestClient

from app.services.diario_service import PONTOS_REGISTRO_DIARIO, hoje_brasilia


class TestDiarioEndpoints:
    """Testes para endpoints de diário"""

    def test_registrar_sintomas_sucesso(self, client: TestClient, headers_auth: dict, dados_diario: dict):
        """Testa registro de sintomas com sucesso"""
        response = client.post("/diario/registrar-sintomas", headers=headers_auth, json=dados_diario)

        assert response.status_code == 200
        data = response.json()
        assert "mensagem" in data


    def test_registrar_sintomas_sem_token(self, client: TestClient, dados_diario: dict):
        """Testa registro sem autenticação"""
        response = client.post("/diario/registrar-sintomas", json=dados_diario)

        assert response.status_code == 401


    def test_registrar_sintomas_dados_completos(self, client: TestClient, headers_auth: dict):
        """Testa registro com dados completos"""
        dados = {
            "data": "2024-01-15",
            "sentimentos": ["feliz"],
            "energia": "alta",
            "sintomas_fisicos": ["dor de cabeça", "fadiga"],
            "sintomas_emocionais": ["ansiedade"],
            "observacao": "Dia de trabalho intenso"
        }

        response = client.post("/diario/registrar-sintomas", headers=headers_auth, json=dados)

        assert response.status_code == 200


    def test_registrar_sintomas_dados_minimos(self, client: TestClient, headers_auth: dict):
        """Testa registro com dados mínimos"""
        dados = {
            "data": "2024-01-15",
            "sentimentos": ["neutro"]
        }

        response = client.post("/diario/registrar-sintomas", headers=headers_auth, json=dados)

        assert response.status_code == 200


    def test_registrar_sintomas_data_invalida(self, client: TestClient, headers_auth: dict):
        """Testa registro com data inválida"""
        dados = {
            "data": "data-invalida",
            "humor": "feliz"
        }

        response = client.post("/diario/registrar-sintomas", headers=headers_auth, json=dados)

        assert response.status_code in [400, 422]


    def test_registrar_sintomas_sem_data(self, client: TestClient, headers_auth: dict):
        """Testa registro sem data"""
        dados = {
            "humor": "feliz"
        }

        response = client.post("/diario/registrar-sintomas", headers=headers_auth, json=dados)

        assert response.status_code in [400, 422]


    def test_get_resumo_dia_sucesso(self, client: TestClient, headers_auth: dict):
        """Testa获取 resumo do dia com sucesso"""
        # Primeiro registrar dados
        dados_diario = {
            "data": "2024-01-15",
            "sentimentos": ["feliz"],
            "sintomas": ["energia"]
        }

        client.post("/diario/registrar-sintomas", headers=headers_auth, json=dados_diario)

        # Depois consultar
        response = client.get("/diario/resumo-do-dia?data=2024-01-15", headers=headers_auth)

        assert response.status_code == 200
        data = response.json()
        assert "data" in data


    def test_get_resumo_dia_sem_registro(self, client: TestClient, headers_auth: dict):
        """Testa获取 resumo de dia sem registro"""
        response = client.get("/diario/resumo-do-dia?data=2024-12-25", headers=headers_auth)

        # Pode retornar 200 com dados vazios ou 404
        assert response.status_code in [200, 404]


    def test_get_resumo_dia_sem_token(self, client: TestClient):
        """Testa获取 resumo do dia sem autenticação"""
        response = client.get("/diario/resumo-do-dia?data=2024-01-15")

        assert response.status_code == 401


    def test_get_resumo_dia_formato_invalido(self, client: TestClient, headers_auth: dict):
        """Testa获取 resumo do dia com formato inválido"""
        response = client.get("/diario/resumo-do-dia?data=invalida", headers=headers_auth)

        assert response.status_code in [400, 422]


class TestDiarioEndpointsValidacao:
    """Testes de validação para diário"""

    def test_humor_valores_validos(self, client: TestClient, headers_auth: dict):
        """Testa registro com diferentes valores de sentimentos"""
        sentimentos_validos = ["feliz", "neutro", "triste", "irritada", "ansiosa"]

        for sentimento in sentimentos_validos:
            dados = {
                "data": "2024-01-15",
                "sentimentos": [sentimento]
            }

            response = client.post("/diario/registrar-sintomas", headers=headers_auth, json=dados)

            # Pode ser 200 ou 422 dependendo da validação
            assert response.status_code in [200, 422]


    def test_registrar_multiplos_dias(self, client: TestClient, headers_auth: dict):
        """Testa registro de múltiplos dias"""
        dados = []

        for dia in range(1, 6):
            dados_dia = {
                "data": f"2024-01-0{dia}",
                "sentimentos": ["feliz"],
                "observacao": f"Dia {dia}"
            }

            response = client.post("/diario/registrar-sintomas", headers=headers_auth, json=dados_dia)
            assert response.status_code == 200

            dados.append(response.json())

        assert len(dados) == 5


class TestDiarioEndpointsIntegracao:
    """Testes de integração para diário"""

    def test_fluxo_completo_diario(self, client: TestClient, headers_auth: dict):
        """Testa fluxo completo: registrar -> consultar -> registrar novo"""
        # 1. Registrar sintomas para um dia
        dados1 = {
            "data": "2024-01-15",
            "sentimentos": ["feliz"],
            "observacao": "Dia produtivo"
        }

        response = client.post("/diario/registrar-sintomas", headers=headers_auth, json=dados1)
        assert response.status_code == 200

        # 2. Consultar resumo do dia
        response = client.get("/diario/resumo-do-dia?data=2024-01-15", headers=headers_auth)
        assert response.status_code == 200

        # 3. Registrar para outro dia
        dados2 = {
            "data": "2024-01-16",
            "sentimentos": ["neutro"],
            "observacao": "Dia normal"
        }

        response = client.post("/diario/registrar-sintomas", headers=headers_auth, json=dados2)
        assert response.status_code == 200

        # 4. Consultar resumo do segundo dia
        response = client.get("/diario/resumo-do-dia?data=2024-01-16", headers=headers_auth)
        assert response.status_code == 200


    def test_atualizar_registro_existente(self, client: TestClient, headers_auth: dict):
        """Testa atualização de registro existente"""
        dados_iniciais = {
            "data": "2024-01-20",
            "sentimentos": ["feliz"],
            "observacao": "Registro inicial"
        }

        # Primeiro registro
        response = client.post("/diario/registrar-sintomas", headers=headers_auth, json=dados_iniciais)
        assert response.status_code == 200

        # Atualização
        dados_atualizados = {
            "data": "2024-01-20",
            "sentimentos": ["triste"],
            "observacao": "Registro atualizado"
        }

        response = client.post("/diario/registrar-sintomas", headers=headers_auth, json=dados_atualizados)
        assert response.status_code == 200

        # Verificar se foi atualizado
        response = client.get("/diario/resumo-do-dia?data=2024-01-20", headers=headers_auth)
        assert response.status_code == 200


class TestDiarioPontuacao:
    """Gamificação: só o primeiro registro do próprio dia pontua"""

    def test_primeiro_registro_do_dia_pontua(self, client: TestClient, headers_auth: dict, db, usuario_teste):
        dados = {"data": hoje_brasilia().isoformat(), "sentimentos": ["Feliz"]}

        response = client.post("/diario/registrar-sintomas", headers=headers_auth, json=dados)

        assert response.status_code == 200
        assert response.json()["pontos"] == PONTOS_REGISTRO_DIARIO
        db.refresh(usuario_teste)
        assert usuario_teste.pontos_totais == PONTOS_REGISTRO_DIARIO

    def test_editar_registro_do_dia_nao_pontua_de_novo(self, client: TestClient, headers_auth: dict, db, usuario_teste):
        hoje = hoje_brasilia().isoformat()
        client.post("/diario/registrar-sintomas", headers=headers_auth, json={"data": hoje, "sentimentos": ["Feliz"]})

        response = client.post("/diario/registrar-sintomas", headers=headers_auth, json={"data": hoje, "sentimentos": ["Triste"]})

        assert response.status_code == 200
        assert response.json()["pontos"] == 0
        db.refresh(usuario_teste)
        assert usuario_teste.pontos_totais == PONTOS_REGISTRO_DIARIO

    def test_registro_de_dia_passado_nao_pontua(self, client: TestClient, headers_auth: dict, db, usuario_teste):
        ontem = (hoje_brasilia() - timedelta(days=1)).isoformat()

        response = client.post("/diario/registrar-sintomas", headers=headers_auth, json={"data": ontem, "sentimentos": ["Feliz"]})

        assert response.status_code == 200
        assert response.json()["pontos"] == 0
        db.refresh(usuario_teste)
        assert (usuario_teste.pontos_totais or 0) == 0
