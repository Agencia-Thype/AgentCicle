from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class DiarioCicloRequest(BaseModel):
    data: date
    sentimento: List[str]
    observacao: Optional[str] = None
    fase: Optional[str] = None
    treino_tipo: Optional[str] = None

