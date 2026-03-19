@echo off
REM Script para executar testes em Windows

echo ====================================
echo  Suite de Testes - AgentCicle API
echo ====================================
echo.

REM Verificar se está no diretório correto
if not exist "app\main.py" (
    echo ❌ Erro: Execute este script diretamente do diretorio 'AgentCicle'
    pause
    exit /b 1
)

REM Menu de opcoes
echo Escolha o tipo de teste:
echo 1. Todos os testes
echo 2. Testes especificos (auth)
echo 3. Testes especificos (assinatura)
echo 4. Testes com coverage
echo 5. Sair
echo.

set /p escolha="Digite sua escolha (1-5): "

if "%escolha%"=="1" (
    echo.
    echo 🚀 Executando todos os testes...
    pytest tests/ -v
) else if "%escolha%"=="2" (
    echo.
    echo 🔐 Executando testes de autenticacao...
    pytest tests/test_auth.py -v
) else if "%escolha%"=="3" (
    echo.
    echo 💳 Executando testes de assinatura...
    pytest tests/test_assinatura.py -v
) else if "%escolha%"=="4" (
    echo.
    echo 📊 Executando testes com coverage...
    pytest tests/ -v --cov=app --cov-report=html --cov-report=term
    echo.
    echo ✅ Coverage report gerado: htmlcov/index.html
) else if "%escolha%"=="5" (
    echo.
    echo 👋 Saindo...
    pause
    exit /b 0
) else (
    echo.
    echo ❌ Escolha invalida
    pause
    exit /b 1
)

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ Testes concluidos com sucesso!
) else (
    echo.
    echo ❌ Alguns testes falharam
)

pause
