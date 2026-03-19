import re
from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import List, Optional
from datetime import date
from pydantic import BaseModel, EmailStr, Field, model_validator


class UsuarioRegister(BaseModel):
    nome: str = Field(min_length=2, max_length=100)
    email: EmailStr
    senha: str = Field(min_length=6, max_length=50)
    confirmacao_senha: str = Field(min_length=6, max_length=50)


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
    nome: Optional[str] = None
    altura: Optional[float] = None
    peso_atual: Optional[float] = None
    objetivo: Optional[str] = None
    data_menstruacao: Optional[date] = None
    duracao_ciclo: Optional[int] = None
    imc: Optional[float] = None
    historico_peso: Optional[List[RegistroPeso]] = []

    class Config:
        from_attributes = True

class AtualizarPerfilRequest(BaseModel):
    nome: Optional[str] = Field(None, min_length=2)
    altura: Optional[float] = Field(None, gt=0)
    peso_atual: Optional[float] = Field(None, gt=0)
    objetivo: Optional[str] = Field(None, max_length=200)
    data_menstruacao: Optional[date]
    duracao_ciclo: Optional[int] = None

    
class AtualizarPerfil(BaseModel):
    nome: Optional[str] = None
    altura: Optional[float] = None
    peso_atual: Optional[float] = None
    objetivo: Optional[str] = None
    data_menstruacao: Optional[date] = None
    duracao_ciclo: Optional[int] = None

    class Config:
        from_attributes = True


class EnviarCodigoRequest(BaseModel):
    email: EmailStr

class RedefinirSenhaRequest(BaseModel):
    email: EmailStr
    codigo: str
    nova_senha: str = Field(min_length=6, max_length=50)
    confirmacao_senha: str


class UsuarioBaseInfo(BaseModel):
    id: int
    nome: str
    email: str


class AssinaturaStatus(BaseModel):
    trialAtivo: bool
    assinaturaAtiva: bool
    temAcesso: bool
    diasRestantesTrial: int
    mensagem: str
    verificadoEm: str
    proximaVerificacao: str
    tempoValidoSegundos: int


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioBaseInfo
    assinatura: Optional[AssinaturaStatus] = None
