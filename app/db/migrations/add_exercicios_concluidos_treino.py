"""
Migração: guarda quais exercícios a usuária marcou em cada treino do dia.

Antes só o percentual era salvo, e ao reabrir a tela o app marcava os
primeiros N exercícios da lista em vez dos que ela realmente fez.
"""
from app.db.database import engine
from sqlalchemy import text


def adicionar_exercicios_concluidos_treino():
    """Adiciona a coluna exercicios_concluidos (JSON) em treino_realizado."""

    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'treino_realizado'"
        ))
        colunas = [row[0] for row in result.fetchall()]

        if "exercicios_concluidos" not in colunas:
            conn.execute(text(
                "ALTER TABLE treino_realizado ADD COLUMN exercicios_concluidos JSON"
            ))
            conn.commit()
            print("✅ Campo 'exercicios_concluidos' adicionado à tabela 'treino_realizado'!")
        else:
            print("ℹ️ Campo 'exercicios_concluidos' já existe na tabela 'treino_realizado'")


if __name__ == "__main__":
    adicionar_exercicios_concluidos_treino()
