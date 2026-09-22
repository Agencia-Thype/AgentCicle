from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.rotina_models import AguaRequest, ConfigHidratacaoRequest, DoseRequest, ItemRotinaRequest
from app.models.sqlalchemy_models import AguaRegistro, ItemRotina, Usuario
from app.services import rotina_service
from app.services.auth_service import verificar_token

router = APIRouter(prefix="/rotina", tags=["Rotina"])


def _usuaria(db: Session, email: str) -> Usuario:
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")
    return usuario


def _item_da_usuaria(db: Session, usuario: Usuario, item_id: int) -> ItemRotina:
    item = db.query(ItemRotina).filter(
        ItemRotina.id == item_id,
        ItemRotina.usuario_id == usuario.id,
        ItemRotina.ativo == 1,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    return item


@router.get("/hoje")
def rotina_de_hoje(db: Session = Depends(get_db), email: str = Depends(verificar_token)):
    """Agenda do dia (doses e status), próxima dose e a hidratação de hoje."""
    return rotina_service.resumo_do_dia(db, _usuaria(db, email))


# --------------------------------------------------------------------- itens

@router.get("/itens")
def listar_itens(db: Session = Depends(get_db), email: str = Depends(verificar_token)):
    usuario = _usuaria(db, email)
    return {"itens": [rotina_service.serializar_item(item) for item in rotina_service.itens_da_usuaria(db, usuario.id)]}


@router.get("/itens/{item_id}")
def obter_item(item_id: int, db: Session = Depends(get_db), email: str = Depends(verificar_token)):
    return rotina_service.serializar_item(_item_da_usuaria(db, _usuaria(db, email), item_id))


@router.post("/itens", status_code=201)
def criar_item(dados: ItemRotinaRequest, db: Session = Depends(get_db), email: str = Depends(verificar_token)):
    item = rotina_service.criar_item(db, _usuaria(db, email), dados)
    return rotina_service.serializar_item(item)


@router.put("/itens/{item_id}")
def atualizar_item(
    item_id: int,
    dados: ItemRotinaRequest,
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token),
):
    item = _item_da_usuaria(db, _usuaria(db, email), item_id)
    return rotina_service.serializar_item(rotina_service.atualizar_item(db, item, dados))


@router.delete("/itens/{item_id}")
def excluir_item(item_id: int, db: Session = Depends(get_db), email: str = Depends(verificar_token)):
    item = _item_da_usuaria(db, _usuaria(db, email), item_id)
    rotina_service.excluir_item(db, item)
    return {"mensagem": "Item removido da rotina"}


# --------------------------------------------------------------------- doses

@router.post("/doses")
def marcar_dose(dados: DoseRequest, db: Session = Depends(get_db), email: str = Depends(verificar_token)):
    usuario = _usuaria(db, email)
    item = _item_da_usuaria(db, usuario, dados.item_id)
    dia = dados.data or rotina_service.hoje_brasilia()
    try:
        registrada = rotina_service.registrar_dose(db, usuario, item, dia, dados.horario)
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro))
    return {"registrada": registrada, "resumo": rotina_service.resumo_do_dia(db, usuario, dia)}


@router.post("/doses/desfazer")
def desmarcar_dose(dados: DoseRequest, db: Session = Depends(get_db), email: str = Depends(verificar_token)):
    usuario = _usuaria(db, email)
    item = _item_da_usuaria(db, usuario, dados.item_id)
    dia = dados.data or rotina_service.hoje_brasilia()
    desfeita = rotina_service.desfazer_dose(db, usuario, item, dia, dados.horario)
    return {"desfeita": desfeita, "resumo": rotina_service.resumo_do_dia(db, usuario, dia)}


# ---------------------------------------------------------------------- água

@router.get("/agua")
def agua(
    data: Optional[date] = Query(None, description="Data no formato YYYY-MM-DD (padrão: hoje)"),
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token),
):
    return rotina_service.agua_do_dia(db, _usuaria(db, email), data)


@router.post("/agua", status_code=201)
def registrar_agua(dados: AguaRequest, db: Session = Depends(get_db), email: str = Depends(verificar_token)):
    usuario = _usuaria(db, email)
    try:
        registro = rotina_service.registrar_agua(db, usuario, dados.ml, dados.data)
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro))
    return rotina_service.agua_do_dia(db, usuario, registro.data)


@router.delete("/agua/{registro_id}")
def desfazer_agua(registro_id: int, db: Session = Depends(get_db), email: str = Depends(verificar_token)):
    usuario = _usuaria(db, email)
    registro = db.query(AguaRegistro).filter(
        AguaRegistro.id == registro_id, AguaRegistro.usuario_id == usuario.id
    ).first()
    if not registro:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    dia = registro.data
    db.delete(registro)
    db.commit()
    return rotina_service.agua_do_dia(db, usuario, dia)


@router.put("/agua/config")
def configurar_agua(
    dados: ConfigHidratacaoRequest,
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token),
):
    usuario = _usuaria(db, email)
    rotina_service.salvar_config_hidratacao(db, usuario, dados)
    return rotina_service.agua_do_dia(db, usuario)


# ----------------------------------------------------------------- histórico

@router.get("/historico")
def historico(
    dias: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token),
):
    return rotina_service.historico(db, _usuaria(db, email), dias)
