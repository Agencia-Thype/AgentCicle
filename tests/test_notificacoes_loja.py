"""
Testes dos webhooks das lojas.

O ponto central: o corpo da notificação não decide nada. Vale o que a loja
responde quando a compra é reconsultada - por isso os testes trocam apenas o
validador, e não o conteúdo da notificação.
"""
import json
from base64 import b64encode, urlsafe_b64encode
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.sqlalchemy_models import CompraLoja, Usuario
from app.services.pagamento_service import CompraValidada

TOKEN_APPLE = "1000000000000777"
TOKEN_GOOGLE = "token-google-abc"


def _jws(payload: dict) -> str:
    corpo = urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"cabecalho.{corpo}.assinatura"


def corpo_apple(tipo: str = "DID_RENEW", transacao: str = TOKEN_APPLE) -> dict:
    return {
        "signedPayload": _jws({
            "notificationType": tipo,
            "data": {"signedTransactionInfo": _jws({"transactionId": transacao})},
        })
    }


def corpo_google(tipo: int = 2, token: str = TOKEN_GOOGLE) -> dict:
    conteudo = {
        "subscriptionNotification": {"notificationType": tipo, "purchaseToken": token},
    }
    return {"message": {"data": b64encode(json.dumps(conteudo).encode()).decode()}}


def compra_valida(dias: int = 30) -> CompraValidada:
    return CompraValidada(
        plataforma="android",
        id_transacao="GPA.7777",
        product_id="ciclica_premium_mensal",
        duracao_meses=1,
        expira_em=datetime.now(timezone.utc) + timedelta(days=dias),
    )


@pytest.fixture
def assinante(db: Session, usuario_teste: Usuario) -> Usuario:
    """Usuária com assinatura ativa e a compra registrada pelas duas lojas."""
    usuario_teste.assinatura_ativa = 1
    usuario_teste.data_inicio_assinatura = datetime.now() - timedelta(days=30)
    usuario_teste.data_fim_assinatura = datetime.now() + timedelta(days=1)

    db.add(CompraLoja(
        usuario_id=usuario_teste.id,
        plataforma="android",
        id_transacao="GPA.7777",
        token_compra=TOKEN_GOOGLE,
        product_id="ciclica_premium_mensal",
        duracao_meses=1,
        created_at=datetime.now(),
    ))
    db.add(CompraLoja(
        usuario_id=usuario_teste.id,
        plataforma="ios",
        id_transacao=TOKEN_APPLE,
        token_compra=TOKEN_APPLE,
        product_id="ciclica_premium_mensal",
        duracao_meses=1,
        created_at=datetime.now(),
    ))
    db.commit()
    db.refresh(usuario_teste)
    return usuario_teste


class TestRenovacao:
    """Loja confirma a compra: a assinatura segue valendo"""

    def test_google_renova_e_estende_a_data(
        self, client: TestClient, db: Session, assinante: Usuario, monkeypatch
    ):
        monkeypatch.setenv("COBRANCA_ATIVA", "true")
        monkeypatch.setattr(
            "app.services.notificacoes_loja_service.validar_compra",
            lambda *a, **k: compra_valida(dias=30),
        )

        response = client.post("/notificacoes-loja/google", json=corpo_google())

        assert response.status_code == 200
        assert response.json()["resultado"] == "renovada"

        db.refresh(assinante)
        assert assinante.assinatura_ativa == 1
        assert assinante.data_fim_assinatura > datetime.now() + timedelta(days=25)

    def test_apple_renova(
        self, client: TestClient, db: Session, assinante: Usuario, monkeypatch
    ):
        monkeypatch.setenv("COBRANCA_ATIVA", "true")
        monkeypatch.setattr(
            "app.services.notificacoes_loja_service.validar_compra",
            lambda *a, **k: compra_valida(dias=30),
        )

        response = client.post("/notificacoes-loja/apple", json=corpo_apple())

        assert response.status_code == 200
        assert response.json()["resultado"] == "renovada"
        assert response.json()["notificacao"] == "DID_RENEW"

        db.refresh(assinante)
        assert assinante.assinatura_ativa == 1


class TestPerdaDeAcesso:
    """Cancelamento, reembolso ou vencimento derrubam o premium"""

    def _loja_recusa(self, monkeypatch):
        def recusar(*a, **k):
            raise HTTPException(status_code=400, detail="Compra inválida: assinatura expirada")

        monkeypatch.setattr("app.services.notificacoes_loja_service.validar_compra", recusar)

    def test_google_cancela(
        self, client: TestClient, db: Session, assinante: Usuario, monkeypatch
    ):
        monkeypatch.setenv("COBRANCA_ATIVA", "true")
        self._loja_recusa(monkeypatch)

        response = client.post("/notificacoes-loja/google", json=corpo_google(tipo=3))

        assert response.status_code == 200
        assert response.json()["resultado"] == "cancelada"

        db.refresh(assinante)
        assert assinante.assinatura_ativa == 0

    def test_apple_reembolso_cancela(
        self, client: TestClient, db: Session, assinante: Usuario, monkeypatch
    ):
        monkeypatch.setenv("COBRANCA_ATIVA", "true")
        self._loja_recusa(monkeypatch)

        response = client.post("/notificacoes-loja/apple", json=corpo_apple(tipo="REFUND"))

        assert response.status_code == 200
        db.refresh(assinante)
        assert assinante.assinatura_ativa == 0


class TestNotificacoesQueNaoMudamNada:
    """Ruído não pode derrubar assinatura de quem paga"""

    def test_compra_desconhecida_e_ignorada(
        self, client: TestClient, db: Session, assinante: Usuario, monkeypatch
    ):
        monkeypatch.setenv("COBRANCA_ATIVA", "true")

        response = client.post(
            "/notificacoes-loja/google", json=corpo_google(token="token-de-outro-app")
        )

        assert response.status_code == 200
        assert response.json()["resultado"] == "ignorado"

        db.refresh(assinante)
        assert assinante.assinatura_ativa == 1

    def test_notificacao_de_teste_do_console(self, client: TestClient, monkeypatch):
        monkeypatch.setenv("COBRANCA_ATIVA", "true")
        conteudo = {"testNotification": {"version": "1.0"}}
        corpo = {"message": {"data": b64encode(json.dumps(conteudo).encode()).decode()}}

        response = client.post("/notificacoes-loja/google", json=corpo)

        assert response.status_code == 200
        assert response.json()["resultado"] == "ignorado"

    def test_loja_fora_do_ar_nao_cancela(
        self, client: TestClient, db: Session, assinante: Usuario, monkeypatch
    ):
        """Erro da loja tem de virar falha, para a notificação ser reenviada."""
        monkeypatch.setenv("COBRANCA_ATIVA", "true")

        def indisponivel(*a, **k):
            raise HTTPException(status_code=502, detail="Google Play indisponível")

        monkeypatch.setattr(
            "app.services.notificacoes_loja_service.validar_compra", indisponivel
        )

        response = client.post("/notificacoes-loja/google", json=corpo_google())

        assert response.status_code == 502
        db.refresh(assinante)
        assert assinante.assinatura_ativa == 1

    def test_corpo_sem_dados(self, client: TestClient, monkeypatch):
        monkeypatch.setenv("COBRANCA_ATIVA", "true")

        assert client.post("/notificacoes-loja/google", json={}).status_code == 400
        assert client.post("/notificacoes-loja/apple", json={}).status_code == 400


class TestProtecaoDaRota:
    """A rota é pública, mas não é de qualquer um"""

    def test_fechada_no_modo_gratuito(self, client: TestClient, monkeypatch):
        monkeypatch.setenv("COBRANCA_ATIVA", "false")

        response = client.post("/notificacoes-loja/google", json=corpo_google())

        assert response.status_code == 404

    def test_segredo_errado_recusado(self, client: TestClient, monkeypatch):
        monkeypatch.setenv("COBRANCA_ATIVA", "true")
        monkeypatch.setenv("NOTIFICACOES_LOJA_TOKEN", "segredo-certo")

        response = client.post(
            "/notificacoes-loja/google?token=segredo-errado", json=corpo_google()
        )

        assert response.status_code == 401

    def test_segredo_certo_passa(
        self, client: TestClient, db: Session, assinante: Usuario, monkeypatch
    ):
        monkeypatch.setenv("COBRANCA_ATIVA", "true")
        monkeypatch.setenv("NOTIFICACOES_LOJA_TOKEN", "segredo-certo")
        monkeypatch.setattr(
            "app.services.notificacoes_loja_service.validar_compra",
            lambda *a, **k: compra_valida(),
        )

        response = client.post(
            "/notificacoes-loja/google?token=segredo-certo", json=corpo_google()
        )

        assert response.status_code == 200

    def test_segredo_tambem_pelo_cabecalho(
        self, client: TestClient, db: Session, assinante: Usuario, monkeypatch
    ):
        monkeypatch.setenv("COBRANCA_ATIVA", "true")
        monkeypatch.setenv("NOTIFICACOES_LOJA_TOKEN", "segredo-certo")
        monkeypatch.setattr(
            "app.services.notificacoes_loja_service.validar_compra",
            lambda *a, **k: compra_valida(),
        )

        response = client.post(
            "/notificacoes-loja/google",
            json=corpo_google(),
            headers={"X-Notificacao-Token": "segredo-certo"},
        )

        assert response.status_code == 200
