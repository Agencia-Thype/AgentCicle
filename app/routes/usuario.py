from fastapi import APIRouter, Depends, HTTPException
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

    # O registro no banco já foi removido; se o Firebase falhar, a conta local
    # não volta a existir - apenas registramos para limpeza posterior.
    try:
        excluir_usuario_firebase(email)
    except Exception as e:
        log_warning(
            f"Conta {email} removida do banco, mas não do Firebase", {"erro": str(e)}
        )

    log_info(f"Conta excluída a pedido da usuária", {"usuario_id": usuario_id, "registros": removidos})

    return {"mensagem": "Conta e dados excluídos permanentemente."}
