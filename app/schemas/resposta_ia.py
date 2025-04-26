from pydantic import BaseModel

class RespostaIA(BaseModel):
    fase_atual: str
    resposta: str
