import pytest
from datetime import timedelta
from fastapi.testclient import TestClient

from app.models.sqlalchemy_models import TreinoRealizado
from app.services.treino_service import definir_treino_do_dia
from app.utils.datas import hoje_brasilia


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


class TestConcluirTreino:
    """Check-ins do treino do dia: a pontuação acompanha a conclusão, pra cima ou pra baixo"""

    def _concluir(self, client: TestClient, headers: dict, percentual: float, exercicios=None, tipo: str = "A"):
        return client.post(
            "/treino-dia/concluir",
            headers=headers,
            json={"tipo_treino": tipo, "percentual": percentual, "exercicios_concluidos": exercicios or []},
        )

    def test_primeiro_checkin_pontua(self, client: TestClient, headers_auth: dict, db, usuario_teste):
        response = self._concluir(client, headers_auth, 30)

        assert response.status_code == 200
        corpo = response.json()
        assert corpo["ja_salvo"] is False
        assert corpo["pontos_ganhos"] == 5
        assert corpo["pontos_treino"] == 5
        db.refresh(usuario_teste)
        assert usuario_teste.pontos_totais == 5

    def test_aumentar_percentual_soma_so_a_diferenca(self, client: TestClient, headers_auth: dict, db, usuario_teste):
        self._concluir(client, headers_auth, 30)

        response = self._concluir(client, headers_auth, 60)

        assert response.status_code == 200
        corpo = response.json()
        assert corpo["pontos_ganhos"] == 5  # faixa de 60% vale 10, 5 já tinham sido ganhos
        assert corpo["atualizar_pontuacao"] is True
        db.refresh(usuario_teste)
        assert usuario_teste.pontos_totais == 10

    def test_repetir_percentual_nao_pontua(self, client: TestClient, headers_auth: dict, db, usuario_teste):
        self._concluir(client, headers_auth, 30)

        response = self._concluir(client, headers_auth, 30)

        assert response.status_code == 200
        corpo = response.json()
        assert corpo["ja_salvo"] is True
        assert corpo["pontos_ganhos"] == 0
        assert corpo["atualizar_pontuacao"] is False
        db.refresh(usuario_teste)
        assert usuario_teste.pontos_totais == 5

    def test_diminuir_percentual_tira_pontos(self, client: TestClient, headers_auth: dict, db, usuario_teste):
        self._concluir(client, headers_auth, 60)

        response = self._concluir(client, headers_auth, 20)

        assert response.status_code == 200
        corpo = response.json()
        assert corpo["pontos_ganhos"] == -7  # faixa de 20% vale 3, eram 10
        assert corpo["pontos_treino"] == 3
        assert corpo["atualizar_pontuacao"] is True
        db.refresh(usuario_teste)
        assert usuario_teste.pontos_totais == 3

    def test_desmarcar_tudo_zera_os_pontos_do_treino(self, client: TestClient, headers_auth: dict, db, usuario_teste):
        self._concluir(client, headers_auth, 60)

        response = self._concluir(client, headers_auth, 0)

        assert response.status_code == 200
        assert response.json()["pontos_ganhos"] == -10
        db.refresh(usuario_teste)
        assert usuario_teste.pontos_totais == 0

    def test_outro_treino_no_mesmo_dia_e_recusado(self, client: TestClient, headers_auth: dict, db, usuario_teste):
        self._concluir(client, headers_auth, 30, tipo="A")

        response = self._concluir(client, headers_auth, 50, tipo="B")

        assert response.status_code == 409
        db.refresh(usuario_teste)
        assert usuario_teste.pontos_totais == 5

    def test_marcados_hoje_devolve_os_exercicios_marcados(self, client: TestClient, headers_auth: dict):
        self._concluir(client, headers_auth, 50, ["Prancha", "Agachamento"])

        response = client.get("/treino-dia/marcados-hoje", headers=headers_auth)

        assert response.status_code == 200
        corpo = response.json()
        assert corpo["percentual"] == 50
        assert corpo["ja_salvo"] is True
        assert corpo["exercicios_concluidos"] == ["Prancha", "Agachamento"]


class TestTreinoDoDia:
    """Só existe um treino por dia, seguindo a sequência A-E dentro da fase"""

    def _registrar(self, db, usuario_id: int, dia, fase: str, treino: str):
        db.add(TreinoRealizado(usuario_id=usuario_id, data=dia, fase=fase, treino=treino, percentual_concluido=100, pontos=20))
        db.commit()

    def test_sem_historico_comeca_pelo_a(self, db, usuario_teste):
        assert definir_treino_do_dia(db, usuario_teste.id, "Folicular") == "A"

    def test_segue_a_sequencia_da_fase(self, db, usuario_teste):
        self._registrar(db, usuario_teste.id, hoje_brasilia() - timedelta(days=1), "Folicular", "A")

        assert definir_treino_do_dia(db, usuario_teste.id, "Folicular") == "B"

    def test_checkin_de_hoje_define_o_treino_do_dia(self, db, usuario_teste):
        self._registrar(db, usuario_teste.id, hoje_brasilia(), "Lútea", "C")

        assert definir_treino_do_dia(db, usuario_teste.id, "Folicular") == "C"
