# Política de Privacidade — AgentCicle

**Última atualização:** [DATA]
**Versão:** 1.0

> **RASCUNHO PARA REVISÃO JURÍDICA.** Este documento foi redigido a partir de uma auditoria do código do aplicativo e descreve com precisão o tratamento de dados hoje implementado. Ele **não substitui revisão por advogado(a)**, especialmente quanto a dados pessoais sensíveis de saúde, que a LGPD trata com rigor específico. Preencha os campos em [COLCHETES] antes de publicar.

---

## 1. Quem somos

O AgentCicle é um aplicativo de acompanhamento do ciclo menstrual com treinos personalizados, diário de sintomas e assistente virtual.

- **Controlador dos dados:** [RAZÃO SOCIAL COMPLETA], CNPJ [NÚMERO]
- **Endereço:** [ENDEREÇO COMPLETO]
- **Contato para assuntos de privacidade:** [E-MAIL DE CONTATO]
- **Encarregado(a) pelo tratamento de dados (DPO):** [NOME E E-MAIL]

Ao criar uma conta e usar o aplicativo, você concorda com esta Política.

---

## 2. Aviso importante: tratamos dados sensíveis de saúde

Informações sobre seu ciclo menstrual, sintomas, sentimentos, peso e condição física são classificadas pela **Lei Geral de Proteção de Dados (Lei 13.709/2018, art. 5º, II)** como **dados pessoais sensíveis**.

Isso significa que:

- O tratamento desses dados depende do **seu consentimento específico e destacado** (art. 11, I), dado no momento do cadastro;
- Você pode **retirar esse consentimento a qualquer momento**, excluindo sua conta pelo próprio aplicativo (ver seção 7);
- **Não vendemos, alugamos nem compartilhamos esses dados para fins publicitários, de marketing ou com corretores de dados.** Em nenhuma hipótese.

---

## 3. Quais dados coletamos

### 3.1 Dados de cadastro e identificação

| Dado | Origem |
|---|---|
| Nome | Informado por você, ou pelo Google/Apple no login social |
| E-mail | Informado por você, ou pelo Google/Apple no login social |
| Identificador da conta (Firebase UID) | Gerado automaticamente na criação da conta |
| Data de criação da conta | Gerada automaticamente |

Se você usar o **Sign in with Apple** e escolher a opção "Ocultar meu e-mail", receberemos apenas um endereço de redirecionamento anônimo da Apple. Nunca teremos acesso ao seu e-mail real.

**Não coletamos e não temos acesso à sua senha.** A autenticação é feita integralmente pelo Firebase Authentication (Google). Nossos servidores recebem apenas um token de verificação.

### 3.2 Dados de saúde e do ciclo (sensíveis)

| Dado | Como é usado |
|---|---|
| Data da última menstruação | Cálculo da fase atual do ciclo |
| Duração do ciclo | Cálculo da fase atual do ciclo |
| Altura, peso atual e histórico de peso | Cálculo de IMC e acompanhamento de evolução |
| Objetivo de treino | Personalização das recomendações |
| Diário de sintomas: sentimentos e observações (texto livre) | Acompanhamento pessoal e contexto para o assistente |
| Treinos realizados, percentual concluído e pontuação | Histórico de progresso e gamificação |
| Progresso nos exercícios de Kegel (nível, séries, conclusão) | Acompanhamento de evolução |

### 3.3 Conversas com a assistente virtual (Lunia)

Armazenamos as perguntas que você envia à assistente, as respostas geradas e o contexto associado (fase do ciclo, percentual de treinos, tema da conversa).

### 3.4 Dados técnicos

Registros de acesso ao servidor contendo endereço IP, tipo de dispositivo e navegador (user agent), horário e rota acessada. São mantidos para segurança, diagnóstico de falhas e cumprimento do **art. 15 do Marco Civil da Internet**.

### 3.5 O que NÃO coletamos

- Localização geográfica
- Contatos, fotos, arquivos ou câmera
- Dados de pagamento (o aplicativo é gratuito — ver seção 9)
- Identificadores de publicidade ou rastreamento entre aplicativos

---

## 4. Por que tratamos seus dados

| Finalidade | Base legal (LGPD) |
|---|---|
| Criar e manter sua conta | Execução de contrato (art. 7º, V) |
| Calcular fases do ciclo e personalizar treinos | Consentimento para dado sensível (art. 11, I) |
| Registrar seu diário de sintomas e progresso | Consentimento para dado sensível (art. 11, I) |
| Gerar respostas da assistente virtual | Consentimento para dado sensível (art. 11, I) |
| Segurança, prevenção a fraude e diagnóstico | Legítimo interesse (art. 7º, IX) |
| Guardar registros de acesso | Obrigação legal (art. 7º, II) |

**Não usamos seus dados para publicidade, criação de perfil comercial ou decisões automatizadas que produzam efeitos jurídicos sobre você.**

---

## 5. Com quem compartilhamos

Compartilhamos o mínimo necessário, apenas com prestadores de serviço que sustentam o funcionamento do aplicativo.

### 5.1 Google (Firebase Authentication)

Recebe seu e-mail e nome para autenticar seu acesso.
Política: https://firebase.google.com/support/privacy

### 5.2 Apple (Sign in with Apple)

Apenas se você optar por esse método de login. A Apple nos informa um identificador e, conforme sua escolha, seu e-mail real ou um endereço anônimo.
Política: https://www.apple.com/legal/privacy/

### 5.3 OpenAI (assistente virtual Lunia)

Quando você conversa com a assistente, enviamos à OpenAI:

- Sua pergunta (texto livre que você escreveu);
- A fase atual do seu ciclo;
- Seu percentual de treinos concluídos;
- Sentimentos que você registrou no diário nos últimos dias.

**Não enviamos seu nome, e-mail, identificador de conta ou qualquer dado que permita identificá-la diretamente.** A OpenAI recebe o conteúdo de forma pseudonimizada.

Atenção: como a pergunta é um campo de texto livre, evite escrever nele informações que identifiquem você ou outras pessoas.
Política: https://openai.com/policies/privacy-policy

### 5.4 Provedor de hospedagem e banco de dados

[NOME DO PROVEDOR], que armazena os dados em servidores localizados em [PAÍS/REGIÃO]. O provedor não acessa o conteúdo dos dados.

### 5.5 Autoridades públicas

Somente mediante ordem judicial ou requisição legal válida.

---

## 6. Transferência internacional

Google, Apple e OpenAI processam dados em servidores fora do Brasil, incluindo os Estados Unidos. Essas transferências ocorrem nos termos do **art. 33 da LGPD**, com base nas cláusulas contratuais e garantias oferecidas por esses fornecedores.

---

## 7. Seus direitos

A LGPD (art. 18) garante a você o direito de:

- **Confirmar** se tratamos seus dados e **acessá-los**;
- **Corrigir** dados incompletos, inexatos ou desatualizados;
- **Solicitar anonimização, bloqueio ou eliminação** de dados desnecessários ou tratados em desconformidade com a lei;
- **Solicitar a portabilidade** dos dados a outro fornecedor;
- **Revogar o consentimento** e solicitar a eliminação dos dados;
- **Ser informada** sobre com quem compartilhamos seus dados;
- **Opor-se** a um tratamento feito com base em legítimo interesse.

### Como exercer

**Excluir sua conta e todos os seus dados:** dentro do aplicativo, acesse **Perfil → Excluir minha conta**. A exclusão é imediata, permanente e apaga:

- Seu cadastro e perfil;
- Todo o histórico do ciclo e do diário de sintomas;
- Todos os treinos realizados e o progresso de Kegel;
- O histórico de peso;
- Todas as conversas com a assistente virtual;
- Sua conta de autenticação no Firebase.

Se você usou o Sign in with Apple, também revogamos a autorização concedida ao aplicativo na sua conta Apple.

**Esta ação não pode ser desfeita e não há backup de recuperação para você.**

**Demais solicitações:** escreva para [E-MAIL DE CONTATO]. Responderemos em até 15 (quinze) dias.

---

## 8. Por quanto tempo guardamos

| Dado | Prazo |
|---|---|
| Dados de conta, ciclo, treinos e conversas | Enquanto sua conta existir |
| Todos os dados acima, após exclusão da conta | Eliminados imediatamente |
| Registros de acesso (logs) | 6 meses, conforme art. 15 do Marco Civil |
| Dados sob obrigação legal ou processo judicial | Pelo prazo exigido pela norma aplicável |

---

## 9. Aplicativo gratuito

O AgentCicle é oferecido **gratuitamente**, sem assinaturas, compras dentro do aplicativo ou anúncios. Não coletamos dados de pagamento.

Caso passemos a oferecer recursos pagos no futuro, esta Política será atualizada e você será informada antes de qualquer cobrança.

---

## 10. Idade mínima

O AgentCicle **não se destina a menores de 13 anos** e não coletamos intencionalmente dados dessa faixa etária.

Adolescentes entre 13 e 18 anos devem usar o aplicativo com ciência e consentimento de pai, mãe ou responsável legal, conforme o **art. 14 da LGPD**.

Se tomarmos conhecimento de que coletamos dados de uma criança sem o consentimento devido, eliminaremos essas informações.

---

## 11. Segurança

Adotamos medidas técnicas e administrativas para proteger seus dados:

- Toda a comunicação entre o aplicativo e nossos servidores é criptografada (HTTPS);
- A autenticação usa tokens verificados a cada requisição, com expiração automática;
- Cada usuária acessa exclusivamente os próprios dados — o servidor identifica a conta pelo token, nunca por um parâmetro enviado pelo aplicativo;
- Não armazenamos senhas.

Nenhum sistema é totalmente imune. Em caso de incidente de segurança com risco relevante a você, comunicaremos você e a **ANPD** conforme o art. 48 da LGPD.

---

## 12. Alterações nesta Política

Podemos atualizar esta Política. Mudanças significativas serão comunicadas pelo aplicativo ou por e-mail antes de entrarem em vigor. A data da última atualização está no topo do documento.

---

## 13. Contato

Dúvidas, solicitações ou reclamações sobre privacidade:

- **E-mail:** [E-MAIL DE CONTATO]
- **Encarregado(a) (DPO):** [NOME E E-MAIL]

Você também pode apresentar reclamação à **Autoridade Nacional de Proteção de Dados (ANPD)** — https://www.gov.br/anpd
