"""
Script principal de migrações para o sistema de Kegel.

Execute este script para aplicar todas as migrações necessárias.
"""
import sys
import os

# Os prints usam emoji: sem UTF-8 na saída, o Windows derruba a migração
# no meio (cp1252 não tem esses caracteres) e esconde o erro de verdade.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app.db.migrations.add_nivel_kegel_usuario import adicionar_campo_nivel_kegel
from app.db.migrations.add_progresso_kegel import criar_tabela_progresso_kegel
from app.db.migrations.add_firebase_auth_fields import adicionar_campos_firebase
from app.db.migrations.add_exercicios_concluidos_treino import adicionar_exercicios_concluidos_treino
from app.db.migrations.add_kegel_diario import criar_tabela_kegel_diario
from app.db.migrations.add_rotina import criar_tabelas_rotina
from app.db.migrations.add_compras_loja import criar_tabela_compras_loja
from app.db.migrations.add_performance_indexes import criar_indices_performance

def run_migrations():
    """Executa todas as migrações pendentes."""
    print("=" * 60)
    print("MIGRAÇÕES DO BANCO DE DADOS")
    print("=" * 60)
    print()

    try:
        print("1/7 - Adicionando campo nivel_kegel à tabela usuarios...")
        adicionar_campo_nivel_kegel()
        print()

        print("2/7 - Criando tabela progresso_kegel...")
        criar_tabela_progresso_kegel()
        print()

        print("3/7 - Adicionando campos de autenticação Firebase...")
        adicionar_campos_firebase()
        print()

        print("4/7 - Adicionando exercícios concluídos ao treino realizado...")
        adicionar_exercicios_concluidos_treino()
        print()

        print("5/7 - Criando tabela kegel_diario (pontuação diária do Kegel)...")
        criar_tabela_kegel_diario()
        print()

        print("6/7 - Criando tabelas da rotina (suplementos, medicamentos e água)...")
        criar_tabelas_rotina()
        print()

        print("7/7 - Criando tabela compras_loja (compras validadas nas lojas)...")
        criar_tabela_compras_loja()
        print()

        print("8/8 - Criando indices de performance...")
        criar_indices_performance()
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
