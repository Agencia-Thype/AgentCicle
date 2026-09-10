# Formulários de privacidade das lojas — respostas do AgentCicle

Documento de apoio para preencher o **Data Safety** (Google Play) e as **Privacy
Nutrition Labels** (App Store). As respostas abaixo refletem o que o código faz
hoje, auditado em [DATA].

> **Regra de ouro:** o que você declara aqui precisa bater com a
> [Política de Privacidade](./politica-de-privacidade.md) e com o comportamento
> real do app. Divergência entre os três é uma das causas mais comuns de
> reprovação e de remoção posterior do app.

---

## Google Play — Data Safety

### O app coleta ou compartilha dados do usuário?
**Sim.**

### Os dados são criptografados em trânsito?
**Sim** (HTTPS em todas as requisições).

### O usuário pode solicitar a exclusão dos dados?
**Sim.** Fornecer o caminho: **Perfil → Excluir minha conta**, dentro do app.

O Play também pede uma **URL de exclusão de conta** acessível fora do app.
Providencie uma página em [URL] explicando o caminho no app e oferecendo o
e-mail [E-MAIL DE CONTATO] como alternativa.

### Tipos de dados a declarar

| Categoria | Tipo | Coletado | Compartilhado | Obrigatório | Finalidade |
|---|---|---|---|---|---|
| Informações pessoais | Nome | Sim | Não | Sim | Funcionalidade do app |
| Informações pessoais | Endereço de e-mail | Sim | Não | Sim | Funcionalidade do app; gerenciamento de conta |
| Informações pessoais | IDs do usuário | Sim | Não | Sim | Funcionalidade do app; gerenciamento de conta |
| Saúde e fitness | Informações de saúde | Sim | **Sim** | Sim | Funcionalidade do app; personalização |
| Saúde e fitness | Informações de fitness | Sim | **Sim** | Sim | Funcionalidade do app; personalização |
| Mensagens | Outras mensagens no app | Sim | **Sim** | Não | Funcionalidade do app |
| Registros do app | Registros de falhas e diagnóstico | Sim | Não | Não | Análises; segurança |

**Sobre os três "Sim" em compartilhamento:** o Google define compartilhamento
como transferir dados a terceiros. O envio de fase do ciclo, sentimentos do
diário e das mensagens à OpenAI se enquadra, **mesmo sendo pseudonimizado**.
Declarar "Não" aqui seria uma declaração falsa.

### Não declarar (o app não coleta)
Localização, informações financeiras, contatos, calendário, fotos e vídeos,
arquivos e documentos, áudio, atividade de navegação, histórico de buscas.

### Práticas de segurança
- Dados criptografados em trânsito: **Sim**
- Usuário pode pedir exclusão: **Sim**
- Segue a Política de Famílias do Google Play: **Não** (app não é direcionado a crianças)

---

## App Store — Privacy Nutrition Labels

Preenchido em App Store Connect → seu app → **Privacidade do app**.

### Dados vinculados à identidade do usuário

Todos os itens abaixo ficam associados à conta, portanto entram como
**"Dados vinculados a você"**:

| Categoria da Apple | Item | Finalidade |
|---|---|---|
| Informações de contato | Nome | Funcionalidade do app |
| Informações de contato | Endereço de e-mail | Funcionalidade do app |
| Identificadores | ID do usuário | Funcionalidade do app |
| Saúde e fitness | Saúde | Funcionalidade do app |
| Saúde e fitness | Fitness | Funcionalidade do app |
| Conteúdo do usuário | Outro conteúdo do usuário | Funcionalidade do app |
| Diagnóstico | Dados de falhas / desempenho | Funcionalidade do app |

### Perguntas de rastreamento

- **Usado para rastrear você:** **Não**, em nenhum item.
- **Usado para publicidade de terceiros / marketing / analytics de terceiros:** **Não**.

O app não possui SDK de publicidade nem identificadores de rastreamento, então
**não é necessário** implementar o App Tracking Transparency (ATT).

### Categoria de idade
Classificação sugerida: **12+**, por conteúdo relacionado a saúde sexual e
reprodutiva. Confirme no questionário de classificação etária da Apple.

---

## Checklist antes de submeter

- [ ] Política de privacidade publicada em URL pública e estável
- [ ] Mesma URL informada nos dois consoles (Play Console e App Store Connect)
- [ ] Placeholders em [COLCHETES] preenchidos nos dois documentos
- [ ] Documento revisado por advogado(a)
- [ ] URL de exclusão de conta criada (exigência do Google Play)
- [ ] Data de "última atualização" preenchida
- [ ] Tela de cadastro exibe consentimento destacado para dados sensíveis de saúde e link para a política
- [ ] Respostas dos formulários conferem com a política publicada

---

## Pendência de produto

A política afirma que o consentimento para dados sensíveis é coletado no
cadastro (art. 11, I da LGPD). **Isso ainda não existe na tela de cadastro.**

Para a afirmação ser verdadeira, a tela de registro precisa de um aceite
destacado — separado dos termos gerais — mencionando explicitamente o
tratamento de dados de saúde, com link para esta política. Sem isso, a base
legal declarada não se sustenta.
