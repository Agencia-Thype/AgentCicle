from sqlalchemy import Column, DateTime, Integer, String, Date, Numeric, Text, ForeignKey
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
    altura = Column(Numeric)
    peso_atual = Column(Numeric)
    objetivo = Column(Text)
    data_peso_atual = Column(Date)
    tentativas_codigo = Column(Integer, default=0)
    validade_codigo = Column(DateTime)

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
