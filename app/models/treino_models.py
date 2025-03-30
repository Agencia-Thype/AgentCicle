from pydantic import BaseModel
from typing import Optional

class TreinoResponse(BaseModel):
    fase: str
    tipo_treino: Optional[str]
    exercicio: str
    metodo: Optional[str]
    series: Optional[str]
    repeticoes: Optional[str]
    descanso: Optional[str]
    cadencia: Optional[str]
    intensidade: Optional[str]
    duracao: Optional[str]
    obs: Optional[str]
    link_video: Optional[str]
