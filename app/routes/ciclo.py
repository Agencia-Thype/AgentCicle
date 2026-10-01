from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta, timezone
from app.db.database import get_db
from app.services.auth_service import verificar_token
from app.models.sqlalchemy_models import Usuario
from app.models.sqlalchemy_models import Usuario, DiarioCiclo
from app.schemas.ciclo_schema import RegistroMenstruacao
from app.services.ciclo_service import calcular_fase_do_ciclo, registrar_nova_menstruacao
from fastapi import Body

router = APIRouter(tags=["Ciclo"])

FASES_CICLO = [
    ("Menstruação", 0, "Fase reflexiva 🌑"),
    ("Folicular", 0, "Fase dinâmica 🌒"),
    ("Ovulatória", 0, "Fase expansiva 🌕"),
    ("Lútea", 0, "Fase criativa 🌘")
]

@router.post("/registrar-menstruacao")
def registrar_menstruacao(
    registro: RegistroMenstruacao,
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    return registrar_nova_menstruacao(db, email, registro.data_inicio)

@router.put("/editar-menstruacao")
def editar_data_menstruacao(
    data_nova: date = Body(..., embed=True),
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    # Atualiza no perfil
    usuario.data_menstruacao = data_nova
    
    # Verifica se já existe registro para esta data
    registro_existente = db.query(DiarioCiclo).filter(
        DiarioCiclo.user_id == usuario.id,
        DiarioCiclo.data == data_nova
    ).first()

    if registro_existente:
        registro_existente.fase = "Menstruação"
    else:
        novo_registro = DiarioCiclo(
            user_id=usuario.id,
            data=data_nova,
            fase="Menstruação",
            created_at=datetime.now(timezone.utc)
        )
        db.add(novo_registro)

    db.commit()

    # Recalcular a fase atual
    fase_atual = calcular_fase_do_ciclo(data_nova, usuario.duracao_ciclo, duracao_menstruacao=usuario.duracao_menstruacao)

    return {
        "mensagem": "Registro de menstruação atualizado com sucesso",
        "data_registrada": data_nova,
        "fase_atual": fase_atual
    }


@router.get("/fase-por-data")
def fase_por_data(
    data: date,
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()

    if not usuario or not usuario.data_menstruacao or not usuario.duracao_ciclo:
        raise HTTPException(status_code=400, detail="Usuária sem dados completos do ciclo")

    info = calcular_fase_do_ciclo(
        usuario.data_menstruacao, usuario.duracao_ciclo, data, duracao_menstruacao=usuario.duracao_menstruacao
    )
    return {
        "data": data,
        "fase": info["fase"],
        "mensagem": info["mensagem"],
        "dias_desde_menstruacao": info["dias_desde_menstruacao"],
        "inicio_ciclo": usuario.data_menstruacao,
    }

@router.get("/fase-ciclo")
def detectar_fase_ciclo(
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario or not usuario.data_menstruacao or not usuario.duracao_ciclo:
        raise HTTPException(status_code=400, detail="Usuária sem dados completos do ciclo")

    info = calcular_fase_do_ciclo(
        usuario.data_menstruacao, usuario.duracao_ciclo, duracao_menstruacao=usuario.duracao_menstruacao
    )
    return {
        "fase": info["fase"],
        "mensagem": info["mensagem"],
        "dias_desde_menstruacao": info["dias_desde_menstruacao"],
        "duracao_ciclo": info["duracao_ciclo"],
        "duracao_menstruacao": info["duracao_menstruacao"],
        "inicio_ciclo": usuario.data_menstruacao,
        # O app pinta o calendário com estes limites, sem refazer a conta.
        "fases": info["fases"],
        "dia_ovulacao": info["dia_ovulacao"],
        "janela_fertil": info["janela_fertil"],
    }
