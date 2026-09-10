"""
Migração: cria a tabela kegel_diario, base da pontuação diária do Kegel.

Usa create(checkfirst=True) do SQLAlchemy, que funciona igual no Postgres e
no SQLite e não faz nada se a tabela já existir.
"""
from app.db.database import engine
from app.models.sqlalchemy_models import KegelDiario


def criar_tabela_kegel_diario():
    """Cria a tabela kegel_diario se ainda não existir."""
    KegelDiario.__table__.create(engine, checkfirst=True)
    print("✅ Tabela 'kegel_diario' pronta!")


if __name__ == "__main__":
    criar_tabela_kegel_diario()
