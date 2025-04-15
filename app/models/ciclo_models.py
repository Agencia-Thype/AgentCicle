from pydantic import BaseModel
from datetime import date

class CicloRequest(BaseModel):
    data_menstruacao: str  # formato: YYYY-MM-DD

class CicloResponse(BaseModel):
    fase: str
    mensagem: str

class RegistroMenstruacao(BaseModel):
    email: str
    data_inicio: date