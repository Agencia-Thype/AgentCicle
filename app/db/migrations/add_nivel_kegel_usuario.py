"""
Migração para adicionar o campo nivel_kegel na tabela usuarios.

Execute este script para adicionar o campo nivel_kegel na tabela usuarios.
"""
from app.db.database import engine
from sqlalchemy import text

def adicionar_campo_nivel_kegel():
    """Adiciona o campo nivel_kegel na tabela usuarios se não existir."""

    with engine.connect() as conn:
        # Verificar se o campo já existe
        result = conn.execute(text("PRAGMA table_info(usuarios)"))
        colunas = [row[1] for row in result.fetchall()]

        if "nivel_kegel" in colunas:
            print("ℹ️ Campo 'nivel_kegel' já existe na tabela 'usuarios'")
            return

        # Adicionar o campo
        conn.execute(text(
            "ALTER TABLE usuarios ADD COLUMN nivel_kegel VARCHAR DEFAULT 'iniciante'"
        ))
        conn.commit()

        print("✅ Campo 'nivel_kegel' adicionado à tabela 'usuarios'!")

        # Verificar se o campo foi adicionado
        result = conn.execute(text("PRAGMA table_info(usuarios)"))
        colunas = [row[1] for row in result.fetchall()]

        if "nivel_kegel" in colunas:
            print("✅ Campo 'nivel_kegel' verificado na tabela 'usuarios'!")
        else:
            print("❌ Erro: Campo 'nivel_kegel' não foi adicionado.")

if __name__ == "__main__":
    adicionar_campo_nivel_kegel()
