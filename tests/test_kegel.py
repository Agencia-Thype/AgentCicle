from fastapi.testclient import TestClient

from app.models.sqlalchemy_models import KegelDiario
from app.services.kegel_service import PONTOS_KEGEL_DIA


class TestPontuacaoKegel:
    """Cada exercício de Kegel pontua uma vez por dia; o dia inteiro vale PONTOS_KEGEL_DIA"""

    def _concluir(self, client: TestClient, headers: dict, exercicio_id: str, nivel: str = "iniciante", percentual: float = 100):
        return client.post(
            "/kegel/concluir-exercicio",
            headers=headers,
            json={"nivel": nivel, "exercicio_id": exercicio_id, "percentual": percentual},
        )

    def test_primeiro_exercicio_do_dia_pontua(self, client: TestClient, headers_auth: dict, db, usuario_teste):
        response = self._concluir(client, headers_auth, "kegel_ini_ex1")

        assert response.status_code == 200
        assert response.json()["pontos_ganhos"] == 3
        db.refresh(usuario_teste)
        assert usuario_teste.pontos_totais == 3

    def test_repetir_exercicio_no_mesmo_dia_nao_pontua(self, client: TestClient, headers_auth: dict, db, usuario_teste):
        self._concluir(client, headers_auth, "kegel_ini_ex1")

        response = self._concluir(client, headers_auth, "kegel_ini_ex1")

        # Antes a rota devolvia o objeto do banco nesse caso e quebrava.
        assert response.status_code == 200
        assert response.json()["pontos_ganhos"] == 0
        db.refresh(usuario_teste)
        assert usuario_teste.pontos_totais == 3

    def test_nivel_completo_vale_o_dia_inteiro(self, client: TestClient, headers_auth: dict, db, usuario_teste):
        ganhos = [
            self._concluir(client, headers_auth, exercicio).json()["pontos_ganhos"]
            for exercicio in ("kegel_ini_ex1", "kegel_ini_ex2", "kegel_ini_ex3")
        ]

        assert ganhos == [3, 3, 4]
        db.refresh(usuario_teste)
        assert usuario_teste.pontos_totais == PONTOS_KEGEL_DIA

    def test_trocar_de_nivel_nao_passa_do_limite_do_dia(self, client: TestClient, headers_auth: dict, db, usuario_teste):
        for exercicio in ("kegel_ini_ex1", "kegel_ini_ex2", "kegel_ini_ex3"):
            self._concluir(client, headers_auth, exercicio)

        response = self._concluir(client, headers_auth, "kegel_int_ex1", nivel="intermediario")

        assert response.status_code == 200
        assert response.json()["pontos_ganhos"] == 0
        db.refresh(usuario_teste)
        assert usuario_teste.pontos_totais == PONTOS_KEGEL_DIA

    def test_conclusao_parcial_nao_pontua(self, client: TestClient, headers_auth: dict, db, usuario_teste):
        response = self._concluir(client, headers_auth, "kegel_ini_ex1", percentual=50)

        assert response.status_code == 200
        assert response.json()["pontos_ganhos"] == 0
        db.refresh(usuario_teste)
        assert (usuario_teste.pontos_totais or 0) == 0

    def test_exercicio_de_outro_nivel_e_recusado(self, client: TestClient, headers_auth: dict, db, usuario_teste):
        response = self._concluir(client, headers_auth, "kegel_int_ex1", nivel="iniciante")

        assert response.status_code == 400
        db.refresh(usuario_teste)
        assert (usuario_teste.pontos_totais or 0) == 0

    def test_registro_do_dia_fica_salvo(self, client: TestClient, headers_auth: dict, db, usuario_teste):
        self._concluir(client, headers_auth, "kegel_ini_ex2")

        registros = db.query(KegelDiario).filter(KegelDiario.usuario_id == usuario_teste.id).all()

        assert [(r.exercicio_id, r.nivel, r.pontos) for r in registros] == [("kegel_ini_ex2", "iniciante", 3)]
