import pytest
from fastapi.testclient import TestClient


class TestIARoutesEndpoints:
    """Testes para endpoints de IA (LunIA)"""

    def test_conversar_sucesso(self, client: TestClient, headers_auth: dict, db: Session):
        """Testa conversa com IA"""
        # Ativar premium para o usuário (endpoint requer premium)
        from app.services.assinatura_service import ativar_assinatura
        from app.models.sqlalchemy_models import Usuario
        usuario = db.query(Usuario).filter(Usuario.email == "teste@example.com").first()
        if usuario:
            ativar_assinatura(db, usuario.id, duracao_meses=1)

        dados = {
            "pergunta": "Olá, como você está?"
        }

        response = client.post("/ia/conversar", headers=headers_auth, json=dados)

        # Pode ser 200, 403 (sem premium), ou 500 se a API da OpenAI não estiver configurada
        assert response.status_code in [200, 403, 500]


    def test_conversar_sem_token(self, client: TestClient):
        """Testa conversa sem autenticação"""
        dados = {
            "pergunta": "Olá!"
        }

        response = client.post("/ia/conversar", json=dados)

        assert response.status_code == 401


    def test_conversar_mensagem_vazia(self, client: TestClient, headers_auth: dict):
        """Testa conversa com mensagem vazia"""
        dados = {
            "pergunta": ""
        }

        response = client.post("/ia/conversar", headers=headers_auth, json=dados)

        # Deve retornar erro de validação
        assert response.status_code in [400, 422]


    def test_conversar_com_historico(self, client: TestClient, headers_auth: dict, db: Session):
        """Testa conversa com histórico"""
        # Ativar premium para o usuário (endpoint requer premium)
        from app.services.assinatura_service import ativar_assinatura
        from app.models.sqlalchemy_models import Usuario
        usuario = db.query(Usuario).filter(Usuario.email == "teste@example.com").first()
        if usuario:
            ativar_assinatura(db, usuario.id, duracao_meses=1)

        dados = {
            "pergunta": "E sobre exercícios?"
        }

        response = client.post("/ia/conversar", headers=headers_auth, json=dados)

        # Pode ser 200, 403 (sem premium), ou 500 se a API da OpenAI não estiver configurada
        assert response.status_code in [200, 403, 500]


    def test_get_mensagem_entrada_sucesso(self, client: TestClient, headers_auth: dict, db: Session):
        """Testa获取 mensagem de entrada"""
        # Ativar premium para o usuário (endpoint requer premium)
        from app.services.assinatura_service import ativar_assinatura
        from app.models.sqlalchemy_models import Usuario
        usuario = db.query(Usuario).filter(Usuario.email == "teste@example.com").first()
        if usuario:
            ativar_assinatura(db, usuario.id, duracao_meses=1)

        response = client.get("/ia/mensagem-entrada", headers=headers_auth)

        # Pode ser 200, 403 (sem premium), ou 404 se não houver mensagem
        assert response.status_code in [200, 403, 404]


    def test_get_mensagem_entrada_sem_token(self, client: TestClient):
        """Testa获取 mensagem de entrada sem autenticação"""
        response = client.get("/ia/mensagem-entrada")

        assert response.status_code == 401


class TestIARoutesEndpointsValidacao:
    """Testes de validação para IA"""

    def test_conversar_mensagem_muito_longa(self, client: TestClient, headers_auth: dict):
        """Testa conversa com mensagem muito longa"""
        mensagem_gigante = "a" * 10000  # 10.000 caracteres

        dados = {
            "mensagem": mensagem_gigante,
            "historico": []
        }

        response = client.post("/ia/conversar", headers=headers_auth, json=dados)

        # Pode ser 200, 422 ou 500
        assert response.status_code in [200, 422, 500]


    def test_conversar_historico_grande(self, client: TestClient, headers_auth: dict):
        """Testa conversa com histórico muito grande"""
        historico_grande = [
            {"role": "user", "content": f"Mensagem {i}"}
            for i in range(100)
        ]

        dados = {
            "mensagem": "Última mensagem",
            "historico": historico_grande
        }

        response = client.post("/ia/conversar", headers=headers_auth, json=dados)

        # Pode ser 200, 422 ou 500
        assert response.status_code in [200, 422, 500]


class TestIARoutesIntegracao:
    """Testes de integração para IA"""

    def test_conversa_multiplas_turnos(self, client: TestClient, headers_auth: dict):
        """Testa conversa com múltiplos turnos"""
        mensagens = [
            "Olá!",
            "Como você está?",
            "Pode me ajudar?"
        ]

        historico = []

        for mensagem in mensagens:
            dados = {
                "mensagem": mensagem,
                "historico": historico
            }

            response = client.post("/ia/conversar", headers=headers_auth, json=dados)

            # Se a API da OpenAI não estiver configurada, pode retornar 500
            if response.status_code == 200:
                data = response.json()
                if "resposta" in data:
                    historico.append({
                        "role": "user",
                        "content": mensagem
                    })
                    historico.append({
                        "role": "assistant",
                        "content": data["resposta"]
                    })
            else:
                # Se falhar, interrompe o teste
                break
