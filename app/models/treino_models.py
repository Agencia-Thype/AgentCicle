from pydantic import BaseModel, Field
from typing import Optional
from typing import Literal

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



class ConcluirTreinoRequest(BaseModel):
    tipo_treino: str
    percentual: float
    # Nomes dos exercícios marcados; opcional para versões antigas do app.
    exercicios_concluidos: Optional[list[str]] = None