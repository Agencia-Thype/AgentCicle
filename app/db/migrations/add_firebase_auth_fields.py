"""
Migração para trocar a autenticação por Firebase: adiciona o campo
firebase_uid na tabela usuarios e torna senha_hash opcional (deixa de ser
usado para novos usuários, mas é preservado para o script de migração
de usuários existentes).
"""
from app.db.database import engine
from sqlalchemy import text


def _colunas_usuarios(conn):
    result = conn.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'usuarios'"
    ))
    return [row[0] for row in result.fetchall()]


def adicionar_campos_firebase():
    """Adiciona firebase_uid e torna senha_hash opcional na tabela usuarios."""

    with engine.connect() as conn:
        colunas = _colunas_usuarios(conn)

        if "firebase_uid" not in colunas:
            conn.execute(text(
                "ALTER TABLE usuarios ADD COLUMN firebase_uid VARCHAR"
            ))
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_usuarios_firebase_uid "
                "ON usuarios (firebase_uid)"
            ))
            print("✅ Campo 'firebase_uid' adicionado à tabela 'usuarios'!")
        else:
            print("ℹ️ Campo 'firebase_uid' já existe na tabela 'usuarios'")

        conn.execute(text(
            "ALTER TABLE usuarios ALTER COLUMN senha_hash DROP NOT NULL"
        ))
        conn.commit()
        print("✅ Campo 'senha_hash' agora é opcional na tabela 'usuarios'!")


if __name__ == "__main__":
    adicionar_campos_firebase()
