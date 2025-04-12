from fastapi import APIRouter, Depends, HTTPException, Request
from app.services.email_service import enviar_email
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.usuario_schemas import AtualizarPerfil, RedefinirSenhaRequest
from app.models.sqlalchemy_models import Usuario
from app.services.auth_service import processar_redefinicao_senha
from datetime import datetime, timedelta
import random



router = APIRouter(tags=["Usuário"])


@router.post("/redefinir-senha")
def redefinir_senha(request: RedefinirSenhaRequest, db: Session = Depends(get_db)):
    return processar_redefinicao_senha(request, db)


@router.post("/enviar-codigo")
async def enviar_codigo(email: dict, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(Usuario.email == email['email']).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Email não encontrado.")

    codigo = str(random.randint(100000, 999999))
    usuario.codigo_validacao = codigo
    usuario.validade_codigo = datetime.utcnow() + timedelta(minutes=15)  # ✅ expira em 15 minutos

    db.commit()

    # Em produção: enviar e-mail real
    print(f"📧 Código para {email['email']}: {codigo}")

    return {"mensagem": "Código enviado ao email informado."}