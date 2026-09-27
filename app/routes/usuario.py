import time

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.sqlalchemy_models import Usuario
from app.services.auth_service import verificar_token, excluir_usuario_firebase
from app.utils.logging import log_info, log_warning

router = APIRouter(tags=["Usuário"])

# Tabelas que referenciam usuarios.id. Nem todas têm ON DELETE CASCADE no banco,
# então a remoção é feita explicitamente aqui, na ordem filho -> pai.
TABELAS_DEPENDENTES = (
    # doses_rotina referencia itens_rotina: tem de sair antes dos itens.
    ("doses_rotina", "usuario_id"),
    ("itens_rotina", "usuario_id"),
    ("agua_registros", "usuario_id"),
    ("config_hidratacao", "usuario_id"),
    ("compras_loja", "usuario_id"),
    ("ia_historico_mensagens", "user_id"),
    ("conversas_ia", "user_id"),
    ("diario_ciclo", "user_id"),
    ("historico_peso", "user_id"),
    ("progresso_kegel", "usuario_id"),
    ("kegel_diario", "usuario_id"),
    ("treino_realizado", "usuario_id"),
)


@router.delete("/usuario/me")
def excluir_minha_conta(
    tarefas: BackgroundTasks,
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token),
):
    """
    Exclui permanentemente a conta da usuária autenticada e todos os seus dados.

    Requisito obrigatório da App Store (5.1.1(v)) e do Google Play para
    aplicativos que permitem criação de conta. A usuária só pode excluir a
    própria conta - o alvo vem do token, nunca da URL.
    """
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    usuario_id = usuario.id
    removidos = {}
    inicio = time.perf_counter()

    try:
        for tabela, coluna in TABELAS_DEPENDENTES:
            resultado = db.execute(
                text(f"DELETE FROM {tabela} WHERE {coluna} = :uid"),
                {"uid": usuario_id},
            )
            removidos[tabela] = resultado.rowcount

        db.delete(usuario)
        db.commit()
    except Exception as e:
        db.rollback()
        log_warning(f"Falha ao excluir conta de {email}", {"erro": str(e)})
        raise HTTPException(
            status_code=500, detail="Não foi possível excluir a conta. Tente novamente."
        )

    tempo_banco_ms = round((time.perf_counter() - inicio) * 1000)

    # O registro no banco já foi removido; se o Firebase falhar, a conta local
    # não volta a existir. Uma nova tentativa roda depois da resposta, para o
    # app não ficar esperando o Google.
    inicio_firebase = time.perf_counter()
    try:
        excluir_usuario_firebase(email)
    except Exception as e:
        log_warning(
            f"Conta {email} removida do banco, mas não do Firebase; tentando de novo",
            {"erro": str(e)},
        )
        tarefas.add_task(_tentar_excluir_do_firebase_de_novo, email)

    log_info(
        "Conta excluída a pedido da usuária",
        {
            "usuario_id": usuario_id,
            "registros": removidos,
            "tempo_banco_ms": tempo_banco_ms,
            "tempo_firebase_ms": round((time.perf_counter() - inicio_firebase) * 1000),
        },
    )

    return {"mensagem": "Conta e dados excluídos permanentemente."}


def _tentar_excluir_do_firebase_de_novo(email: str) -> None:
    try:
        excluir_usuario_firebase(email)
        log_info(f"Conta {email} removida do Firebase na segunda tentativa")
    except Exception as e:
        log_warning(
            f"Conta {email} continua no Firebase; remover manualmente", {"erro": str(e)}
        )
