from pydantic import BaseModel
from typing import Optional
from datetime import date

class PerfilUsuario(BaseModel):
    nome: Optional[str]
    altura: Optional[float]
    peso_atual: Optional[float]
    objetivo: Optional[str]
    data_menstruacao: Optional[date]
