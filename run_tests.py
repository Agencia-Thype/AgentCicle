#!/usr/bin/env python3
"""
Script para executar os testes da API AgentCicle
"""

import subprocess
import sys
import os


def run_command(command, description):
    """Executa um comando e exibe o resultado"""
    print(f"\n{'='*60}")
    print(f" {description}")
    print(f"{'='*60}")

    result = subprocess.run(
        command,
        shell=True,
        capture_output=False,
        text=True
    )

    return result.returncode == 0


def main():
    """Função principal para executar os testes"""

    # Verificar se está no diretório correto
    if not os.path.exists("app/main.py"):
        print("❌ Erro: Execute este script diretamente do diretório 'AgentCicle'")
        sys.exit(1)

    print("🧪 Suite de Testes - AgentCicle API")
    print("="*60)

    # Opções de teste
    print("\nEscolha o tipo de teste:")
    print("1. Todos os testes")
    print("2. Testes rápidos (exclui lentos)")
    print("3. Testes específicos (auth)")
    print("4. Testes específicos (assinatura)")
    print("5. Testes com coverage")
    print("6. Sair")

    escolha = input("\nDigite sua escolha (1-6): ").strip()

    success = False

    if escolha == "1":
        success = run_command(
            "pytest tests/ -v",
            "🚀 Executando todos os testes..."
        )

    elif escolha == "2":
        success = run_command(
            "pytest tests/ -v -m 'not slow'",
            "⚡ Executando testes rápidos..."
        )

    elif escolha == "3":
        success = run_command(
            "pytest tests/test_auth.py -v",
            "🔐 Executando testes de autenticação..."
        )

    elif escolha == "4":
        success = run_command(
            "pytest tests/test_assinatura.py -v",
            "💳 Executando testes de assinatura..."
        )

    elif escolha == "5":
        success = run_command(
            "pytest tests/ -v --cov=app --cov-report=html --cov-report=term",
            "📊 Executando testes com coverage..."
        )

        if success:
            print("\n✅ Coverage report gerado: htmlcov/index.html")

    elif escolha == "6":
        print("👋 Saindo...")
        sys.exit(0)

    else:
        print("❌ Escolha inválida")
        sys.exit(1)

    if success:
        print("\n✅ Testes concluídos com sucesso!")
        sys.exit(0)
    else:
        print("\n❌ Alguns testes falharam")
        sys.exit(1)


if __name__ == "__main__":
    main()
