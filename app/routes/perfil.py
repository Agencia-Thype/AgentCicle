from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from app.schemas.usuario_schemas import AtualizarPerfil, PerfilUsuario, AtualizarPerfilRequest
from app.services.auth_service import verificar_token
from app.db.database import get_db
from app.models.sqlalchemy_models import Usuario, HistoricoPeso
import io
import matplotlib.pyplot as plt
from fastapi.responses import StreamingResponse
from app.utils.acesso import verificar_acesso

router = APIRouter(tags=["Perfil"])

@router.get("/perfil", response_model=AtualizarPerfil)
@verificar_acesso(recurso_premium=False, permite_trial=True)
def get_perfil(
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    print(f"📋 Acessando /perfil para email: {email}")
    try:
        usuario = db.query(Usuario).filter(Usuario.email == email).first()
        if not usuario:
            print(f"❌ Usuário não encontrado para email: {email}")
            raise HTTPException(status_code=404, detail="Usuária não encontrada")
        print(f"✅ Usuário encontrado: {usuario.nome} (ID: {usuario.id})")
    except Exception as e:
        print(f"❌ Erro ao buscar usuário: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar usuário: {str(e)}")

    # Calcular IMC
    imc = None
    if usuario.altura and usuario.peso_atual:
        imc = round(float(usuario.peso_atual) / float(usuario.altura) ** 2, 1)

    # Buscar histórico de peso (últimos 5 registros)
    historico = (
        db.query(HistoricoPeso)
        .filter(HistoricoPeso.user_id == usuario.id)
        .order_by(HistoricoPeso.data_registro.desc())
        .limit(5)
        .all()
    )

    historico_formatado = [
        {
            "peso": float(h.peso),
            "altura": float(h.altura) if h.altura else None,
            "imc": float(h.imc) if h.imc else None,
            "data": h.data_registro
        }
        for h in historico
    ]

    return PerfilUsuario(
        nome=usuario.nome,
        altura=float(usuario.altura) if usuario.altura else None,
        peso_atual=float(usuario.peso_atual) if usuario.peso_atual else None,
        objetivo=usuario.objetivo,
        data_menstruacao=usuario.data_menstruacao,
        duracao_ciclo=usuario.duracao_ciclo,
        imc=imc,
        historico_peso=historico_formatado
    )


@router.put("/perfil")
@verificar_acesso(recurso_premium=False, permite_trial=True)
async def atualizar_perfil(
    perfil: AtualizarPerfilRequest,
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    if perfil.altura is not None:
        usuario.altura = perfil.altura

    if perfil.peso_atual is not None:
        usuario.peso_atual = perfil.peso_atual
        usuario.data_peso_atual = date.today()
        
        imc = None
        if perfil.altura:
            imc = perfil.peso_atual / (perfil.altura ** 2)
            
        novo_historico = HistoricoPeso(
            user_id=usuario.id,
            peso=perfil.peso_atual,
            altura=perfil.altura,
            imc=imc,
            data_registro=date.today()
        )
        db.add(novo_historico)

    if perfil.objetivo is not None:
        usuario.objetivo = perfil.objetivo
      # Variáveis para retorno
    fase_atualizada = None
    
    if perfil.data_menstruacao is not None:
        # Verificar se a data mudou
        data_antiga = usuario.data_menstruacao
        
        if data_antiga != perfil.data_menstruacao:
            hoje = datetime.now()
            
            # Verificar se a usuária já concluiu algum treino hoje
            from app.services.treino_service import usuario_tem_treino_concluido_hoje
            
            if usuario_tem_treino_concluido_hoje(db, usuario.id):
                raise HTTPException(
                    status_code=400, 
                    detail="Não é possível alterar a data da menstruação após ter concluído treinos hoje. Por favor, tente novamente amanhã."
                )
            
            # Verificar as regras de negócio para atualização da data de menstruação
            if usuario.data_menstruacao and usuario.ultima_atualizacao_menstruacao:
                ultima_atualizacao = usuario.ultima_atualizacao_menstruacao
                dias_desde_ultima_atualizacao = (hoje - ultima_atualizacao).days
                dias_desde_registro = (hoje.date() - usuario.data_menstruacao).days
                
                # Regra 1: Janela de correção de 5 dias após o registro inicial
                if dias_desde_registro > 5:
                    # Regra 2: Uma nova edição só será permitida 28 dias após a última edição
                    if dias_desde_ultima_atualizacao < 28:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Não é possível editar a data da menstruação fora da janela de correção de 5 dias. "
                                   f"Uma nova edição será permitida após {28 - dias_desde_ultima_atualizacao} dias."
                        )
            
            # Atualizar a data e registrar o momento da atualização
            usuario.data_menstruacao = perfil.data_menstruacao
            usuario.ultima_atualizacao_menstruacao = hoje
            
            print(f"🔄 Data da menstruação atualizada: {data_antiga} -> {perfil.data_menstruacao}")
            
            # Calcular a nova fase para informar ao cliente
            from app.services.ciclo_service import calcular_fase_do_ciclo
            fase_atualizada = calcular_fase_do_ciclo(
                str(perfil.data_menstruacao), 
                perfil.duracao_ciclo or usuario.duracao_ciclo or 28
            )

    if perfil.duracao_ciclo is not None:
        usuario.duracao_ciclo = perfil.duracao_ciclo
        
    db.commit()
    
    # Se houve atualização da fase, informar no retorno
    if fase_atualizada:
        return {
            "mensagem": "Perfil atualizado com sucesso", 
            "fase_atualizada": True,
            "nova_fase": fase_atualizada["fase"],
            "mensagem_fase": fase_atualizada["mensagem"]
        }
    return {"mensagem": "Perfil atualizado com sucesso"}


@router.get("/perfil/grafico")
@verificar_acesso(recurso_premium=True, permite_trial=False)  # Considerando como recurso premium
async def grafico_historico_peso(
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    historico = db.query(HistoricoPeso).filter(HistoricoPeso.user_id == usuario.id).order_by(HistoricoPeso.data_registro).all()

    if not historico:
        raise HTTPException(status_code=404, detail="Sem histórico de peso encontrado.")

    datas = [h.data_registro for h in historico]
    pesos = [h.peso for h in historico]
    imcs = [h.imc for h in historico]

    plt.figure(figsize=(10, 5))
    plt.plot(datas, pesos, label="Peso (kg)", marker='o')
    plt.plot(datas, imcs, label="IMC", marker='x')
    plt.xlabel("Data")
    plt.ylabel("Valores")
    plt.title("Histórico de Peso e IMC")
    plt.legend()
    plt.grid(True)

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()

    return StreamingResponse(buf, media_type="image/png")


@router.post("/sincronizar-fase")
@verificar_acesso(recurso_premium=False, permite_trial=True)
async def sincronizar_fase_apos_atualizacao(
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    """
    Endpoint para sincronizar informações da fase após atualização da data da menstruação.
    Isso garante que a IA e os treinos usem a fase atualizada imediatamente.
    """
    from app.services.ciclo_service import calcular_fase_do_ciclo
    from app.services.treino_service import usuario_tem_treino_concluido_hoje
    
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")
    
    # Garantir que temos os dados mais atualizados
    db.refresh(usuario)
      # Verificar se a usuária já concluiu algum treino hoje
    if usuario_tem_treino_concluido_hoje(db, usuario.id):
        raise HTTPException(
            status_code=400, 
            detail="Não é possível sincronizar a fase após ter concluído treinos hoje. Por favor, tente novamente amanhã."
        )
    
    if not usuario.data_menstruacao:
        raise HTTPException(status_code=400, detail="Data da menstruação não cadastrada")
    
    # Verificar as regras de negócio para atualização da fase
    hoje = datetime.now()
    if usuario.ultima_atualizacao_menstruacao:
        ultima_atualizacao = usuario.ultima_atualizacao_menstruacao
        dias_desde_ultima_atualizacao = (hoje - ultima_atualizacao).days
        dias_desde_registro = (hoje.date() - usuario.data_menstruacao).days
        
        # Aplicar as mesmas regras de negócio do endpoint de atualização
        if dias_desde_registro > 5 and dias_desde_ultima_atualizacao < 28:
            raise HTTPException(
                status_code=400,
                detail=f"Não é possível sincronizar a fase fora da janela de correção de 5 dias. "
                       f"Uma nova sincronização será permitida após {28 - dias_desde_ultima_atualizacao} dias."
            )
    
    # Calcular a fase atual com a data atualizada
    fase_info = calcular_fase_do_ciclo(str(usuario.data_menstruacao), usuario.duracao_ciclo or 28)
    
    return {
        "mensagem": "Fase sincronizada com sucesso",
        "fase_atual": fase_info["fase"],
        "dias_desde_menstruacao": fase_info["dias_desde_menstruacao"],
        "mensagem_fase": fase_info["mensagem"],
        "data_menstruacao": usuario.data_menstruacao,
        "duracao_ciclo": usuario.duracao_ciclo or 28
    }
