import pytest
from datetime import date, datetime, timedelta

from app.models.sqlalchemy_models import AguaRegistro, DoseRotina, ItemRotina
from app.services import rotina_service

HOJE = date(2026, 9, 11)  # sexta-feira


@pytest.fixture
def relogio(monkeypatch):
    """Fixa o "agora" do serviço em 11/09/2026 às 10:00 (Brasília)."""
    agora = {"valor": datetime(2026, 9, 11, 10, 0)}
    monkeypatch.setattr(rotina_service, "agora_brasilia", lambda: agora["valor"])
    monkeypatch.setattr(rotina_service, "hoje_brasilia", lambda: agora["valor"].date())
    return agora


def _item(**extra):
    dados = {
        "nome": "Ômega 3",
        "categoria": "suplemento",
        "dosagem": "1 cápsula",
        "horarios": ["08:00", "21:00"],
        "data_inicio": "2026-09-01",
    }
    dados.update(extra)
    return dados


def _criar(client, headers, **extra):
    resposta = client.post("/rotina/itens", json=_item(**extra), headers=headers)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


class TestItens:
    def test_criar_e_listar(self, client, headers_auth, relogio):
        item = _criar(client, headers_auth)

        assert item["horarios"] == ["08:00", "21:00"]
        assert item["lembrete_ativo"] is True
        itens = client.get("/rotina/itens", headers=headers_auth).json()["itens"]
        assert [i["nome"] for i in itens] == ["Ômega 3"]

    def test_horarios_sao_ordenados_sem_repeticao(self, client, headers_auth, relogio):
        item = _criar(client, headers_auth, horarios=["21:00", "08:00", "08:00"])
        assert item["horarios"] == ["08:00", "21:00"]

    @pytest.mark.parametrize("extra", [
        {"horarios": ["25:00"]},
        {"horarios": []},
        {"nome": "   "},
        {"categoria": "chá"},
        {"frequencia": "dias_especificos", "dias_semana": []},
        {"dias_semana": [7], "frequencia": "dias_especificos"},
        {"data_fim": "2026-08-01"},
    ])
    def test_dados_invalidos(self, client, headers_auth, relogio, extra):
        resposta = client.post("/rotina/itens", json=_item(**extra), headers=headers_auth)
        assert resposta.status_code == 422

    def test_estoque_so_vale_com_controle_ligado(self, client, headers_auth, relogio):
        sem_controle = _criar(client, headers_auth, estoque_atual=10)
        com_controle = _criar(client, headers_auth, controle_estoque=True, estoque_atual=10)

        assert sem_controle["estoque_atual"] is None
        assert com_controle["estoque_atual"] == 10
        assert com_controle["estoque_alerta"] == 5

    def test_sem_token(self, client):
        assert client.get("/rotina/itens").status_code == 401

    def test_editar(self, client, headers_auth, relogio):
        item = _criar(client, headers_auth)
        resposta = client.put(
            f"/rotina/itens/{item['id']}", json=_item(nome="Vitamina D", categoria="vitamina"), headers=headers_auth
        )
        assert resposta.status_code == 200
        assert resposta.json()["nome"] == "Vitamina D"

    def test_nao_mexe_em_item_de_outra_usuaria(self, client, db, headers_auth, usuario_admin, relogio):
        alheio = ItemRotina(
            usuario_id=usuario_admin.id, nome="Remédio", categoria="medicamento",
            frequencia="todos_os_dias", horarios=["08:00"], data_inicio=HOJE, ativo=1,
        )
        db.add(alheio)
        db.commit()

        assert client.get(f"/rotina/itens/{alheio.id}", headers=headers_auth).status_code == 404
        assert client.put(f"/rotina/itens/{alheio.id}", json=_item(), headers=headers_auth).status_code == 404
        assert client.delete(f"/rotina/itens/{alheio.id}", headers=headers_auth).status_code == 404
        dose = {"item_id": alheio.id, "horario": "08:00"}
        assert client.post("/rotina/doses", json=dose, headers=headers_auth).status_code == 404

    def test_excluir_tira_da_agenda_mas_nao_do_historico(self, client, db, headers_auth, usuario_teste, relogio):
        item = _criar(client, headers_auth, horarios=["08:00"])
        db.add(DoseRotina(usuario_id=usuario_teste.id, item_id=item["id"], data=HOJE - timedelta(days=1), horario="08:00"))
        db.commit()

        assert client.delete(f"/rotina/itens/{item['id']}", headers=headers_auth).status_code == 200

        assert client.get("/rotina/itens", headers=headers_auth).json()["itens"] == []
        assert client.get("/rotina/hoje", headers=headers_auth).json()["doses"] == []
        ontem = client.get("/rotina/historico", headers=headers_auth).json()["dias"][1]
        assert (ontem["doses_previstas"], ontem["doses_tomadas"]) == (1, 1)


class TestAgenda:
    def test_status_das_doses(self, client, headers_auth, relogio):
        _criar(client, headers_auth, horarios=["08:00", "09:45", "12:00"])

        hoje = client.get("/rotina/hoje", headers=headers_auth).json()

        # 10:00: 08:00 passou há 2h; 09:45 ainda está na tolerância de 30 min.
        assert [(d["horario"], d["status"]) for d in hoje["doses"]] == [
            ("08:00", "atrasado"), ("09:45", "pendente"), ("12:00", "pendente"),
        ]
        assert hoje["proxima"]["horario"] == "09:45"
        assert hoje["proxima"]["minutos"] == -15
        assert (hoje["total"], hoje["tomadas"]) == (3, 0)

    def test_marcar_e_desfazer_dose(self, client, db, headers_auth, relogio):
        item = _criar(client, headers_auth)
        dose = {"item_id": item["id"], "horario": "08:00"}

        marcada = client.post("/rotina/doses", json=dose, headers=headers_auth).json()
        assert marcada["registrada"] is True
        assert marcada["resumo"]["tomadas"] == 1
        assert marcada["resumo"]["doses"][0]["status"] == "tomado"

        # Marcar de novo não duplica.
        assert client.post("/rotina/doses", json=dose, headers=headers_auth).json()["registrada"] is False
        assert db.query(DoseRotina).count() == 1

        desfeita = client.post("/rotina/doses/desfazer", json=dose, headers=headers_auth).json()
        assert desfeita["desfeita"] is True
        assert desfeita["resumo"]["doses"][0]["status"] == "atrasado"

    def test_dose_fora_do_horario_ou_no_futuro(self, client, headers_auth, relogio):
        item = _criar(client, headers_auth)

        fora = client.post("/rotina/doses", json={"item_id": item["id"], "horario": "10:00"}, headers=headers_auth)
        futuro = client.post(
            "/rotina/doses", json={"item_id": item["id"], "horario": "08:00", "data": "2026-09-12"}, headers=headers_auth
        )
        assert fora.status_code == 400
        assert futuro.status_code == 400

    def test_dias_especificos(self, client, headers_auth, relogio):
        # Sexta = 5 (0 é domingo).
        _criar(client, headers_auth, nome="Seg e qua", frequencia="dias_especificos", dias_semana=[1, 3])
        _criar(client, headers_auth, nome="Sexta", frequencia="dias_especificos", dias_semana=[5])

        nomes = {d["nome"] for d in client.get("/rotina/hoje", headers=headers_auth).json()["doses"]}
        assert nomes == {"Sexta"}

    def test_inicio_e_fim(self, client, headers_auth, relogio):
        _criar(client, headers_auth, nome="Começa amanhã", data_inicio="2026-09-12")
        _criar(client, headers_auth, nome="Acabou ontem", data_inicio="2026-09-01", data_fim="2026-09-10")
        _criar(client, headers_auth, nome="Acaba hoje", data_inicio="2026-09-01", data_fim="2026-09-11")

        nomes = {d["nome"] for d in client.get("/rotina/hoje", headers=headers_auth).json()["doses"]}
        assert nomes == {"Acaba hoje"}

    def test_estoque_desce_e_volta(self, client, headers_auth, relogio):
        item = _criar(client, headers_auth, controle_estoque=True, estoque_atual=3, estoque_alerta=2)
        dose = {"item_id": item["id"], "horario": "08:00"}

        client.post("/rotina/doses", json=dose, headers=headers_auth)
        depois = client.get(f"/rotina/itens/{item['id']}", headers=headers_auth).json()
        assert (depois["estoque_atual"], depois["estoque_baixo"]) == (2, True)

        client.post("/rotina/doses/desfazer", json=dose, headers=headers_auth)
        assert client.get(f"/rotina/itens/{item['id']}", headers=headers_auth).json()["estoque_atual"] == 3


class TestAgua:
    def test_meta_sugerida(self, client, db, headers_auth, usuario_teste, relogio):
        assert client.get("/rotina/agua", headers=headers_auth).json()["meta_ml"] == 2000

        usuario_teste.peso_atual = 70
        db.commit()
        agua = client.get("/rotina/agua", headers=headers_auth).json()
        assert agua["meta_ml"] == 2500  # 70 kg x 35 ml = 2450, arredondado
        assert agua["meta_personalizada"] is False

    def test_registrar_e_desfazer(self, client, headers_auth, relogio):
        client.post("/rotina/agua", json={"ml": 300}, headers=headers_auth)
        agua = client.post("/rotina/agua", json={"ml": 500}, headers=headers_auth).json()
        assert (agua["total_ml"], agua["faltam_ml"], agua["percentual"]) == (800, 1200, 40)
        assert [r["hora"] for r in agua["registros"]] == ["10:00", "10:00"]

        agua = client.delete(f"/rotina/agua/{agua['registros'][0]['id']}", headers=headers_auth).json()
        assert agua["total_ml"] == 500

    @pytest.mark.parametrize("ml", [0, -200, 5000])
    def test_ml_invalido(self, client, headers_auth, relogio, ml):
        assert client.post("/rotina/agua", json={"ml": ml}, headers=headers_auth).status_code == 422

    def test_config(self, client, headers_auth, relogio):
        resposta = client.put(
            "/rotina/agua/config",
            json={"meta_ml": 2500, "lembretes": ["16:00", "09:00"], "lembretes_ativos": False},
            headers=headers_auth,
        )
        agua = resposta.json()
        assert (agua["meta_ml"], agua["lembretes"], agua["lembretes_ativos"]) == (2500, ["09:00", "16:00"], False)
        assert agua["meta_personalizada"] is True

    def test_sequencia(self, client, db, headers_auth, usuario_teste, relogio):
        # Bateu a meta (2 L) nos 3 dias antes de hoje; o 4º dia ficou abaixo.
        for dias_atras, ml in [(1, 2000), (2, 2100), (3, 2500), (4, 1000)]:
            db.add(AguaRegistro(usuario_id=usuario_teste.id, data=HOJE - timedelta(days=dias_atras), ml=ml))
        db.add(AguaRegistro(usuario_id=usuario_teste.id, data=HOJE, ml=500))
        db.commit()

        # Hoje ainda não bateu, mas o dia não acabou: não quebra a sequência.
        assert client.get("/rotina/agua", headers=headers_auth).json()["sequencia_dias"] == 3

        client.post("/rotina/agua", json={"ml": 1500}, headers=headers_auth)
        assert client.get("/rotina/agua", headers=headers_auth).json()["sequencia_dias"] == 4


class TestHistorico:
    def test_adesao_esquecidas_e_sequencia(self, client, db, headers_auth, usuario_teste, relogio):
        item = _criar(client, headers_auth, horarios=["08:00"])
        # Tomou de 08/09 a 11/09; esqueceu 07/09.
        for dias_atras in range(0, 4):
            db.add(DoseRotina(
                usuario_id=usuario_teste.id, item_id=item["id"],
                data=HOJE - timedelta(days=dias_atras), horario="08:00",
            ))
        db.commit()

        historico = client.get("/rotina/historico", headers=headers_auth).json()

        assert len(historico["dias"]) == 7
        assert historico["dias"][0]["data"] == "2026-09-11"
        assert historico["dias"][4]["data"] == "2026-09-07"
        assert historico["dias"][4]["esquecidas"] == [{"item_id": item["id"], "nome": "Ômega 3", "horario": "08:00"}]
        assert historico["sequencia_rotina"] == 4
        assert historico["resumo"]["doses_tomadas"] == 4
        assert historico["resumo"]["doses_previstas"] == 7
        assert historico["itens"][0]["adesao"] == 57

    def test_dia_sem_nada_previsto_nao_quebra_sequencia(self):
        dias = [(HOJE - timedelta(days=i), status) for i, status in enumerate([True, None, True, False])]
        assert rotina_service._sequencia(dias, HOJE) == 2

    def test_limite_de_dias(self, client, headers_auth, relogio):
        assert client.get("/rotina/historico?dias=31", headers=headers_auth).status_code == 422
        assert len(client.get("/rotina/historico?dias=30", headers=headers_auth).json()["dias"]) == 30
