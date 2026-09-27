"""
Migration: cria indices compostos para as consultas mais frequentes do app.

As telas de abertura filtram muito por usuario + data. Sem estes indices, o
banco precisa varrer mais linhas conforme o uso cresce.
"""
from sqlalchemy import text

from app.db.database import engine


INDEXES = (
    "CREATE INDEX IF NOT EXISTS ix_treino_realizado_usuario_data ON treino_realizado (usuario_id, data)",
    "CREATE INDEX IF NOT EXISTS ix_diario_ciclo_user_data ON diario_ciclo (user_id, data)",
    "CREATE INDEX IF NOT EXISTS ix_progresso_kegel_usuario_data ON progresso_kegel (usuario_id, data_conclusao)",
    "CREATE INDEX IF NOT EXISTS ix_kegel_diario_usuario_data ON kegel_diario (usuario_id, data)",
    "CREATE INDEX IF NOT EXISTS ix_doses_rotina_usuario_data ON doses_rotina (usuario_id, data)",
    "CREATE INDEX IF NOT EXISTS ix_itens_rotina_usuario_ativo ON itens_rotina (usuario_id, ativo)",
    "CREATE INDEX IF NOT EXISTS ix_agua_registros_usuario_data ON agua_registros (usuario_id, data)",
)


def criar_indices_performance():
    """Cria indices idempotentes para acelerar as telas principais."""
    with engine.begin() as conn:
        for ddl in INDEXES:
            conn.execute(text(ddl))
    print("Indices de performance prontos.")


if __name__ == "__main__":
    criar_indices_performance()
