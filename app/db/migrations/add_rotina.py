"""
Migração: cria as tabelas da rotina de cuidados (suplementos, medicamentos,
vitaminas e hidratação).

Usa create(checkfirst=True) do SQLAlchemy, que funciona igual no Postgres e
no SQLite e não faz nada se a tabela já existir.
"""
from app.db.database import engine
from app.models.sqlalchemy_models import AguaRegistro, ConfigHidratacao, DoseRotina, ItemRotina


def criar_tabelas_rotina():
    """Cria as tabelas da rotina que ainda não existirem."""
    # itens_rotina antes de doses_rotina, que aponta para ela.
    for modelo in (ItemRotina, DoseRotina, AguaRegistro, ConfigHidratacao):
        modelo.__table__.create(engine, checkfirst=True)
        print(f"✅ Tabela '{modelo.__tablename__}' pronta!")


if __name__ == "__main__":
    criar_tabelas_rotina()
