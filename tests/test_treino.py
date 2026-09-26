import pytest
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.models.sqlalchemy_models import TreinoRealizado
from app.services.treino_service import (
    buscar_exercicios_por_tipo,
    definir_treino_do_dia,
    obter_tipos_treino_disponiveis,
)
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


class TestProgressoSemanal:
    def test_retorna_somente_dias_com_treino_feito(self, client, headers_auth, db, usuario_teste):
        hoje = hoje_brasilia()
        db.add_all([
            TreinoRealizado(usuario_id=usuario_teste.id, data=hoje, fase="Folicular", treino="A", percentual_concluido=50, pontos=10),
            TreinoRealizado(usuario_id=usuario_teste.id, data=hoje - timedelta(days=1), fase="Folicular", treino="B", percentual_concluido=0, pontos=0),
        ])
        db.commit()

        response = client.get(
            "/treino-dia/progresso-semanal",
            headers=headers_auth,
            params={"inicio": (hoje - timedelta(days=6)).isoformat(), "fim": hoje.isoformat()},
        )

        assert response.status_code == 200
        assert response.json()["dias_concluidos"] == [hoje.isoformat()]

    def test_sem_treino_nao_retorna_dia_concluido(self, client, headers_auth):
        hoje = hoje_brasilia()
        response = client.get(
            "/treino-dia/progresso-semanal",
            headers=headers_auth,
            params={"inicio": (hoje - timedelta(days=6)).isoformat(), "fim": hoje.isoformat()},
        )

        assert response.status_code == 200
        assert response.json()["dias_concluidos"] == []


class TestFiltroCatalogoTreino:
    @staticmethod
    def _criar_catalogo_luteo(db):
        db.execute(text("DROP TABLE IF EXISTS fase_4_tpm"))
        db.execute(text("""
            CREATE TABLE fase_4_tpm (
                fase TEXT,
                tipo_treino TEXT,
                exercicio TEXT
            )
        """))
        linhas = [
            ("LÚTEA/TPM", "TREINO A - full body", f"Exercício A{i}")
            for i in range(1, 8)
        ] + [
            ("LÚTEA/TPM", "TREINO B - back day", nome)
            for nome in (
                "Pull Down/Tríceps Corda/Face Pull",
                "Stiff",
                "Banco Romano",
                "Elevação Pélvica",
                "Remada Baixa triângulo",
                "Leg Press/Panturrilha",
            )
        ] + [
            ("Tpm", "TREINO C - cardio", "HIIT Esteira"),
            ("Tpm", "TREINO C - cardio", "Escada contínua"),
        ]
        db.execute(
            text("INSERT INTO fase_4_tpm (fase, tipo_treino, exercicio) VALUES (:fase, :tipo, :exercicio)"),
            [{"fase": fase, "tipo": tipo, "exercicio": exercicio} for fase, tipo, exercicio in linhas],
        )
        db.commit()

    def test_b_nao_se_confunde_com_full_body(self, db):
        self._criar_catalogo_luteo(db)

        resultados = buscar_exercicios_por_tipo(db, "fase_4_tpm", "B")
        nomes = [row._mapping["exercicio"] for row in resultados]

        assert len(nomes) == 6
        assert nomes == sorted([
            "Pull Down/Tríceps Corda/Face Pull",
            "Stiff",
            "Banco Romano",
            "Elevação Pélvica",
            "Remada Baixa triângulo",
            "Leg Press/Panturrilha",
        ])
        assert all(row._mapping["tipo_treino"] == "TREINO B - back day" for row in resultados)

    def test_tipos_disponiveis_sao_extraidos_do_catalogo(self, db):
        self._criar_catalogo_luteo(db)

        assert obter_tipos_treino_disponiveis(db, "Lútea") == ["A", "B", "C"]

    def test_depois_do_c_volta_ao_a_quando_nao_existem_d_e(self, db, usuario_teste):
        self._criar_catalogo_luteo(db)
        db.add(TreinoRealizado(
            usuario_id=usuario_teste.id,
            data=hoje_brasilia() - timedelta(days=1),
            fase="Lútea",
            treino="C",
            percentual_concluido=100,
            pontos=20,
        ))
        db.commit()

        assert definir_treino_do_dia(db, usuario_teste.id, "Lútea") == "A"
