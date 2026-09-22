"""
Migração: cria a tabela das compras confirmadas pelas lojas.

É ela que impede reusar o mesmo recibo em outra conta quando a cobrança está
ligada. Usa create(checkfirst=True), que não faz nada se a tabela já existir.
"""
from app.db.database import engine
from app.models.sqlalchemy_models import CompraLoja


def criar_tabela_compras_loja():
    """Cria compras_loja se ainda não existir."""
    CompraLoja.__table__.create(engine, checkfirst=True)
    print("Tabela 'compras_loja' pronta!")


if __name__ == "__main__":
    criar_tabela_compras_loja()
