"""
Migração para adicionar a tabela de progresso de Kegel.

Execute este script para criar a tabela progresso_kegel no banco de dados.
"""
from app.db.database import engine, Base
from app.models.sqlalchemy_models import ProgressoKegel
from sqlalchemy import text

def criar_tabela_progresso_kegel():
    """Cria a tabela de progresso de Kegel se não existir."""

    # Criar a tabela usando SQLAlchemy
    ProgressoKegel.__table__.create(engine, checkfirst=True)

    print("✅ Tabela 'progresso_kegel' criada com sucesso!")

    # Verificar se a tabela foi criada
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='progresso_kegel'"
        ))
        if result.fetchone():
            print("✅ Tabela 'progresso_kegel' verificada no banco de dados!")
        else:
            print("❌ Erro: Tabela 'progresso_kegel' não foi criada.")

if __name__ == "__main__":
    criar_tabela_progresso_kegel()
