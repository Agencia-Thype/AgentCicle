"""
Migração para adicionar o campo duracao_menstruacao na tabela usuarios.

Sem valor padrão no banco: NULL quer dizer "não informado", e o cálculo das
fases usa 5 dias nesse caso.
"""
from sqlalchemy import inspect, text

from app.db.database import engine


def _tem_coluna(nome: str) -> bool:
    return nome in {coluna["name"] for coluna in inspect(engine).get_columns("usuarios")}


def adicionar_campo_duracao_menstruacao():
    """Adiciona o campo duracao_menstruacao na tabela usuarios se não existir."""
    if _tem_coluna("duracao_menstruacao"):
        print("Campo 'duracao_menstruacao' já existe na tabela 'usuarios'")
        return

    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE usuarios ADD COLUMN duracao_menstruacao INTEGER"))
        conn.commit()

    if _tem_coluna("duracao_menstruacao"):
        print("Campo 'duracao_menstruacao' adicionado à tabela 'usuarios'!")
    else:
        print("ERRO: campo 'duracao_menstruacao' não foi adicionado.")


if __name__ == "__main__":
    adicionar_campo_duracao_menstruacao()
