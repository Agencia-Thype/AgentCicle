
from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class SintomasRequest(BaseModel):
    sentimentos: List[str]
    observacao: Optional[str] = None
    fase: Optional[str] = None
    data: Optional[date] = None  