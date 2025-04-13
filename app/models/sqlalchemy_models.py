from sqlalchemy import Column, DateTime, Float, Integer, String, Date, Numeric, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    verificado = Column(Integer, default=0)
    codigo_validacao = Column(String)  # ✅ ESTA LINHA É NOVA
    tipo = Column(String, default="comum")
    data_criacao = Column(Date)
    data_menstruacao = Column(Date)
    duracao_ciclo = Column(Integer)
    altura = Column(Numeric)
    peso_atual = Column(Numeric)
    objetivo = Column(Text)
    data_peso_atual = Column(Date)
    tentativas_codigo = Column(Integer, default=0)
    validade_codigo = Column(DateTime)
    pontos_totais = Column(Integer, default=0)
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
