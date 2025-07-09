# Integração da Funcionalidade de Trial e Assinatura

Este documento descreve como integrar as funcionalidades de trial e assinatura no aplicativo Cíclica.

## Componentes Frontend

### 1. TrialBanner.js

Este componente exibe um banner informativo sobre o status do trial ou assinatura da usuária. 
O banner mostra informações diferentes com base no status:

- **Trial Ativo**: Mostra quantos dias restam no período de trial
- **Assinatura Ativa**: Confirma que a usuária possui uma assinatura ativa
- **Trial Expirado**: Avisa que o período de teste acabou e incentiva a assinar

**Como integrar:**

```jsx
// No seu componente de layout principal
import TrialBanner from './components/TrialBanner';

function MainLayout({ children }) {
  return (
    <div className="app-container">
      <TrialBanner />
      <Header />
      <main>{children}</main>
      <Footer />
    </div>
  );
}
```

### 2. TrialSplashScreen.js

Este componente exibe uma tela de boas-vindas quando uma usuária faz login pela primeira vez ou quando inicia um novo período de trial.

**Como integrar:**

```jsx
// No seu componente de autenticação ou dashboard
import { useState, useEffect } from 'react';
import TrialSplashScreen from './components/TrialSplashScreen';

function Dashboard() {
  const [showSplash, setShowSplash] = useState(false);
  const [trialDays, setTrialDays] = useState(7);
  
  useEffect(() => {
    // Verificar se é o primeiro login ou se o usuário acabou de iniciar um trial
    const checkFirstLogin = async () => {
      try {
        const token = localStorage.getItem('token');
        if (!token) return;
        
        const response = await axios.get('/assinatura/status', {
          headers: { Authorization: `Bearer ${token}` }
        });
        
        // Se é um trial recém-iniciado e nunca mostrou o splash antes
        const splashShown = localStorage.getItem('trialSplashShown');
        if (response.data.trialAtivo && !splashShown) {
          setTrialDays(response.data.diasRestantesTrial);
          setShowSplash(true);
          // Marcar como já mostrado
          localStorage.setItem('trialSplashShown', 'true');
        }
      } catch (err) {
        console.error('Erro ao verificar status:', err);
      }
    };
    
    checkFirstLogin();
  }, []);
  
  const handleCloseSplash = () => {
    setShowSplash(false);
  };
  
  return (
    <div>
      {showSplash && (
        <TrialSplashScreen 
          onClose={handleCloseSplash} 
          daysRemaining={trialDays} 
        />
      )}
      
      {/* Resto do dashboard */}
      <h1>Dashboard</h1>
      {/* ... */}
    </div>
  );
}
```

## Integração com Backend

### 1. Verificação de Status

Para exibir corretamente o status do trial/assinatura, faça uma chamada para o endpoint `/assinatura/status` ao carregar a aplicação:

```javascript
async function fetchSubscriptionStatus() {
  const token = localStorage.getItem('token');
  if (!token) return null;
  
  try {
    const response = await axios.get('/assinatura/status', {
      headers: { Authorization: `Bearer ${token}` }
    });
    return response.data;
  } catch (error) {
    console.error('Erro ao buscar status da assinatura:', error);
    return null;
  }
}
```

### 2. Resposta a Erros de Acesso

Quando o backend retornar um erro 403 (que acontecerá quando os bloqueios forem ativados), exiba uma mensagem incentivando a assinatura:

```javascript
// Configuração global do Axios para interceptar erros 403
axios.interceptors.response.use(
  response => response,
  error => {
    if (error.response && error.response.status === 403) {
      // Mostrar modal ou redirecionar para página de assinatura
      showSubscriptionRequiredModal();
      // ou: window.location.href = '/assinar';
    }
    return Promise.reject(error);
  }
);

function showSubscriptionRequiredModal() {
  // Implementar um modal informando que a assinatura é necessária
  // ...
}
```

## Preparação para Testes

Para testar diferentes cenários, você pode utilizar os seguintes endpoints:

1. **Ver Status Atual**: `GET /assinatura/status`
2. **Simular Ativação de Assinatura**: `POST /assinatura/ativar?duracao_meses=X`
3. **Simular Cancelamento**: `POST /assinatura/cancelar`

## Lembre-se

- Por enquanto, o app continua funcional sem bloqueios reais (apenas logs no backend)
- A UI já deve mostrar claramente o status do trial/assinatura
- Os endpoints já estão preparados para implementar os bloqueios quando necessário
