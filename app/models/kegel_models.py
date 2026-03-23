from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class NivelKegel(str, Enum):
    INICIANTE = "iniciante"
    INTERMEDIARIO = "intermediario"
    AVANCADO = "avancado"

class FaseKegel(BaseModel):
    """Fase individual do exercício de Kegel (contração/relaxamento)"""
    tipo: str = Field(..., description="Tipo da fase: 'contracao' ou 'relaxamento'")
    duracao_segundos: float = Field(..., description="Duração em segundos")
    instrucao: str = Field(..., description="Instrução textual para o usuário")

class SerieKegel(BaseModel):
    """Série de exercícios de Kegel"""
    repeticoes: int = Field(..., description="Número de repetições")
    fases: List[FaseKegel] = Field(..., description="Lista de fases da série")

class ExercicioKegel(BaseModel):
    """Exercício completo de Kegel"""
    id: str = Field(..., description="Identificador único do exercício")
    nome: str = Field(..., description="Nome do exercício")
    nivel: NivelKegel = Field(..., description="Nível de dificuldade")
    objetivo: str = Field(..., description="Objetivo do exercício (resistência, hipertrofia, potência, agilidade)")
    series: int = Field(..., description="Número de séries")
    descanso_segundos: int = Field(..., description="Tempo de descanso entre séries em segundos")
    instrucoes: List[SerieKegel] = Field(..., description="Instruções detalhadas das séries")

class TreinoKegelResponse(BaseModel):
    """Resposta da API com o treino de Kegel do dia"""
    nivel: NivelKegel = Field(..., description="Nível atual do usuário")
    exercicios: List[ExercicioKegel] = Field(..., description="Lista de exercícios do dia")
    progresso_usuario: Optional[dict] = Field(None, description="Informações sobre o progresso do usuário")

class ProgressoKegel(BaseModel):
    """Modelo para registrar progresso em exercícios de Kegel"""
    nivel: NivelKegel = Field(..., description="Nível realizado")
    exercicio_id: str = Field(..., description="ID do exercício realizado")
    series_completas: int = Field(..., description="Número de séries completadas")
    percentual_conclusao: float = Field(..., description="Percentual de conclusão do exercício")
