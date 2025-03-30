from pydantic import BaseModel

class CicloRequest(BaseModel):
    data_menstruacao: str  # formato: YYYY-MM-DD

class CicloResponse(BaseModel):
    fase: str
    mensagem: str
