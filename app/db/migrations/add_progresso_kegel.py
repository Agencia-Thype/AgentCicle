"""
Migração para adicionar a tabela de progresso de Kegel.

A conferência usa o inspector do SQLAlchemy: a consulta a sqlite_master só
funciona no SQLite e interrompia as migrações seguintes no Postgres.
"""
from sqlalchemy import inspect

from app.db.database import engine
from app.models.sqlalchemy_models import ProgressoKegel


def criar_tabela_progresso_kegel():
    """Cria a tabela de progresso de Kegel se não existir."""
    ProgressoKegel.__table__.create(engine, checkfirst=True)

    if inspect(engine).has_table("progresso_kegel"):
        print("Tabela 'progresso_kegel' pronta!")
    else:
        print("ERRO: tabela 'progresso_kegel' não foi criada.")


if __name__ == "__main__":
    criar_tabela_progresso_kegel()
