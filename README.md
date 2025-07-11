# AgentCicle

Aplicativo para acompanhamento do ciclo menstrual com recursos de treino personalizado, diário de sintomas, e integração com IA.

## Funcionalidades

- Acompanhamento do ciclo menstrual
- Treinos personalizados para cada fase do ciclo
- Diário de sintomas
- Assistente de IA para dúvidas sobre saúde menstrual
- Sistema de gamificação com pontos por treinos realizados

## Nova Funcionalidade: Trial e Assinatura

O aplicativo agora implementa um sistema de trial de 7 dias e controle de assinatura:

- Novos usuários têm acesso a um período de avaliação de 7 dias
- Após o período de trial, é necessário assinar para continuar usando o app
- Banner informativo sobre o status do trial/assinatura é exibido no app
- Tela inicial de boas-vindas explicando o período de avaliação

### Campos adicionados no modelo de usuário

- `data_criacao_conta`: Data de criação da conta
- `data_fim_trial`: Data do fim do período de avaliação (data_criacao_conta + 7 dias)
- `assinatura_ativa`: Status da assinatura
- `data_inicio_assinatura`: Data de início da assinatura
- `data_fim_assinatura`: Data de término da assinatura

### Endpoints de assinatura

- `GET /assinatura/status`: Retorna o status da assinatura/trial do usuário
- `POST /assinatura/ativar`: Ativa a assinatura (simulação)
- `POST /assinatura/cancelar`: Cancela a assinatura (simulação)

### Testes

Para verificar as regras de negócio implementadas:

1. Crie uma nova conta para ver o trial ativo por 7 dias
2. Use o endpoint `/assinatura/status` para verificar o status
3. Use o endpoint `/assinatura/ativar` para simular a ativação da assinatura
4. Verifique os logs do servidor para ver os avisos de acesso

## Documentação adicional

- [Integração do Trial e Assinatura](./docs/integracao_trial_assinatura.md): Guia para integrar os componentes frontend com o backend
- [Guia de Polling no Frontend](./docs/guia_polling_frontend.md): Boas práticas para implementar polling correto no frontend e evitar problemas de desempenho