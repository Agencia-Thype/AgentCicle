from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class IaHistoricoMensagem(Base):
    __tablename__ = "ia_historico_mensagens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    pergunta = Column(Text, nullable=False)
    resposta = Column(Text, nullable=False)
    contexto = Column(Text)  # JSON serializado com dados como fase, treinos etc.
    data_hora = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", backref="historico_ia")
