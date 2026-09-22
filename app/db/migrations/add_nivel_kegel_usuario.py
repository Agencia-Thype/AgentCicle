"""
Migração para adicionar o campo nivel_kegel na tabela usuarios.

A verificação usa o inspector do SQLAlchemy em vez de PRAGMA table_info: o
PRAGMA só existe no SQLite e derrubava a cadeia inteira de migrações quando
rodada contra o Postgres de produção.
"""
from sqlalchemy import inspect, text

from app.db.database import engine


def _tem_coluna(nome: str) -> bool:
    return nome in {coluna["name"] for coluna in inspect(engine).get_columns("usuarios")}


def adicionar_campo_nivel_kegel():
    """Adiciona o campo nivel_kegel na tabela usuarios se não existir."""
    if _tem_coluna("nivel_kegel"):
        print("Campo 'nivel_kegel' já existe na tabela 'usuarios'")
        return

    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE usuarios ADD COLUMN nivel_kegel VARCHAR DEFAULT 'iniciante'"
        ))
        conn.commit()

    if _tem_coluna("nivel_kegel"):
        print("Campo 'nivel_kegel' adicionado à tabela 'usuarios'!")
    else:
        print("ERRO: campo 'nivel_kegel' não foi adicionado.")


if __name__ == "__main__":
    adicionar_campo_nivel_kegel()
