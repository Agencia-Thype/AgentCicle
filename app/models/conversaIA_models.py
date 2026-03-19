from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, Boolean, String, JSON
from datetime import datetime
from app.db.database import Base
from sqlalchemy.orm import relationship

class ConversaIA(Base):
    __tablename__ = "conversas_ia"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("usuarios.id", ondelete="CASCADE"))
    data = Column(DateTime, default=datetime.utcnow)

    pergunta = Column(Text, nullable=False)
    resposta = Column(Text, nullable=False)
    contexto = Column(JSON)  # dados do ciclo, percentual, sentimentos, etc

    fase = Column(String)  # Ex: Lútea
    tema = Column(String)  # Ex: "fome", "motivação", "cansaço", etc
    resposta_emocional = Column(Boolean, default=False)
    treino_recomendado = Column(Text)

    # Relacionamento reverso se quiser usar no usuário
    usuario = relationship("Usuario", backref="conversas_ia")
