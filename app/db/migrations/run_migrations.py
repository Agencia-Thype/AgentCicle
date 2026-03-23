"""
Script principal de migrações para o sistema de Kegel.

Execute este script para aplicar todas as migrações necessárias.
"""
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.db.migrations.add_nivel_kegel_usuario import adicionar_campo_nivel_kegel
from app.db.migrations.add_progresso_kegel import criar_tabela_progresso_kegel

def run_migrations():
    """Executa todas as migrações do sistema de Kegel."""
    print("=" * 60)
    print("MIGRAÇÕES DO SISTEMA DE EXERCÍCIOS DE KEGEL")
    print("=" * 60)
    print()

    try:
        print("1/2 - Adicionando campo nivel_kegel à tabela usuarios...")
        adicionar_campo_nivel_kegel()
        print()

        print("2/2 - Criando tabela progresso_kegel...")
        criar_tabela_progresso_kegel()
        print()

        print("=" * 60)
        print("✅ TODAS AS MIGRAÇÕES FORAM CONCLUÍDAS COM SUCESSO!")
        print("=" * 60)

    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ ERRO DURANTE AS MIGRAÇÕES: {str(e)}")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    run_migrations()
