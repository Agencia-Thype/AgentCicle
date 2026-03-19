# 🧪 Suite de Testes - AgentCicle API

Testes automatizados completos para validar todos os endpoints da API.

## 📋 Estrutura dos Testes

```
tests/
├── __init__.py
├── conftest.py              # Fixtures e configurações
├── test_auth.py             # Testes de autenticação
├── test_assinatura.py       # Testes de assinatura
├── test_ciclo.py            # Testes de ciclo menstrual
├── test_diario.py           # Testes de diário de sintomas
├── test_treino.py           # Testes de treinos
├── test_perfil.py           # Testes de perfil
├── test_pontuacao.py        # Testes de pontuação
├── test_relatorio.py        # Testes de relatórios
├── test_fase_atual.py       # Testes de fase atual
├── test_ia_routes.py        # Testes da IA (LunIA)
└── test_geral.py            # Testes gerais e integração
```

## 🚀 Como Executar os Testes

### Opção 1: Script Interativo
```bash
python run_tests.py
```

### Opção 2:pytest Direto
```bash
# Todos os testes
pytest tests/ -v

# Teste específico
pytest tests/test_auth.py -v

# Teste específico com filtro
pytest tests/test_auth.py::TestAuthEndpoints::test_login_sucesso -v

# Com coverage
pytest tests/ --cov=app --cov-report=html
```

## 📊 Cobertura de Testes

### Endpoints Testados

#### Autenticação (`/auth`)
- ✅ `POST /register` - Registro de usuário
- ✅ `POST /validar-email` - Validação de email
- ✅ `POST /login` - Login
- ✅ `GET /me` - Informações do usuário logado
- ✅ `POST /solicitar-redefinicao-senha` - Solicitar redefinição
- ✅ `POST /redefinir-senha` - Redefinir senha

#### Assinatura (`/assinatura`)
- ✅ `GET /assinatura/status` - Status da assinatura
- ✅ `GET /assinatura/status-login` - Status otimizado
- ✅ `POST /assinatura/ativar` - Ativar assinatura
- ✅ `POST /assinatura/cancelar` - Cancelar assinatura

#### Ciclo (`/`)
- ✅ `POST /registrar-menstruacao` - Registrar menstruação
- ✅ `PUT /editar-menstruacao` - Editar menstruação
- ✅ `GET /fase-por-data` - Fase por data específica
- ✅ `GET /fase-ciclo` - Fase do ciclo atual

#### Diário (`/`)
- ✅ `POST /registrar-sintomas` - Registrar sintomas
- ✅ `GET /resumo-do-dia` - Resumo do dia

#### Treino (`/`)
- ✅ `GET /` - Obter treino do dia

#### Perfil (`/perfil`)
- ✅ `GET /perfil/perfil` - Obter perfil
- ✅ `PUT /perfil/perfil` - Atualizar perfil
- ✅ `GET /perfil/perfil/grafico` - Dados do gráfico
- ✅ `POST /perfil/sincronizar-fase` - Sincronizar fase

#### Pontuação (`/`)
- ✅ `GET /` - Obter pontuação

#### Relatório (`/relatorio`)
- ✅ `GET /mensal` - Relatório mensal

#### Fase Atual (`/fase-atual`)
- ✅ `GET /detalhes` - Detalhes da fase atual

#### IA (`/ia`)
- ✅ `POST /conversar` - Conversar com LunIA
- ✅ `GET /mensagem-entrada` - Mensagem de entrada

## 🎯 Tipos de Testes

### 1. Testes de Sucesso
Validam que os endpoints funcionam corretamente com dados válidos.

### 2. Testes de Erro
Validam que os endpoints retornam erros apropriados:
- `401` - Não autenticado
- `403` - Não autorizado
- `404` - Não encontrado
- `422` - Validação
- `500` - Erro do servidor

### 3. Testes de Validação
Validam que os dados de entrada são validados corretamente:
- Email inválido
- Senhas não conferem
- Campos faltando
- Formato de data inválido

### 4. Testes de Integração
Validam fluxos completos através de múltiplos endpoints.

### 5. Testes de Segurança
Validam proteções contra:
- SQL Injection
- XSS
- Injeção de código

### 6. Testes de Performance
Validam tempo de resposta dos endpoints.

## 📝 Fixtures Disponíveis

### Banco de Dados
- `db` - Sessão do banco de teste
- `client` - Cliente HTTP síncrono
- `async_client` - Cliente HTTP assíncrono

### Usuários
- `usuario_teste` - Usuário básico de teste
- `token_teste` - Token JWT válido
- `headers_auth` - Headers com autenticação
- `usuario_admin` - Usuário admin
- `token_admin` - Token JWT de admin
- `headers_admin` - Headers de admin

### Dados de Teste
- `dados_registro` - Dados válidos para registro
- `dados_login` - Dados válidos para login
- `dados_ciclo` - Dados válidos para ciclo
- `dados_diario` - Dados válidos para diário

## 🐛 Troubleshooting

### Erro: ModuleNotFoundError
```bash
# Instale as dependências
pip install -r requirements.txt
```

### Erro: Database não criado
```bash
# O banco de teste SQLite é criado automaticamente
# Verifique se tem permissão de escrita no diretório
```

### Testes lentos
```bash
# Execute apenas testes rápidos
pytest tests/ -v -m "not slow"
```

### Verbose output
```bash
# Mais detalhes nos testes
pytest tests/ -vv -s
```

## 📈 Relatórios

### Coverage HTML
```bash
pytest tests/ --cov=app --cov-report=html
# Abra: htmlcov/index.html
```

### JUnit XML
```bash
pytest tests/ --junitxml=report.xml
```

## 🔄 CI/CD

Os testes podem ser integrados em pipelines CI/CD:

```yaml
# Exemplo GitHub Actions
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest tests/ -v --cov=app
```

## 📊 Status Atual

- **Total de Testes:** 100+
- **Endpoints Cobertos:** 30+
- **Cobertura de Código:** ~70%
- **Tempo de Execução:** ~30 segundos

---

**Última atualização:** 18/03/2026
