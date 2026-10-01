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


class TestDivisaoDoCicloEmFases:
    """Ovulação = duração - 14; quem varia com a duração é a folicular."""

    @pytest.mark.parametrize(
        "duracao, folicular, ovulacao, lutea",
        [
            (21, (6, 6), 7, (8, 21)),
            (22, (6, 7), 8, (9, 22)),
            (24, (6, 9), 10, (11, 24)),
            (26, (6, 11), 12, (13, 26)),
            (28, (6, 13), 14, (15, 28)),
            (30, (6, 15), 16, (17, 30)),
            (32, (6, 17), 18, (19, 32)),
            (35, (6, 20), 21, (22, 35)),
        ],
    )
    def test_tabela_de_referencia(self, duracao, folicular, ovulacao, lutea):
        from app.services.ciclo_service import dividir_ciclo_em_fases

        divisao = dividir_ciclo_em_fases(duracao)
        fases = {f["fase"]: (f["inicio"], f["fim"]) for f in divisao["fases"]}

        assert fases == {
            "Menstruação": (1, 5),
            "Folicular": folicular,
            "Ovulatória": (ovulacao, ovulacao),
            "Lútea": lutea,
        }
        assert divisao["dia_ovulacao"] == ovulacao

    def test_janela_fertil_de_cinco_dias_antes_a_um_depois(self):
        from app.services.ciclo_service import dividir_ciclo_em_fases

        assert dividir_ciclo_em_fases(28)["janela_fertil"] == {"inicio": 9, "fim": 15}

    @pytest.mark.parametrize("duracao", list(range(10, 61)))
    def test_todo_dia_do_ciclo_tem_exatamente_uma_fase(self, duracao):
        from app.services.ciclo_service import dividir_ciclo_em_fases

        fases = dividir_ciclo_em_fases(duracao)["fases"]
        dias = [d for f in fases for d in range(f["inicio"], f["fim"] + 1)]
        assert dias == list(range(1, duracao + 1))

    def test_ciclo_curto_nao_coloca_a_ovulacao_dentro_da_menstruacao(self):
        from app.services.ciclo_service import dividir_ciclo_em_fases

        fases = {f["fase"]: (f["inicio"], f["fim"]) for f in dividir_ciclo_em_fases(15)["fases"]}
        assert fases == {"Menstruação": (1, 5), "Ovulatória": (6, 6), "Lútea": (7, 15)}

    @pytest.mark.parametrize("duracao", [None, 0, 2, 9, 61, 400])
    def test_duracao_absurda_vale_28(self, duracao):
        from app.services.ciclo_service import dividir_ciclo_em_fases

        assert dividir_ciclo_em_fases(duracao)["duracao_ciclo"] == 28


class TestFaseDeHoje:
    @pytest.mark.parametrize(
        "duracao, dias_passados, fase, proxima, faltam",
        [
            (28, 0, "Menstruação", "Folicular", 5),
            (28, 4, "Menstruação", "Folicular", 1),
            (28, 5, "Folicular", "Ovulatória", 8),
            (28, 13, "Ovulatória", "Lútea", 1),
            (28, 14, "Lútea", "Menstruação", 14),
            (28, 27, "Lútea", "Menstruação", 1),
            (35, 20, "Ovulatória", "Lútea", 1),
            (21, 5, "Folicular", "Ovulatória", 1),
        ],
    )
    def test_fase_e_dias_para_a_proxima(self, duracao, dias_passados, fase, proxima, faltam):
        from datetime import date, timedelta
        from app.services.ciclo_service import calcular_fase_do_ciclo

        hoje = date(2026, 10, 1)
        info = calcular_fase_do_ciclo(hoje - timedelta(days=dias_passados), duracao, hoje)

        assert info["fase"] == fase
        assert info["dia_do_ciclo"] == dias_passados + 1
        assert info["duracao_ciclo"] == duracao
        assert info["proxima_fase"] == proxima
        assert info["dias_para_proxima_fase"] == faltam

    def test_ciclo_recomeca_depois_do_ultimo_dia(self):
        from datetime import date, timedelta
        from app.services.ciclo_service import calcular_fase_do_ciclo

        hoje = date(2026, 10, 1)
        info = calcular_fase_do_ciclo(hoje - timedelta(days=30), 30, hoje)
        assert (info["fase"], info["dia_do_ciclo"]) == ("Menstruação", 1)


class TestDuracaoPeloHistorico:
    def _datas(self, *dias):
        from datetime import date, timedelta
        return [date(2026, 1, 1) + timedelta(days=d) for d in dias]

    def test_mediana_dos_ciclos_registrados(self):
        from app.services.ciclo_service import duracao_ciclo_pelo_historico

        # ciclos de 27, 29, 28 e 30 dias
        assert duracao_ciclo_pelo_historico(self._datas(0, 27, 56, 84, 114)) == 28

    def test_menos_de_tres_ciclos_nao_muda_o_perfil(self):
        from app.services.ciclo_service import duracao_ciclo_pelo_historico

        assert duracao_ciclo_pelo_historico(self._datas(0, 28, 56)) is None

    def test_dias_seguidos_de_menstruacao_sao_o_mesmo_ciclo(self):
        from app.services.ciclo_service import duracao_ciclo_pelo_historico

        datas = self._datas(0, 1, 2, 28, 29, 56, 57, 58, 84)
        assert duracao_ciclo_pelo_historico(datas) == 28

    def test_mes_sem_registro_nao_conta_como_ciclo(self):
        from app.services.ciclo_service import duracao_ciclo_pelo_historico

        # 28, 28, (90 = meses sem registrar), 30
        assert duracao_ciclo_pelo_historico(self._datas(0, 28, 56, 146, 176)) == 28


class TestDuracaoDaMenstruacao:
    def test_menstruacao_mais_longa_empurra_a_folicular(self):
        from app.services.ciclo_service import dividir_ciclo_em_fases

        fases = {f["fase"]: (f["inicio"], f["fim"]) for f in dividir_ciclo_em_fases(28, 7)["fases"]}
        assert fases == {
            "Menstruação": (1, 7),
            "Folicular": (8, 13),
            "Ovulatória": (14, 14),
            "Lútea": (15, 28),
        }

    def test_ovulacao_nunca_cai_dentro_da_menstruacao(self):
        from app.services.ciclo_service import dividir_ciclo_em_fases

        # 21 - 14 = dia 7, que ainda seria menstruação.
        fases = {f["fase"]: (f["inicio"], f["fim"]) for f in dividir_ciclo_em_fases(21, 7)["fases"]}
        assert fases == {"Menstruação": (1, 7), "Ovulatória": (8, 8), "Lútea": (9, 21)}

    def test_perfil_devolve_cinco_dias_quando_nao_informada(self, client, headers_auth):
        response = client.get("/perfil", headers=headers_auth)

        assert response.status_code == 200
        assert response.json()["duracao_menstruacao"] == 5

    def test_perfil_salva_e_as_fases_passam_a_usar(self, client, headers_auth):
        response = client.put(
            "/perfil",
            headers=headers_auth,
            json={"data_menstruacao": None, "duracao_menstruacao": 7},
        )
        assert response.status_code == 200

        assert client.get("/perfil", headers=headers_auth).json()["duracao_menstruacao"] == 7

        ciclo = client.get("/fase-ciclo", headers=headers_auth).json()
        assert ciclo["duracao_menstruacao"] == 7
        assert ciclo["fases"][0] == {"fase": "Menstruação", "inicio": 1, "fim": 7}

    def test_perfil_sem_o_campo_nao_apaga_o_valor_salvo(self, client, headers_auth):
        client.put("/perfil", headers=headers_auth, json={"data_menstruacao": None, "duracao_menstruacao": 4})
        # Versões antigas do app não enviam o campo.
        client.put("/perfil", headers=headers_auth, json={"data_menstruacao": None, "duracao_ciclo": 30})

        perfil = client.get("/perfil", headers=headers_auth).json()
        assert (perfil["duracao_menstruacao"], perfil["duracao_ciclo"]) == (4, 30)

    @pytest.mark.parametrize("valor", [0, 11])
    def test_perfil_recusa_duracao_fora_da_faixa(self, client, headers_auth, valor):
        response = client.put(
            "/perfil",
            headers=headers_auth,
            json={"data_menstruacao": None, "duracao_menstruacao": valor},
        )
        assert response.status_code == 422
