from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.sqlalchemy_models import Usuario
from app.services.auth_service import verificar_token

router = APIRouter(prefix="/pontuacao", tags=["Pontuação"])

CLASSES_LUNARES = (
    (0, "Lua Nova", "Início, constância e criação de novos hábitos."),
    (120, "Lua Crescente", "Evolução e força para continuar avançando."),
    (240, "Lua Cheia", "Consistência, energia e conquistas em expansão."),
    (360, "Lua Minguante", "Maturidade, equilíbrio e cuidado contínuo."),
)


def calcular_classe_lunar(pontos: int) -> dict:
    """Calcula a classe exclusivamente pela pontuação acumulada."""
    pontos = max(0, int(pontos or 0))
    indice = max(i for i, (limite, _, _) in enumerate(CLASSES_LUNARES) if pontos >= limite)
    limite_atual, classe, descricao = CLASSES_LUNARES[indice]
    proxima = CLASSES_LUNARES[indice + 1] if indice + 1 < len(CLASSES_LUNARES) else None

    return {
        "classe": classe,
        "descricao_classe": descricao,
        "pontuacao_inicial_classe": limite_atual,
        "proxima_classe": proxima[1] if proxima else None,
        "proxima_pontuacao": proxima[0] if proxima else None,
        "pontos_para_proxima": max(0, proxima[0] - pontos) if proxima else 0,
    }


@router.get("")
def get_pontuacao(
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token),
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    pontos = max(0, int(usuario.pontos_totais or 0))
    classe = calcular_classe_lunar(pontos)

    return {
        "pontos_mes": pontos,
        "pontos_totais": pontos,
        **classe,
        # Compatibilidade temporária com versões antigas do aplicativo.
        "dias_restantes": 0,
    }
