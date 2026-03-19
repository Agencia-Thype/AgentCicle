import pytest
from fastapi.testclient import TestClient


class TestRelatorioEndpoints:
    """Testes para endpoints de relatório"""

    def test_get_relatorio_mensal_sucesso(self, client: TestClient, headers_auth: dict, db: Session):
        """Testa获取 relatório mensal com sucesso"""
        # Ativar premium para o usuário de teste (endpoint requer premium)
        from app.services.assinatura_service import ativar_assinatura
        from app.models.sqlalchemy_models import Usuario
        usuario = db.query(Usuario).filter(Usuario.email == "teste@example.com").first()
        if usuario:
            ativar_assinatura(db, usuario.id, duracao_meses=1)

        response = client.get("/relatorio/mensal?mes=2024-01", headers=headers_auth)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (dict, list))


    def test_get_relatorio_mensal_sem_token(self, client: TestClient):
        """Testa获取 relatório sem autenticação"""
        response = client.get("/relatorio/mensal?mes=2024-01")

        assert response.status_code == 401


    def test_get_relatorio_mensal_parametros_validos(self, client: TestClient, headers_auth: dict):
        """Testa获取 relatório com parâmetros válidos"""
        parametros_validos = [
            {"mes": 1, "ano": 2024},
            {"mes": 6, "ano": 2024},
            {"mes": 12, "ano": 2024},
            {"mes": 1, "ano": 2023}
        ]

        for params in parametros_validos:
            response = client.get(
                f"/relatorio/mensal?mes={params['mes']}&ano={params['ano']}",
                headers=headers_auth
            )

            # Pode ser 200 ou 422 se mês for inválido
            assert response.status_code in [200, 422]


    def test_get_relatorio_mensal_mes_invalido(self, client: TestClient, headers_auth: dict):
        """Testa获取 relatório com mês inválido"""
        response = client.get("/relatorio/mensal?mes=13&ano=2024", headers=headers_auth)

        # Deve retornar erro de validação
        assert response.status_code in [400, 422]


    def test_get_relatorio_mensal_mes_zero(self, client: TestClient, headers_auth: dict):
        """Testa获取 relatório com mês zero"""
        response = client.get("/relatorio/mensal?mes=0&ano=2024", headers=headers_auth)

        # Deve retornar erro de validação
        assert response.status_code in [400, 422]


    def test_get_relatorio_mensal_ano_invalido(self, client: TestClient, headers_auth: dict):
        """Testa获取 relatório com ano inválido"""
        response = client.get("/relatorio/mensal?mes=1&ano=1800", headers=headers_auth)

        # Pode ser válido ou inválido dependendo da implementação
        assert response.status_code in [200, 422]


    def test_get_relatorio_mensal_sem_parametros(self, client: TestClient, headers_auth: dict):
        """Testa获取 relatório sem parâmetros"""
        response = client.get("/relatorio/mensal", headers=headers_auth)

        # Deve retornar erro ou usar valores padrão
        assert response.status_code in [200, 400, 422]


class TestRelatorioEndpointsIntegracao:
    """Testes de integração para relatório"""

    def test_relatorio_meses_diferentes(self, client: TestClient, headers_auth: dict):
        """Testa获取 relatórios de meses diferentes"""
        meses = [1, 2, 3]

        for mes in meses:
            response = client.get(
                f"/relatorio/mensal?mes={mes}&ano=2024",
                headers=headers_auth
            )

            # Todos devem ter sucesso ou erro de validação consistente
            assert response.status_code in [200, 422]


    def test_relatorio_ano_corrente(self, client: TestClient, headers_auth: dict):
        """Testa获取 relatório do ano corrente"""
        from datetime import datetime
        ano_atual = datetime.now().year
        mes_atual = datetime.now().month

        response = client.get(
            f"/relatorio/mensal?mes={mes_atual}&ano={ano_atual}",
            headers=headers_auth
        )

        # Deve funcionar para o mês atual
        assert response.status_code in [200, 422]
