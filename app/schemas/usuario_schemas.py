from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import List, Optional
from datetime import date

class UsuarioRegister(BaseModel):
    nome: str
    email: EmailStr
    senha: str = Field(min_length=6)
    confirmacao_senha: str

    @model_validator(mode="after")
    def senhas_devem_bater(self) -> "UsuarioRegister":
        if self.senha != self.confirmacao_senha:
            raise ValueError("As senhas não conferem")
        return self

class UsuarioLogin(BaseModel):
    email: EmailStr
    senha: str

class ValidarEmailRequest(BaseModel):
    email: EmailStr
    codigo: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class RegistroPeso(BaseModel):
    peso: float
    altura: Optional[float]
    imc: Optional[float]
    data: date

class PerfilUsuario(BaseModel):
    nome: Optional[str]
    altura: Optional[float]
    peso_atual: Optional[float]
    objetivo: Optional[str]
    data_menstruacao: Optional[date]
    imc: Optional[float]  # novo campo
    historico_peso: Optional[List[RegistroPeso]] = []  # novo campo
