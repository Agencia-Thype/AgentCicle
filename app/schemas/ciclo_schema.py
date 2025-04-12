from pydantic import BaseModel
from datetime import date

class RegistroMenstruacao(BaseModel):
    data_inicio: date