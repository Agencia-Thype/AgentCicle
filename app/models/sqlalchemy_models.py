from sqlalchemy import Column, DateTime, Float, Integer, String, Date, Numeric, Text, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    senha_hash = Column(String, nullable=True)  # legado (pré-Firebase); não usado para novos usuários
    firebase_uid = Column(String, unique=True, index=True, nullable=True)
    verificado = Column(Integer, default=0)
    codigo_validacao = Column(String)  # ✅ ESTA LINHA É NOVA
    tipo = Column(String, default="comum")
    data_criacao = Column(Date)
    data_menstruacao = Column(Date)
    duracao_ciclo = Column(Integer)
    duracao_menstruacao = Column(Integer)  # dias de sangramento; NULL = não informado (vale 5)
    altura = Column(Numeric)
    peso_atual = Column(Numeric)
    objetivo = Column(Text)
    data_peso_atual = Column(Date)
    ultima_atualizacao_menstruacao = Column(DateTime)  # Campo para rastrear quando a data da menstruação foi atualizada pela última vez
    tentativas_codigo = Column(Integer, default=0)
    validade_codigo = Column(DateTime)
    pontos_totais = Column(Integer, default=0)
    
    # Campos para controle de trial e assinatura
    data_criacao_conta = Column(DateTime)
    data_fim_trial = Column(DateTime)
    assinatura_ativa = Column(Integer, default=0)  # Usando Integer em vez de Boolean para compatibilidade
    data_inicio_assinatura = Column(DateTime, nullable=True)
    data_fim_assinatura = Column(DateTime, nullable=True)

    # Campo para controle do nível de exercícios de Kegel
    nivel_kegel = Column(String, default="iniciante", nullable=True)

    treinos = relationship("TreinoRealizado", back_populates="usuario")
    registros_ciclo = relationship("DiarioCiclo", back_populates="usuario")

    historico_peso = relationship("HistoricoPeso", back_populates="usuario")

class HistoricoPeso(Base):
    __tablename__ = "historico_peso"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuarios.id"))
    peso = Column(Numeric)
    altura = Column(Numeric)
    imc = Column(Numeric)
    data_registro = Column(Date)

    usuario = relationship("Usuario", back_populates="historico_peso")

class TreinoRealizado(Base):
    __tablename__ = "treino_realizado"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    data = Column(Date)
    fase = Column(String)
    treino = Column(String)
    percentual_concluido = Column(Float)
    pontos = Column(Integer)
    # Nomes dos exercícios marcados, para a tela restaurar exatamente os mesmos.
    exercicios_concluidos = Column(JSON)

    usuario = relationship("Usuario", back_populates="treinos")

class DiarioCiclo(Base):
    __tablename__ = "diario_ciclo"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuarios.id"))
    data = Column(Date, nullable=False)
    sentimento = Column(Text)
    observacao = Column(Text)
    fase = Column(String)
    treino_tipo = Column(String)
    created_at = Column(DateTime)

    usuario = relationship("Usuario", back_populates="registros_ciclo")

class ProgressoKegel(Base):
    __tablename__ = "progresso_kegel"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    nivel = Column(String, nullable=False)  # iniciante, intermediario, avancado
    exercicio_id = Column(String, nullable=False)
    data_conclusao = Column(DateTime, nullable=False)
    series_completas = Column(Integer, default=0)
    percentual_conclusao = Column(Float, default=0)
    concluido = Column(Integer, default=0)  # 0 = não, 1 = sim

    usuario = relationship("Usuario")


class KegelDiario(Base):
    """
    Exercícios de Kegel feitos em cada dia - base da pontuação diária.

    ProgressoKegel é vitalício (desbloqueio de nível); este registro é por dia,
    uma linha por exercício, para pontuar cada exercício só uma vez por dia.
    """
    __tablename__ = "kegel_diario"
    __table_args__ = (
        UniqueConstraint("usuario_id", "data", "exercicio_id", name="uq_kegel_diario_exercicio_dia"),
    )

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    data = Column(Date, nullable=False)
    nivel = Column(String, nullable=False)
    exercicio_id = Column(String, nullable=False)
    pontos = Column(Integer, default=0)
    created_at = Column(DateTime)


class ItemRotina(Base):
    """
    Suplemento, vitamina ou medicamento da rotina da usuária.

    Excluir não apaga a linha: marca ativo=0 e encerra o item ontem, para o
    histórico dos dias anteriores continuar contando as doses que eram previstas.
    """
    __tablename__ = "itens_rotina"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    nome = Column(String, nullable=False)
    categoria = Column(String, nullable=False)  # suplemento, medicamento, vitamina
    dosagem = Column(String)
    frequencia = Column(String, nullable=False, default="todos_os_dias")  # ou dias_especificos
    # 0 = domingo ... 6 = sábado, a mesma convenção do app (Date.getDay).
    dias_semana = Column(JSON)
    horarios = Column(JSON, nullable=False)  # ["08:00", "21:00"]
    data_inicio = Column(Date, nullable=False)
    data_fim = Column(Date)
    observacoes = Column(Text)
    indicado_medico = Column(Integer, default=0)
    lembrete_ativo = Column(Integer, default=1)
    controle_estoque = Column(Integer, default=0)
    estoque_atual = Column(Integer)
    estoque_alerta = Column(Integer)
    ativo = Column(Integer, default=1)
    created_at = Column(DateTime)


class DoseRotina(Base):
    """Dose tomada: uma linha por item, dia e horário."""
    __tablename__ = "doses_rotina"
    __table_args__ = (
        UniqueConstraint("item_id", "data", "horario", name="uq_dose_rotina_item_dia_horario"),
    )

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    item_id = Column(Integer, ForeignKey("itens_rotina.id"), nullable=False, index=True)
    data = Column(Date, nullable=False)
    horario = Column(String, nullable=False)
    tomado_em = Column(DateTime)


class AguaRegistro(Base):
    """Cada copo registrado na hidratação do dia."""
    __tablename__ = "agua_registros"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    data = Column(Date, nullable=False, index=True)
    ml = Column(Integer, nullable=False)
    created_at = Column(DateTime)


class ConfigHidratacao(Base):
    """Meta e lembretes de água escolhidos pela usuária. Sem linha, vale a sugestão."""
    __tablename__ = "config_hidratacao"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, unique=True, index=True)
    meta_ml = Column(Integer)
    lembretes = Column(JSON)  # ["09:00", "11:00"]
    lembretes_ativos = Column(Integer, default=1)


class CompraLoja(Base):
    """
    Compra confirmada pela App Store ou pela Google Play.

    Guarda o id da transação para que o mesmo pagamento não ative premium em
    duas contas: o recibo é de quem comprou, e o aparelho pode reenviá-lo.
    """
    __tablename__ = "compras_loja"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    plataforma = Column(String, nullable=False)  # ios | android
    id_transacao = Column(String, nullable=False, unique=True, index=True)
    # Token que a loja manda nas notificações de renovação e cancelamento.
    token_compra = Column(String, index=True)
    product_id = Column(String, nullable=False)
    duracao_meses = Column(Integer, nullable=False)
    expira_em = Column(DateTime)
    created_at = Column(DateTime)
