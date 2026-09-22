import re
from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

_HORARIO = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def normalizar_horarios(horarios: List[str]) -> List[str]:
    """Valida "HH:MM", tira repetidos e ordena."""
    for horario in horarios:
        if not _HORARIO.match(horario):
            raise ValueError(f"Horário inválido: '{horario}'. Use HH:MM.")
    return sorted(set(horarios))


def _texto_opcional(valor: Optional[str]) -> Optional[str]:
    if valor is None:
        return None
    valor = valor.strip()
    return valor or None


class ItemRotinaRequest(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    categoria: Literal["suplemento", "medicamento", "vitamina"]
    dosagem: Optional[str] = Field(default=None, max_length=60)
    frequencia: Literal["todos_os_dias", "dias_especificos"] = "todos_os_dias"
    # 0 = domingo ... 6 = sábado
    dias_semana: List[int] = Field(default_factory=list)
    horarios: List[str] = Field(min_length=1, max_length=8)
    data_inicio: date
    data_fim: Optional[date] = None
    observacoes: Optional[str] = Field(default=None, max_length=500)
    indicado_medico: bool = False
    lembrete_ativo: bool = True
    controle_estoque: bool = False
    estoque_atual: Optional[int] = Field(default=None, ge=0)
    estoque_alerta: Optional[int] = Field(default=None, ge=0)

    @field_validator("nome")
    @classmethod
    def validar_nome(cls, valor: str) -> str:
        valor = valor.strip()
        if not valor:
            raise ValueError("Informe o nome do item.")
        return valor

    @field_validator("dosagem", "observacoes")
    @classmethod
    def limpar_texto(cls, valor: Optional[str]) -> Optional[str]:
        return _texto_opcional(valor)

    @field_validator("horarios")
    @classmethod
    def validar_horarios(cls, valor: List[str]) -> List[str]:
        return normalizar_horarios(valor)

    @field_validator("dias_semana")
    @classmethod
    def validar_dias(cls, valor: List[int]) -> List[int]:
        if any(dia < 0 or dia > 6 for dia in valor):
            raise ValueError("Os dias da semana vão de 0 (domingo) a 6 (sábado).")
        return sorted(set(valor))

    @model_validator(mode="after")
    def validar_conjunto(self):
        if self.frequencia == "dias_especificos" and not self.dias_semana:
            raise ValueError("Escolha pelo menos um dia da semana.")
        if self.frequencia == "todos_os_dias":
            self.dias_semana = []
        if self.data_fim and self.data_fim < self.data_inicio:
            raise ValueError("A data de fim não pode ser antes da data de início.")
        if self.controle_estoque:
            if self.estoque_alerta is None:
                self.estoque_alerta = 5
        else:
            self.estoque_atual = None
            self.estoque_alerta = None
        return self


class DoseRequest(BaseModel):
    item_id: int
    horario: str
    data: Optional[date] = None  # sem data, vale hoje

    @field_validator("horario")
    @classmethod
    def validar_horario(cls, valor: str) -> str:
        return normalizar_horarios([valor])[0]


class AguaRequest(BaseModel):
    ml: int = Field(gt=0, le=2000)
    data: Optional[date] = None


class ConfigHidratacaoRequest(BaseModel):
    meta_ml: int = Field(ge=500, le=6000)
    lembretes: List[str] = Field(default_factory=list, max_length=12)
    lembretes_ativos: bool = True

    @field_validator("lembretes")
    @classmethod
    def validar_lembretes(cls, valor: List[str]) -> List[str]:
        return normalizar_horarios(valor)
