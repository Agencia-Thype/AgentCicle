# Guia para Implementação de Polling no Frontend

Este documento fornece orientações para implementar corretamente o polling (consultas periódicas) no frontend da aplicação para verificar o status de assinatura e outras informações que precisam ser atualizadas periodicamente.

## Princípio fundamental: Verificação APENAS após login completo

> **FUNDAMENTAL**: O status de assinatura/trial é verificado SOMENTE depois que o login foi completado com sucesso. Não há necessidade de verificação antes do login ou de polling contínuo durante o uso do aplicativo.
> 
> A sequência correta é:
> 1. Usuária faz login com credenciais
> 2. Backend verifica credenciais e retorna o token JWT
> 3. Na MESMA resposta de login, o backend já inclui o status completo da assinatura
> 4. Frontend armazena esse status localmente e usa essas informações para todas as decisões de UI

## Nova funcionalidade: Trial nunca retorna após assinatura premium

> **IMPORTANTE**: Implementamos uma nova regra de negócio: uma vez que a usuária tenha assinado o plano premium, o período de trial nunca mais será considerado, mesmo que a assinatura expire. Esta mudança garante que usuárias não possam alternar entre assinatura e trial para obter acesso estendido.

### Como identificar usuárias que já tiveram assinatura

O campo `jaTeveAssinatura` foi adicionado às respostas de status e indica se a usuária já teve uma assinatura premium ativa em algum momento. Este campo deve ser usado para determinar o comportamento da UI relacionado a promoções e ofertas.

```json
{
  "trialAtivo": false,
  "assinaturaAtiva": false,
  "temAcesso": false,
  "diasRestantesTrial": 0,
  "jaTeveAssinatura": true, // <-- Novo campo!
  "statusTipo": "expirado", // <-- Novo campo para facilitar lógica de UI
  "mensagem": "Sua assinatura expirou. Renove agora para continuar usando todos os recursos!"
}
```

### Valores do campo statusTipo

Para facilitar a lógica no frontend, adicionamos o campo `statusTipo` que pode ter os seguintes valores:

- `premium`: Usuária com assinatura ativa
- `trial`: Usuária em período de trial ativo
- `expirado`: Usuária que já teve assinatura premium, mas expirou
- `trial_expirado`: Usuária cujo trial expirou e nunca teve assinatura premium

## Problemas de Polling Excessivo

Identificamos um problema de múltiplas requisições simultâneas para a rota `/assinatura/status`, o que gera carga desnecessária no servidor e pode causar problemas de desempenho. Este comportamento é caracterizado por:

1. Múltiplas conexões fazendo requisições simultâneas à mesma rota
2. Requisições feitas em intervalos muito curtos (milissegundos)
3. Chamadas repetitivas mesmo sem mudança no estado da aplicação

## Boas Práticas para Polling

Ao implementar o polling no frontend, siga estas diretrizes:

### 1. Respeite os Cabeçalhos de Cache

A API agora inclui cabeçalhos `Cache-Control` que informam por quanto tempo os dados podem ser considerados válidos:

```javascript
// Exemplo em JavaScript
fetch('/api/assinatura/status')
  .then(response => {
    // Verifique se o cabeçalho de cache está presente
    const cacheControl = response.headers.get('Cache-Control');
    // Extraia o valor max-age
    const maxAge = cacheControl?.match(/max-age=(\d+)/)?.[1] || 30;
    
    return response.json();
  })
  .then(data => {
    // Armazene os dados e o timestamp de quando devem expirar
    const expireAt = Date.now() + (maxAge * 1000);
    localStorage.setItem('assinaturaStatus', JSON.stringify({
      data,
      expireAt
    }));
    
    // Atualize a interface
    updateUI(data);
  });
```

### 2. Use Intervalos Razoáveis

Implemente polling com intervalos razoáveis:

```javascript
// Exemplo de polling com intervalo razoável (30 segundos)
const POLLING_INTERVAL = 30000; // 30 segundos

function startPolling() {
  // Função de polling
  const checkStatus = () => {
    // Verifique se já temos dados em cache que ainda são válidos
    const cachedData = JSON.parse(localStorage.getItem('assinaturaStatus') || '{}');
    if (cachedData.expireAt && cachedData.expireAt > Date.now()) {
      // Use os dados em cache
      updateUI(cachedData.data);
      return;
    }
    
    // Se não tiver cache ou estiver expirado, busque novos dados
    fetch('/api/assinatura/status')
      .then(response => response.json())
      .then(data => {
        // Armazene os dados com tempo de expiração
        localStorage.setItem('assinaturaStatus', JSON.stringify({
          data,
          expireAt: Date.now() + POLLING_INTERVAL
        }));
        
        updateUI(data);
      })
      .catch(error => console.error('Erro ao buscar status:', error));
  };
  
  // Faça a primeira verificação imediatamente
  checkStatus();
  
  // Configure o intervalo de polling
  return setInterval(checkStatus, POLLING_INTERVAL);
}

// Inicie o polling quando necessário
const pollingId = startPolling();

// Pare o polling quando não for mais necessário
function stopPolling() {
  clearInterval(pollingId);
}
```

### 3. Use o Timestamp do Servidor

O endpoint `/assinatura/status` agora retorna um campo `timestamp` que pode ser usado para controle de atualização:

```javascript
let lastTimestamp = 0;

function fetchStatusIfNeeded() {
  fetch('/api/assinatura/status')
    .then(response => response.json())
    .then(data => {
      // Só atualize a interface se receber um timestamp mais recente
      if (data.timestamp > lastTimestamp) {
        lastTimestamp = data.timestamp;
        updateUI(data);
      }
    });
}
```

### 4. Implemente Exponential Backoff

Se uma requisição falhar, aumente gradualmente o intervalo entre tentativas:

```javascript
let retryCount = 0;
const MAX_RETRY_COUNT = 5;
const BASE_DELAY = 5000; // 5 segundos

function fetchWithRetry() {
  fetch('/api/assinatura/status')
    .then(response => {
      // Resetar contador se sucesso
      retryCount = 0;
      return response.json();
    })
    .then(data => updateUI(data))
    .catch(error => {
      console.error('Erro na requisição:', error);
      
      // Aumenta o contador de tentativas
      retryCount = Math.min(retryCount + 1, MAX_RETRY_COUNT);
      
      // Calcula o delay usando exponential backoff
      const delay = BASE_DELAY * Math.pow(2, retryCount);
      
      // Agenda nova tentativa após o delay
      setTimeout(fetchWithRetry, delay);
    });
}
```

### 5. Evite Múltiplas Instâncias de Polling

Certifique-se de que apenas uma instância da função de polling esteja ativa:

```javascript
let pollingInstance = null;

function ensureSinglePollingInstance() {
  // Se já existe uma instância, pare-a antes de criar uma nova
  if (pollingInstance) {
    clearInterval(pollingInstance);
  }
  
  // Cria nova instância
  pollingInstance = setInterval(fetchStatusIfNeeded, POLLING_INTERVAL);
}
```

## Verificação Única vs. Polling Contínuo

Uma abordagem mais eficiente para o status do trial/assinatura é fazer uma verificação única em momentos estratégicos, ao invés de polling contínuo:

### Verificação no Login

Não é mais necessário fazer uma requisição separada para obter o status. A resposta do login já traz tudo o que precisamos:

```javascript
// Durante o processo de login
async function realizarLogin(credenciais) {
  try {
    // 1. Autenticação que já retorna status completo
    const respostaLogin = await fetch('/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credenciais)
    });
    
    const dadosLogin = await respostaLogin.json();
    
    // 2. Extrair informações relevantes
    const { access_token, token_type, usuario, assinatura } = dadosLogin;
    
    // 3. Armazenar token para autenticação
    localStorage.setItem('token', access_token);
    localStorage.setItem('usuario', JSON.stringify(usuario));
    
    // 4. Armazenar status de assinatura que já vem com metadados de validade
    localStorage.setItem('dadosAssinatura', JSON.stringify(assinatura));
    
    // 5. Configurar UI com base no tipo de status
    configurarUIComBaseNoStatus(assinatura.statusTipo);
    
    return {
      sucesso: true,
      usuario,
      assinatura,
      mensagem: "Login realizado com sucesso"
    };
  } catch (erro) {
    console.error("Erro ao realizar login:", erro);
    return {
      sucesso: false,
      mensagem: "Falha ao realizar login"
    };
  }
}

// Função para ajustar a UI com base no status
function configurarUIComBaseNoStatus(statusTipo) {
  switch (statusTipo) {
    case 'premium':
      // Mostra elementos premium, esconde botões de upgrade
      showPremiumFeatures(true);
      hideUpgradeButtons();
      break;
    case 'trial':
      // Mostra elementos premium com badge "trial"
      showPremiumFeatures(true);
      showTrialBadge();
      showUpgradeButtons("Assine agora");
      break;
    case 'expirado':
      // Esconde elementos premium, mostra CTA de renovação
      showPremiumFeatures(false);
      showUpgradeButtons("Renove sua assinatura");
      break;
    case 'trial_expirado':
      // Esconde elementos premium, mostra CTA de primeira assinatura
      showPremiumFeatures(false);
      showUpgradeButtons("Assine agora");
      break;
  }
}
```

### Verificando o Status Quando Necessário

Esta função só deve ser usada em casos específicos, não como polling constante:

```javascript
// Função para verificar se o status armazenado já expirou
function statusExpirado() {
  // Recupera dados de assinatura armazenados no login
  const dadosArmazenados = JSON.parse(localStorage.getItem('dadosAssinatura') || '{}');
  
  // Se não houver dados, considere expirado
  if (!dadosArmazenados.verificadoEm || !dadosArmazenados.proximaVerificacao) {
    return true;
  }
  
  // Verifica se já passamos da data de próxima verificação
  const agora = new Date();
  const proximaVerificacao = new Date(dadosArmazenados.proximaVerificacao);
  
  return agora >= proximaVerificacao;
}

// Função para obter status atual - NÃO USE ESTA FUNÇÃO DURANTE O USO NORMAL DO APP!
// Esta função deve ser usada APENAS em casos excepcionais, como após pagamento ou ao abrir o app após dias
async function obterStatusAtualizado() {
  // 1. Verifica se o status armazenado ainda é válido
  if (!statusExpirado()) {
    // Se ainda for válido, use o que já está armazenado
    return JSON.parse(localStorage.getItem('dadosAssinatura'));
  }
  
  // 2. Se expirou, busque atualizado do servidor
  try {
    const token = localStorage.getItem('token');
    
    // Use a rota específica para verificação de status
    const resposta = await fetch('/assinatura/status-login', {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    // 3. Armazene o novo status
    const novoStatus = await resposta.json();
    localStorage.setItem('dadosAssinatura', JSON.stringify(novoStatus));
    
    // 4. Atualize a UI com base no novo status
    configurarUIComBaseNoStatus(novoStatus.statusTipo);
    
    console.log('Status atualizado em caso excepcional, não durante uso normal do app');
    
    return novoStatus;
  } catch (erro) {
    console.error("Erro ao atualizar status:", erro);
    // Em caso de erro, use o último status conhecido
    return JSON.parse(localStorage.getItem('dadosAssinatura') || '{}');
  }
}
```

### Momentos Estratégicos para Verificação

Verifique o status apenas nestes momentos:

1. **No login do usuário**
2. **Ao abrir o aplicativo depois de fechado**
3. **Ao navegar para telas que dependem do status (ex: funcionalidades premium)**
4. **Após uma transação de pagamento**
5. **Quando o usuário explicitamente solicitar (ex: botão "Atualizar status")**

Esta abordagem é muito mais eficiente que o polling contínuo e elimina o problema de múltiplas requisições simultâneas.

## Novos Endpoints no Backend para Otimização

O backend agora oferece novas APIs otimizadas para reduzir a necessidade de polling contínuo:

### 1. Status durante Login (`/login`)

A resposta do login agora inclui o status completo da assinatura:

```json
{
  "access_token": "eyJhbGciOiJIUzI1...",
  "token_type": "bearer",
  "usuario": {
    "id": 15,
    "nome": "Maria",
    "email": "maria@email.com"
  },
  "assinatura": {
    "trialAtivo": true,
    "assinaturaAtiva": false,
    "temAcesso": true,
    "diasRestantesTrial": 5,
    "dataFimTrial": "2025-07-18T10:30:00.000000",
    "mensagem": "Você está no período de testes gratuito. Restam 5 dias.",
    "verificadoEm": "2025-07-11T10:30:00.000000",
    "proximaVerificacao": "2025-07-12T10:30:00.000000",
    "tempoValidoSegundos": 86400,
    "jaTeveAssinatura": false,
    "statusTipo": "trial",
    "ultimoLogin": "2025-07-11T10:30:00.000000"
  }
}
```

O campo `proximaVerificacao` indica quando o frontend deve verificar o status novamente, eliminando a necessidade de polling frequente. O campo `jaTeveAssinatura` indica se a usuária já teve uma assinatura premium anteriormente, e o campo `statusTipo` facilita a lógica de UI.

### 2. Status para Login (`/assinatura/status-login`)

Este endpoint especializado retorna informações completas de status com metadados para cache:

```json
{
  "trialAtivo": true,
  "assinaturaAtiva": false,
  "temAcesso": true,
  "diasRestantesTrial": 5,
  "dataFimTrial": "2025-07-18T10:30:00.000000",
  "nome": "Maria",
  "email": "maria@email.com",
  "mensagem": "Você está no período de testes gratuito. Restam 5 dias.",
  "verificadoEm": "2025-07-11T10:30:00.000000",
  "proximaVerificacao": "2025-07-12T10:30:00.000000",
  "tempoValidoSegundos": 86400,
  "jaTeveAssinatura": false,
  "statusTipo": "trial",
  "ultimoLogin": "2025-07-11T10:30:00.000000"
}
```

Use este endpoint apenas quando precisar atualizar o status completo da assinatura fora do fluxo de login.

### Implementação Backend

O backend implementa:

1. **Cache inteligente**: Armazena resultados em memória para reduzir consultas ao banco de dados
2. **Cache adaptativo**: Diferentes tempos de cache baseados no status (trial: 1 dia, assinante: 7 dias)
3. **Metadados de controle**: Informações sobre quando verificar novamente
4. **Resposta única no login**: Elimina a necessidade de requisição adicional para status

## Conclusão

Implementar estas práticas de polling adequadas irá:

1. Reduzir significativamente a carga no servidor
2. Melhorar o desempenho do aplicativo frontend
3. Proporcionar uma experiência mais fluida ao usuário
4. Evitar problemas relacionados à múltiplas requisições simultâneas

## Recomendações para Cenários Específicos

### Ao Abrir o App Após Muito Tempo

Quando a usuária abre o app após um longo período sem uso:

```javascript
// No código de inicialização do app
async function iniciarAplicativo() {
  // Verificar se o token está presente (usuária logada)
  const token = localStorage.getItem('token');
  if (!token) {
    // Redirecionar para tela de login
    navigateToLogin();
    return;
  }
  
  // Verificar se o status expirou
  if (statusExpirado()) {
    // Buscar status atualizado
    await obterStatusAtualizado();
  }
  
  // Continuar inicialização do app
  inicializarComponentes();
}
```

### Ao Tentar Acessar Recurso Premium

Quando a usuária tenta acessar um recurso que requer assinatura:

```javascript
// Antes de mostrar conteúdo premium
function verificarAcessoRecurso() {
  // IMPORTANTE: Na maioria dos casos, basta usar o status armazenado durante o login
  const statusAssinatura = JSON.parse(localStorage.getItem('dadosAssinatura') || '{}');
  
  // Verifica se tem acesso com base nos dados do login
  // Raramente é necessário verificar se expirou ou atualizar - somente em casos excepcionais
  if (statusAssinatura.temAcesso) {
    // Mostrar conteúdo premium
    mostrarConteudoPremium();
  } else {
    // Mostrar tela de upgrade
    mostrarTelaUpgrade(statusAssinatura.statusTipo);
  }
}

// Apenas em casos muito raros, como ao abrir o app após vários dias sem logout
// você precisaria fazer algo assim:
async function verificarAcessoAposLongoTempo() {
  // Se o status armazenado expirou (vários dias sem fazer logout)
  if (statusExpirado()) {
    // Somente neste caso excepcional, atualize o status
    await obterStatusAtualizado();
  }
  
  // Na vasta maioria dos casos, use apenas os dados do login
  const statusAtual = JSON.parse(localStorage.getItem('dadosAssinatura') || '{}');
  return statusAtual.temAcesso;
}
```

### Após Completar um Pagamento

Após a usuária realizar um pagamento para assinar ou renovar:

```javascript
// Após confirmação de pagamento bem-sucedido
async function processarPagamentoConfirmado() {
  // Forçar atualização do status ignorando cache
  const resposta = await fetch('/assinatura/status-login?forceUpdate=true', {
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('token')}`
    }
  });
  
  const novoStatus = await resposta.json();
  
  // Atualizar o status armazenado
  localStorage.setItem('dadosAssinatura', JSON.stringify(novoStatus));
  
  // Atualizar UI para mostrar recursos premium
  configurarUIComBaseNoStatus(novoStatus.statusTipo);
  
  // Mostrar mensagem de sucesso
  mostrarMensagem("Assinatura ativada com sucesso!");
}
```

## FAQ - Perguntas Frequentes

### 1. Quando exatamente devo verificar o status da assinatura?
**R:** O status é verificado APENAS no momento do login. O backend já retorna o status completo junto com o token JWT. Você não precisa fazer uma requisição separada.

### 2. E se eu precisar verificar o status durante o uso do app?
**R:** Você não precisa! Use o status que já foi armazenado durante o login. Ele já contém todas as informações necessárias (trialAtivo, assinaturaAtiva, temAcesso, statusTipo, etc.).

### 3. O que fazer quando a usuária paga uma nova assinatura?
**R:** Apenas neste caso específico, você deve forçar uma atualização do status usando a função `obterStatusAtualizado()`. Isso garantirá que o status local reflita a nova assinatura.

### 4. Como saber se o trial ou a assinatura expirou durante o uso do app?
**R:** O status armazenado durante o login já inclui os metadados `verificadoEm` e `proximaVerificacao`. Você só precisa verificar novamente se a data atual for maior que `proximaVerificacao`. Mesmo assim, a usuária continuará tendo acesso até fazer logout, então isso raramente é necessário.

### 5. Preciso fazer polling para verificar se a assinatura mudou?
**R:** Absolutamente não! O polling é desnecessário e causa sobrecarga no servidor. O status só precisa ser verificado no login.

### 6. E se a usuária ficar muito tempo no app sem fazer logout?
**R:** Nos raros casos onde a usuária fica com o app aberto por vários dias, você pode verificar se o `statusExpirado()` é verdadeiro e, apenas nesse caso, chamar `obterStatusAtualizado()`.

## Fluxo de Transição entre Trial e Premium

O sistema implementa as seguintes regras para transições entre trial e premium:

### Regras implementadas:

1. **Novo registro**: Usuária recebe 7 dias de trial automaticamente após validar o email.

2. **Durante o trial**: 
   - Se a usuária assinar o plano premium, o trial é desconsiderado.
   - O campo `jaTeveAssinatura` é definido como `true` permanentemente.

3. **Após assinatura premium**:
   - Mesmo se a assinatura expirar, o trial nunca será reconsiderado.
   - O status da usuária será `expirado` (não `trial_expirado`).

4. **Renovação**:
   - Se a usuária renovar uma assinatura expirada, o campo `jaTeveAssinatura` permanece `true`.

### Exemplo de transições de status:

```
Novo registro → validação de email → trial ativo (7 dias) → 
  → [assina premium] → assinatura ativa → 
    → [expira assinatura] → assinatura expirada (nunca volta para trial)
```

### Recomendações de UI:

Com base no campo `statusTipo`, mostre diferentes mensagens e CTA (Call to Action):

- `trial`: "Você está no período gratuito. Restam X dias. Assine agora para não perder o acesso!"
- `premium`: "Você possui acesso premium! Aproveite todos os recursos."
- `expirado`: "Sua assinatura expirou. Renove para continuar acessando todos os recursos."
- `trial_expirado`: "Seu período gratuito terminou. Assine agora para acessar todos os recursos."

Esta lógica elimina a possibilidade de usuárias "ganhar" múltiplos períodos de trial e garante que, uma vez que tenha experimentado o plano premium, a usuária seja incentivada a renovar a assinatura.

## Usando o status armazenado para decisões de UI

Após o login bem-sucedido, o status da assinatura já está disponível e armazenado localmente. Use essas informações para todas as decisões de UI no aplicativo:

```javascript
// Função para verificar acesso a um recurso premium
function verificarAcessoRecurso() {
  // Recupera o status armazenado durante o login
  const statusAssinatura = JSON.parse(localStorage.getItem('dadosAssinatura') || '{}');
  
  // Decisão baseada no status armazenado, sem consulta ao servidor
  if (statusAssinatura.temAcesso) {
    // Tem acesso (trial ativo ou assinatura ativa)
    return true;
  } else {
    // Não tem acesso
    return false;
  }
}

// Função para mostrar/esconder elementos da UI com base no status
function ajustarUI() {
  // Recupera o status armazenado durante o login
  const statusAssinatura = JSON.parse(localStorage.getItem('dadosAssinatura') || '{}');
  
  // Elementos premium
  const elementosPremium = document.querySelectorAll('.premium-feature');
  // Mensagens de upgrade
  const mensagemUpgrade = document.getElementById('upgrade-message');
  
  if (statusAssinatura.temAcesso) {
    // Mostra recursos premium
    elementosPremium.forEach(el => el.classList.remove('hidden'));
    
    // Esconde mensagem de upgrade
    mensagemUpgrade.classList.add('hidden');
    
    // Se for trial, mostra badge de trial
    if (statusAssinatura.statusTipo === 'trial') {
      mostrarTrialBadge(statusAssinatura.diasRestantesTrial);
    }
  } else {
    // Esconde recursos premium
    elementosPremium.forEach(el => el.classList.add('hidden'));
    
    // Mostra mensagem de upgrade apropriada
    mensagemUpgrade.classList.remove('hidden');
    mensagemUpgrade.textContent = statusAssinatura.mensagem;
  }
}
```

O mais importante é entender que **todas estas decisões são baseadas no status armazenado durante o login**, sem precisar consultar o servidor novamente.

## Fluxo de verificação durante o login

Para esclarecer como o processo acontece, aqui está o fluxo completo:

1. **Usuária faz login**: O frontend envia credenciais para `/login`
2. **Backend processa o login**: Além de autenticar a usuária, o backend:
   - Verifica o status de assinatura/trial no banco de dados
   - Calcula se é trial ativo, assinatura ativa, ou nenhum dos dois
   - Determina se a usuária já teve assinatura premium anteriormente
   - Adiciona todas essas informações na resposta do login

3. **Frontend recebe resposta de login**: A resposta contém:
   - Token de autenticação
   - Dados básicos da usuária
   - Status completo de assinatura/trial com metadados

4. **Frontend armazena localmente**: 
   - O token JWT para autenticação
   - O status de assinatura com seus metadados de validade
   - A data de quando o status foi verificado
   - A data de quando o status deve ser verificado novamente

5. **Durante o uso do app**: 
   - O frontend usa o status armazenado localmente
   - Não há necessidade de consultar o status a cada ação
   - O frontend apenas verifica se o status armazenado ainda é válido

6. **Quando o status expira**:
   - Apenas neste momento o frontend faz uma nova consulta a `/assinatura/status-login`
   - Armazena o novo status localmente
   - Continua usando este status até expirar novamente

Este fluxo simplificado reduz drasticamente o número de requisições ao servidor, melhorando a performance e a experiência do usuário.
