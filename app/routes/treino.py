from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, List
from datetime import date, datetime, timedelta

from app.db.database import get_db
from app.services.auth_service import verificar_token
from app.models.sqlalchemy_models import Usuario, TreinoRealizado
from app.services.treino_service import obter_treino_por_fase
from app.services.ciclo_service import calcular_fase_do_ciclo
from app.models.treino_models import ConcluirTreinoRequest
from sqlalchemy import func
from app.utils.acesso import verificar_acesso

router = APIRouter(prefix="/treino-dia", tags=["Treino"])

@router.get("")
@verificar_acesso(recurso_premium=False, permite_trial=True)
async def treino_do_dia(
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    return obter_treino_por_fase(email=email, db=db)


# @router.post("/registrar")
# def registrar_treino(
#     db: Session = Depends(get_db),
#     email: str = Depends(verificar_token)
# ):
#     usuario = db.query(Usuario).filter(Usuario.email == email).first()
#     if not usuario:
#         raise HTTPException(status_code=404, detail="Usuária não encontrada")

#     fase = calcular_fase(str(usuario.data_menstruacao))

#     treinos_feitos = (
#         db.query(TreinoRealizado)
#         .filter(TreinoRealizado.usuario_id == usuario.id)
#         .filter(TreinoRealizado.fase == fase)
#         .order_by(TreinoRealizado.data.desc())
#         .all()
#     )

#     sequencia = ["A", "B", "C", "D", "E"]
#     if not treinos_feitos:
#         tipo_treino = "A"
#     else:
#         ultimo = treinos_feitos[0].treino
#         idx = sequencia.index(ultimo)
#         tipo_treino = sequencia[(idx + 1) % len(sequencia)]

#     treino_realizado = TreinoRealizado(
#         usuario_id=usuario.id,
#         fase=fase,
#         treino=tipo_treino,
#         data=date.today()
#     )
#     db.add(treino_realizado)
#     db.commit()

#     return {"mensagem": f"Treino {tipo_treino} registrado com sucesso para a fase {fase}!"}

@router.post("/concluir", status_code=200)
@verificar_acesso(recurso_premium=False, permite_trial=True)
async def concluir_treino(
    dados: ConcluirTreinoRequest,
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    # Verificar status do usuário (assinatura/trial)
    from app.services.assinatura_service import verificar_status_usuario
    status_usuario = verificar_status_usuario(db, usuario.id)
    
    # Usar o valor de temAcesso como fallback se podePontuar não existir
    pode_pontuar = status_usuario.get("podePontuar", status_usuario.get("temAcesso", False))
    
    # Se não puder pontuar, mostramos apenas um aviso por enquanto
    if not pode_pontuar:
        print(f"⚠️ Usuário {email} tentou registrar pontos sem trial/assinatura ativa")
        # Quando ativar os bloqueios, comentar a linha abaixo
        pode_pontuar = True
        # E descomentar esta linha:
        # return {"erro": "Seu período de avaliação expirou. Assine para continuar registrando treinos e ganhando pontos."}

    fase_info = calcular_fase_do_ciclo(str(usuario.data_menstruacao), usuario.duracao_ciclo or 28)
    fase = fase_info["fase"]
    percentual = dados.percentual
    
    # Garantir que o percentual está entre 0 e 100
    if percentual < 0:
        percentual = 0
    elif percentual > 100:
        percentual = 100
        
    print(f"✅ Percentual recebido e validado: {percentual}% (usuário: {usuario.email}, fase: {fase}, treino: {dados.tipo_treino})")

    # Iniciar transação explícita para garantir atomicidade
    db.begin(subtransactions=True)
    
    treino_existente = db.query(TreinoRealizado).filter_by(
        usuario_id=usuario.id,
        data=date.today(),
        fase=fase,
        treino=dados.tipo_treino
    ).first()

    def calcular_pontos(p):
        if p == 0:
            return 0
        elif p < 25:
            return 3
        elif p < 50:
            return 5
        elif p < 75:
            return 10
        elif p < 100:
            return 15
        else:
            return 20

    if treino_existente:
        percentual_antigo = float(treino_existente.percentual_concluido or 0)
        print(f"📝 Treino existente encontrado (id={treino_existente.id}, data={treino_existente.data}): percentual_atual={percentual_antigo}%, novo_percentual={percentual}%")
        
        # Verificar se o percentual é diferente, não apenas maior
        if percentual != percentual_antigo:
            # Se o percentual for maior, atualizamos os pontos
            if percentual > percentual_antigo:
                pontos_antigos = treino_existente.pontos or 0
                novos_pontos = calcular_pontos(percentual)
                
                print(f"🔄 Percentual aumentou: {percentual_antigo}% → {percentual}% | Pontos: {pontos_antigos} → {novos_pontos}")

                if novos_pontos > pontos_antigos:
                    # Ganha apenas a diferença
                    ganho_real = novos_pontos - pontos_antigos
                    usuario.pontos_totais = (usuario.pontos_totais or 0) + ganho_real
                    treino_existente.pontos = novos_pontos
                    print(f"💰 Ganho real de pontos: +{ganho_real} | Total do usuário: {usuario.pontos_totais}")
            else:
                # Se for menor, apenas atualizamos o percentual sem alterar os pontos
                print(f"⚠️ Percentual diminuiu: {percentual_antigo}% → {percentual}% | Pontos mantidos: {treino_existente.pontos}")
            
            # Atualizamos o percentual em ambos os casos
            treino_existente.percentual_concluido = percentual
            
            try:
                db.commit()
                db.refresh(treino_existente)
                print(f"✅ TREINO ATUALIZADO NO BANCO: ID={treino_existente.id}, percentual={treino_existente.percentual_concluido}%, pontos={treino_existente.pontos}")
            except Exception as e:
                db.rollback()
                print(f"❌ ERRO AO ATUALIZAR TREINO: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Erro ao salvar treino: {str(e)}")
        else:
            print(f"ℹ️ Percentual igual ao já registrado: {percentual}% | Nenhuma alteração necessária")
            
            # Calcular o progresso semanal após atualizar o treino
            hoje = date.today()
            inicio_semana = hoje - timedelta(days=hoje.weekday())
            fim_semana = inicio_semana + timedelta(days=6)
            
            # Verificar os treinos da semana para obter o progresso atualizado
            treinos_semana = db.query(TreinoRealizado).filter(
                TreinoRealizado.usuario_id == usuario.id,
                TreinoRealizado.data >= inicio_semana,
                TreinoRealizado.data <= fim_semana,
            ).all()
            
            # Calcular o progresso da semana
            progresso_semana = calcular_progresso_semana(treinos_semana, usuario.data_menstruacao, inicio_semana, fim_semana)

            return {
                "mensagem": f"Treino atualizado para {percentual}% de conclusão.",
                "ja_salvo": True,
                "percentual": percentual,
                "pontos": treino_existente.pontos,
                "pontos_totais": usuario.pontos_totais,
                "progresso_semana": progresso_semana,
                "redirecionar_para": "/home",  # Instrução para o frontend redirecionar para a home
                "atualizar_pontuacao": True  # Instrução para o frontend atualizar a pontuação
            }

        # Se percentual for igual ou menor, não muda nada
        # Mas ainda retornamos informações para o frontend atualizar a UI
        hoje = date.today()
        inicio_semana = hoje - timedelta(days=hoje.weekday())
        fim_semana = inicio_semana + timedelta(days=6)
        
        # Verificar os treinos da semana para obter o progresso atualizado
        treinos_semana = db.query(TreinoRealizado).filter(
            TreinoRealizado.usuario_id == usuario.id,
            TreinoRealizado.data >= inicio_semana,
            TreinoRealizado.data <= fim_semana,
        ).all()
        
        # Calcular o progresso da semana
        progresso_semana = calcular_progresso_semana(treinos_semana, usuario.data_menstruacao, inicio_semana, fim_semana)
        
        return {
            "mensagem": f"Você já concluiu este treino hoje com {percentual_antigo}%. Nenhuma pontuação nova aplicada.",
            "ja_salvo": True,
            "percentual": percentual_antigo,
            "pontos": treino_existente.pontos,
            "pontos_totais": usuario.pontos_totais,
            "progresso_semana": progresso_semana,
            "redirecionar_para": "/home",  # Instrução para o frontend redirecionar para a home
            "atualizar_pontuacao": False  # Não precisa atualizar a pontuação pois não mudou
        }

    # 🆕 Se não existir, cria um novo registro
    try:
        novos_pontos = calcular_pontos(percentual)
        print(f"🆕 Criando novo registro de treino: tipo={dados.tipo_treino}, fase={fase}, percentual={percentual}%, pontos={novos_pontos}")
        
        novo_treino = TreinoRealizado(
            usuario_id=usuario.id,
            data=date.today(),
            fase=fase,
            treino=dados.tipo_treino,
            percentual_concluido=percentual,
            pontos=novos_pontos
        )
        
        db.add(novo_treino)
        usuario.pontos_totais = (usuario.pontos_totais or 0) + novos_pontos
        
        db.commit()
        db.refresh(novo_treino)
        
        print(f"✅ Novo treino criado com sucesso: ID={novo_treino.id}, percentual={novo_treino.percentual_concluido}%, pontos={novo_treino.pontos}")
    except Exception as e:
        db.rollback()
        print(f"❌ ERRO AO CRIAR NOVO TREINO: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao salvar treino: {str(e)}")

    # Calcular o progresso semanal após salvar o treino
    hoje = date.today()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)
    
    # Verificar os treinos da semana para obter o progresso atualizado
    treinos_semana = db.query(TreinoRealizado).filter(
        TreinoRealizado.usuario_id == usuario.id,
        TreinoRealizado.data >= inicio_semana,
        TreinoRealizado.data <= fim_semana,
    ).all()
    
    # Calcular o progresso da semana
    progresso_semana = calcular_progresso_semana(treinos_semana, usuario.data_menstruacao, inicio_semana, fim_semana)
    
    # Retornar resposta enriquecida com informações para o frontend
    return {
        "mensagem": f"Treino salvo com {percentual}% e {novos_pontos} ponto(s) conquistados.",
        "ja_salvo": False,
        "percentual": percentual,
        "pontos": novos_pontos,
        "pontos_totais": usuario.pontos_totais,
        "progresso_semana": progresso_semana,
        "redirecionar_para": "/home",  # Instrução para o frontend redirecionar para a home
        "atualizar_pontuacao": True  # Instrução para o frontend atualizar a pontuação
    }


def calcular_progresso_semana(treinos, data_menstruacao, data_inicio, data_fim):
    """
    Calcula o progresso semanal baseado nos treinos realizados.
    
    Args:
        treinos: Lista de treinos realizados
        data_menstruacao: Data de menstruação do usuário
        data_inicio: Data de início da semana
        data_fim: Data de fim da semana
        
    Returns:
        float: Porcentagem média de progresso na semana
    """
    treinos_por_data = {}
    
    for t in treinos:
        if isinstance(t.data, datetime):
            dia = t.data.date()
        else:
            dia = t.data

        valor = float(t.percentual_concluido or 0)
        if dia not in treinos_por_data or valor > treinos_por_data[dia]:
            treinos_por_data[dia] = valor
            
    soma = 0
    dias_com_treino_esperado = 0
    
    dias_da_semana = (data_fim - data_inicio).days + 1
    for i in range(dias_da_semana):
        dia = data_inicio + timedelta(days=i)
        fase = fase_do_dia(data_menstruacao, dia)
        
        if fase in ["Menstruação", "Folicular", "Ovulatória", "Lútea"]:
            progresso = treinos_por_data.get(dia, 0)
            dias_com_treino_esperado += 1
            soma += progresso
            
    if dias_com_treino_esperado == 0:
        return 0
        
    media = soma / dias_com_treino_esperado
    return round(media, 1)


FASES = [
    ("Menstruação", 0, 5),
    ("Folicular", 6, 12),
    ("Ovulatória", 13, 16),
    ("Lútea", 17, 28),
]

def fase_do_dia(data_menstruacao: date, dia: date) -> str:
    dias_ciclo = (dia - data_menstruacao).days % 28
    for nome, ini, fim in FASES:
        if ini <= dias_ciclo <= fim:
            return nome
    return "Desconhecida"

@router.get("/marcados-hoje")
def progresso_treino_hoje(
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")

    fase_info = calcular_fase_do_ciclo(str(usuario.data_menstruacao), usuario.duracao_ciclo or 28)
    fase = fase_info["fase"]
    
    # Buscar todos os treinos do dia atual para esta fase
    hoje = date.today()
    treinos_hoje = db.query(TreinoRealizado).filter(
        TreinoRealizado.usuario_id == usuario.id,
        TreinoRealizado.data == hoje,
        TreinoRealizado.fase == fase
    ).order_by(TreinoRealizado.id.desc()).all()
    
    # Log para verificação e diagnóstico
    print(f"🔍 Treinos registrados hoje ({hoje}) para usuário {usuario.id} na fase {fase}: {len(treinos_hoje)}")
    
    if not treinos_hoje:
        print("ℹ️ Nenhum treino registrado hoje")
        return {"percentual": 0, "ja_salvo": False}
    
    # Pegar o treino com maior percentual (mais relevante)
    treino = max(treinos_hoje, key=lambda t: float(t.percentual_concluido or 0))
    
    print(f"✅ Treino encontrado: ID={treino.id}, tipo={treino.treino}, percentual={treino.percentual_concluido}%, pontos={treino.pontos}")
    
    # Se houver múltiplos treinos no mesmo dia, registramos isso para diagnóstico
    if len(treinos_hoje) > 1:
        print(f"⚠️ Múltiplos treinos encontrados para hoje ({len(treinos_hoje)}): {[t.id for t in treinos_hoje]}")
        tipos_treino = set(t.treino for t in treinos_hoje)
        print(f"  - Tipos de treino registrados: {tipos_treino}")
    
    return {
        "percentual": float(treino.percentual_concluido or 0),
        "ja_salvo": True,
        "tipo_treino": treino.treino,
        "pontos": treino.pontos or 0,
        "id": treino.id,  # Adicionando ID para facilitar diagnóstico no frontend
        "total_registros_hoje": len(treinos_hoje)  # Informação adicional para diagnóstico
    }



@router.get("/progresso-semanal")
def progresso_semanal(
    inicio: str = Query(..., description="Data inicial no formato YYYY-MM-DD"),
    fim: str = Query(..., description="Data final no formato YYYY-MM-DD"),
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario or not usuario.data_menstruacao:
        raise HTTPException(status_code=404, detail="Usuária não encontrada ou sem menstruação registrada")

    try:
        data_inicio = datetime.strptime(inicio, "%Y-%m-%d").date()

        data_fim = datetime.strptime(fim, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido")

    dias_da_semana = (data_fim - data_inicio).days + 1
    if dias_da_semana <= 0:
        raise HTTPException(status_code=400, detail="Intervalo inválido")

    # Buscar treinos realizados no período
    treinos_realizados = db.query(TreinoRealizado).filter(
        TreinoRealizado.usuario_id == usuario.id,
        TreinoRealizado.data >= data_inicio,
        TreinoRealizado.data <= data_fim,
    ).all()

    treinos_por_data = {}

    for t in treinos_realizados:
        if isinstance(t.data, datetime):
            dia = t.data.date()
        else:
            dia = t.data

        valor = float(t.percentual_concluido or 0)
        if dia not in treinos_por_data or valor > treinos_por_data[dia]:
            treinos_por_data[dia] = valor

    for dia, valor in treinos_por_data.items():
        print(f"🧾 Dia {dia} → {valor}% concluído")

    soma = 0
    dias_com_treino_esperado = 0

    for i in range(dias_da_semana):
        dia = data_inicio + timedelta(days=i)
        fase = fase_do_dia(usuario.data_menstruacao, dia)

        if fase in ["Menstruação", "Folicular", "Ovulatória", "Lútea"]:
            progresso = treinos_por_data.get(dia, 0)
            print(f"🔎 Verificando dia {dia}: fase={fase}, progresso={progresso}")
            dias_com_treino_esperado += 1
            soma += progresso

    if dias_com_treino_esperado == 0:
        return {"media_percentual": 0}

    media = soma / dias_com_treino_esperado

    print("📅 Treinos por data:", treinos_por_data)
    print(f"✅ Soma: {soma} | Dias com treino esperado: {dias_com_treino_esperado} | Média: {media:.1f}%")

    return {"media_percentual": round(media, 1)}
    
    
@router.get("/diagnostico")
@verificar_acesso(recurso_premium=False, permite_trial=True)
def diagnostico_treinos(
    data_inicio: Optional[str] = Query(None, description="Data inicial no formato YYYY-MM-DD (opcional)"),
    data_fim: Optional[str] = Query(None, description="Data final no formato YYYY-MM-DD (opcional)"),
    db: Session = Depends(get_db),
    email: str = Depends(verificar_token)
):
    """
    Endpoint para diagnóstico dos treinos registrados.
    Retorna informações detalhadas sobre os treinos para ajudar na identificação de problemas.
    """
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuária não encontrada")
    
    # Se não informar datas, usa últimos 30 dias
    hoje = date.today()
    try:
        if data_inicio:
            inicio = datetime.strptime(data_inicio, "%Y-%m-%d").date()
        else:
            inicio = hoje - timedelta(days=30)
            
        if data_fim:
            fim = datetime.strptime(data_fim, "%Y-%m-%d").date()
        else:
            fim = hoje
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD.")
        
    # Buscar todos os treinos no período
    treinos = db.query(TreinoRealizado).filter(
        TreinoRealizado.usuario_id == usuario.id,
        TreinoRealizado.data >= inicio,
        TreinoRealizado.data <= fim
    ).order_by(TreinoRealizado.data.desc(), TreinoRealizado.id.desc()).all()
    
    # Organizar treinos por data
    treinos_por_data = {}
    for t in treinos:
        data_key = t.data.isoformat() if isinstance(t.data, date) else str(t.data)
        if data_key not in treinos_por_data:
            treinos_por_data[data_key] = []
            
        treinos_por_data[data_key].append({
            "id": t.id,
            "fase": t.fase,
            "tipo": t.treino,
            "percentual": float(t.percentual_concluido or 0),
            "pontos": t.pontos or 0
        })
    
    # Informações de resumo
    resumo = {
        "total_treinos": len(treinos),
        "dias_com_treino": len(treinos_por_data),
        "media_percentual": round(sum(float(t.percentual_concluido or 0) for t in treinos) / len(treinos), 1) if treinos else 0,
        "pontos_totais": usuario.pontos_totais,
        "dias_no_periodo": (fim - inicio).days + 1
    }
    
    # Análise de duplicidades e possíveis problemas
    dias_com_multiplos_treinos = {
        data: treinos for data, treinos in treinos_por_data.items() 
        if len(treinos) > 1
    }
    
    problemas = []
    
    # Verificar dias com múltiplos treinos do mesmo tipo
    for data, treinos_dia in dias_com_multiplos_treinos.items():
        tipos = {}
        for t in treinos_dia:
            if t["tipo"] not in tipos:
                tipos[t["tipo"]] = []
            tipos[t["tipo"]].append(t)
                
        for tipo, treinos_tipo in tipos.items():
            if len(treinos_tipo) > 1:
                problemas.append({
                    "tipo": "duplicidade_mesmo_tipo",
                    "data": data,
                    "tipo_treino": tipo,
                    "registros": treinos_tipo
                })
    
    return {
        "periodo": {
            "inicio": inicio.isoformat(),
            "fim": fim.isoformat()
        },
        "resumo": resumo,
        "treinos_por_data": treinos_por_data,
        "dias_com_multiplos_treinos": len(dias_com_multiplos_treinos),
        "problemas_detectados": problemas
    }
