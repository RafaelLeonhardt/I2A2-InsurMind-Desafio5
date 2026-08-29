# Alternar o Contexto Demonstrativo Specification

## Problem Statement

Hoje o frontend renderiza uma shell estática única (`App.tsx`), sempre na perspectiva do Segurado, com "Marina Costa" e dados fixos embutidos no JSX. As superfícies já implementadas (Prontidão, Restaurar dados sintéticos) não estão conectadas a nenhuma navegação real. Sem uma barra de contexto e um seletor de perfil funcionais, a pessoa demonstradora não consegue apresentar as duas perspectivas (Administrador e Segurado) de forma clara, nem provar que a alternância é só apresentação — nunca autenticação ou autorização.

## Goals

- [ ] A pessoa demonstradora alterna entre Administrador e Segurado a qualquer momento, por um seletor "Visualizar como", sem que isso pareça login ou controle de acesso.
- [ ] Toda superfície exibe uma barra de contexto (perfil, segurado ativo quando aplicável, data/hora de referência) e a faixa fixa "Ambiente educacional · Dados sintéticos · Sem envio real".
- [ ] A navegação lateral mostra somente as superfícies do perfil ativo; as duas superfícies administrativas já entregues (Prontidão, Restaurar dados sintéticos) e a Visão geral do Segurado ficam alcançáveis por ela.
- [ ] O perfil escolhido sobrevive a um reload via armazenamento local do navegador, sem criar sessão de identidade no backend.

## Out of Scope

Explicitamente excluído. Documentado para prevenir scope creep.

| Feature | Reason |
| --- | --- |
| Seletor de segurado (múltiplos segurados) | AC da História 1.4 exige operar de forma completa só com o segurado padrão; seletor fica para história futura quando houver mais de um segurado navegável. |
| Superfícies de Monitoramento, Regras, Alertas, Comunicados, Meus Dados, Segurados sintéticos | Pertencem a épicos 2+; ainda não implementadas. Antecipá-las violaria a restrição de "não antecipar entidades ou comportamentos dos épicos posteriores" (`epic-1-context.md`). |
| Cliente HTTP gerado por OpenAPI/`openapi-typescript` | Entra na História 1.5; esta história usa `fetch` direto, seguindo o precedente de AD-003. |
| Autenticação, autorização ou qualquer controle de acesso real | Fora do MVP por definição de produto (FR44); a troca de perfil é só apresentação. |

---

## Assumptions & Open Questions

Toda ambiguidade foi resolvida ou registrada aqui — nada fica sem definição.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Composição da navegação do Administrador | Dois itens de navegação: "Prontidão" e "Restaurar dados sintéticos" | Decidido em discussão com o usuário; evita inventar uma superfície "Administração" não pedida pelo épico | y |
| Perfil padrão sem preferência salva | Administrador | Decidido em discussão com o usuário | y |
| Modal "Restaurar dados sintéticos" aberto durante a troca de perfil | Fecha automaticamente ao trocar de perfil | Decidido em discussão com o usuário; o modal não tem formulário com dados a perder | y |
| Origem do nome do segurado padrão exibido na barra de contexto | Buscar pela API real (novo endpoint mínimo de leitura), nunca hardcoded no frontend | Segue o padrão já estabelecido no projeto (AD-003: mesmo antes da OpenAPI-typescript, o frontend sempre chama a API real; nunca fixture) e evita reintroduzir um nome fixo como o "Marina Costa" atual | y |
| Identidade do segurado padrão | O primeiro segurado semeado, `identificador_demonstracao("segurado/chuva-elegivel")`, nome "Pessoa Segurada Sintética DEMO-001" | Único segurado sintético já elegível para o cenário de chuva no seed (`semeador.py`); nome já é inequivocamente fictício, satisfaz o AC sem exigir seletor | y |
| Mecanismo de "próxima ação válida" quando o contexto está ausente/incompatível | Mensagem explicando a inconsistência + botão que retorna à Visão geral do perfil ativo vigente | Único destino sempre válido dado que cada perfil tem uma superfície inicial estável nesta história | y |
| Biblioteca/mecanismo de navegação entre superfícies (SPA router vs. estado local) | Decisão de arquitetura, não de produto | Cabe à fase de Design, não a esta especificação | n/a — Design decide |
| Componente visual exato do seletor "Visualizar como" | Segue `{components.seletor-demonstrativo}` do `DESIGN.md` (rótulo visível, ícone auxiliar) | Já especificado nos artefatos de design; não é uma decisão de produto em aberto | y |
| Verificação automatizada do "indicador de foco de 3 px" (CTX-18) | O valor exato de 3 px é garantido pela regra CSS `button:focus-visible, a:focus-visible, main:focus-visible { outline: 3px solid var(--amber) }` (`src/frontend/src/App.css:17`) e validado por revisão visual/UAT, não por um teste automatizado de `getComputedStyle` | `jsdom` (ambiente de teste do Vitest, sem `css: true`) não aplica o cascateamento real de folhas de estilo externas; um teste de `getComputedStyle` sobre esse valor não distinguiria uma regressão real de um falso positivo/negativo, violando o critério "non-shallow" da revisão de adequação de testes. Os testes automatizados cobrem a ordem de tabulação e a ativação por `Enter`/clique (a parte comportamental do AC); o valor "3 px" em si fica sob responsabilidade da revisão de design/UAT | y |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Alternar entre Administrador e Segurado ⭐ MVP

**User Story**: Como pessoa demonstradora, quero alternar entre as visões de Administrador e Segurado, para apresentar as duas perspectivas sem confundi-las com identidades ou permissões reais.

**Why P1**: É o próprio objeto da História 1.4; sem alternância funcional não há demonstração das duas perspectivas.

**Acceptance Criteria** (each line is one EARS pattern):

1. O sistema SHALL exibir, em toda superfície, uma barra de contexto com o perfil visualizado, a data e hora de referência e o segurado sintético ativo quando aplicável. <!-- ubiquitous -->
2. O sistema SHALL exibir permanentemente, em toda superfície, a faixa "Ambiente educacional · Dados sintéticos · Sem envio real", sem oferecer nenhum controle que a feche. <!-- ubiquitous -->
3. WHEN a pessoa demonstradora, estando na visão de Administrador, selecionar "Visualizar como Segurado" THEN o sistema SHALL apresentar na navegação somente a superfície "Visão geral" prevista para o perfil Segurado. <!-- event-driven -->
4. WHEN a alternância de perfil ocorrer THEN o sistema SHALL limpar qualquer seleção ou estado administrativo transitório incompatível com o novo perfil (incluindo fechar o modal "Restaurar dados sintéticos" se estiver aberto), sem alterar nenhum dado persistido no backend. <!-- event-driven -->
5. WHEN a pessoa demonstradora, estando na visão de Segurado, selecionar "Visualizar como Administrador" THEN o sistema SHALL apresentar na navegação somente as superfícies "Prontidão" e "Restaurar dados sintéticos". <!-- event-driven -->
6. O sistema SHALL NUNCA descrever, em nenhum texto de interface, a troca de perfil como login, autenticação, autorização ou elevação de privilégio. <!-- ubiquitous -->

**Independent Test**: Abrir a aplicação, alternar Administrador → Segurado → Administrador pelo seletor "Visualizar como" e observar a navegação, a barra de contexto e a ausência de qualquer linguagem de login em cada troca.

---

### P1: Apresentar o segurado sintético padrão

**User Story**: Como pessoa demonstradora, quero que a visão de Segurado sempre mostre o segurado sintético padrão, para operar a demonstração sem precisar escolher entre vários segurados.

**Why P1**: É um AC explícito da História 1.4 e pré-condição para a barra de contexto fazer sentido na visão de Segurado.

**Acceptance Criteria**:

1. WHEN a visão de Segurado for aberta THEN o sistema SHALL buscar e exibir, via API real, o nome inequivocamente fictício do segurado sintético padrão ("Pessoa Segurada Sintética DEMO-001") como segurado ativo na barra de contexto. <!-- event-driven -->
2. O sistema SHALL operar de forma completa com o segurado sintético padrão nesta história, sem exigir um seletor de outros segurados. <!-- ubiquitous -->
3. IF a busca do segurado sintético padrão falhar THEN o sistema SHALL exibir, na barra de contexto, um estado de indisponibilidade com causa e uma ação de nova tentativa, em vez de mostrar um nome fixo ou vazio. <!-- unwanted-behavior -->

**Independent Test**: Abrir a visão de Segurado com o backend no ar e confirmar que o nome exibido veio de uma chamada de rede real (não de uma string fixa no bundle); derrubar o endpoint e confirmar o estado de indisponibilidade.

---

### P1: Persistir o perfil localmente sem criar identidade

**User Story**: Como pessoa demonstradora, quero que o perfil escolhido sobreviva a um reload da página, para não ter que reconfigurar a apresentação a cada atualização, sem que isso crie uma sessão de identidade real.

**Why P1**: AC explícito da História 1.4; sustenta demonstrações longas com múltiplos reloads.

**Acceptance Criteria**:

1. WHEN o perfil for alternado THEN o sistema SHALL gravar o perfil ativo em armazenamento local do navegador (`localStorage`), sem chamar nenhum endpoint de autenticação ou sessão. <!-- event-driven -->
2. WHEN a página for atualizada (reload) THEN o sistema SHALL restaurar o perfil gravado em `localStorage`, usando "Administrador" como padrão quando não houver valor salvo. <!-- event-driven -->
3. O sistema SHALL garantir que nenhuma decisão, regra de negócio ou verificação de permissão no backend leia ou dependa do valor de perfil armazenado no frontend. <!-- ubiquitous -->

**Independent Test**: Alternar para Segurado, recarregar a página (F5) e confirmar que a visão de Segurado permanece ativa; inspecionar as requisições de rede e confirmar que nenhuma delas envia o perfil como credencial ou token de sessão.

---

### P1: Bloquear contexto ausente ou incompatível

**User Story**: Como pessoa demonstradora, quero que a interface bloqueie de forma explícita qualquer tentativa de mostrar uma superfície com contexto ausente ou incompatível, para nunca expor silenciosamente dados de um perfil errado.

**Why P1**: AC explícito da História 1.4; é a salvaguarda que evita vazamento visual entre perfis durante a demonstração.

**Acceptance Criteria**:

1. IF uma superfície for solicitada sem um contexto de perfil válido, ou com um contexto incompatível com o perfil ativo THEN o sistema SHALL bloquear a apresentação dessa superfície. <!-- unwanted-behavior -->
2. IF a apresentação de uma superfície for bloqueada por contexto ausente ou incompatível THEN o sistema SHALL oferecer uma próxima ação válida: um botão que retorna à Visão geral do perfil ativo vigente. <!-- unwanted-behavior -->
3. IF o contexto for inválido THEN o sistema SHALL NOT exibir, nem por um instante, dados pertencentes ao perfil anterior. <!-- unwanted-behavior -->

**Independent Test**: Forçar (via navegação direta a uma rota/estado de superfície administrativa enquanto o perfil ativo é Segurado) uma incompatibilidade e confirmar que a interface bloqueia e oferece o retorno, sem piscar conteúdo do perfil anterior.

---

### P2: Operar em larguras de desktop suportadas

**User Story**: Como pessoa demonstradora, quero que a navegação e o seletor de perfil continuem funcionais entre 1024 px e monitores amplos, para demonstrar em qualquer notebook ou monitor típico sem perder funções.

**Why P2**: Importante para robustez da demonstração em diferentes máquinas, mas não bloqueia a alternância de perfil em si (já coberta no P1).

**Acceptance Criteria**:

1. WHILE a largura da janela estiver entre 1024 px e a largura de monitores amplos, o sistema SHALL manter todas as funções de navegação e do seletor "Visualizar como" acessíveis, recolhendo a navegação lateral quando necessário. <!-- state-driven -->
2. IF a largura da janela for menor que 1024 px THEN o sistema SHALL exibir um aviso informando que a resolução não é suportada pelo MVP, mantendo a operação possível. <!-- unwanted-behavior -->

**Independent Test**: Redimensionar a janela do navegador por 1024 px, 1279 px e uma largura ampla (ex. 1920 px) e confirmar navegação e seletor operáveis em todas; redimensionar abaixo de 1024 px e confirmar o aviso sem perda de função.

---

### P2: Operar o seletor e a navegação por teclado

**User Story**: Como pessoa demonstradora, quero operar o seletor "Visualizar como" e a navegação inteiramente por teclado, para demonstrar acessibilidade e não depender do mouse.

**Why P2**: Requisito de acessibilidade explícito no AC da história; essencial para o padrão do produto, mas independente da lógica central de alternância (P1).

**Acceptance Criteria**:

1. WHEN a pessoa operar o seletor demonstrativo e a navegação usando `Tab`, `Shift+Tab` e `Enter` THEN o sistema SHALL seguir a ordem de leitura visual e manter um indicador de foco de 3 px sempre visível. <!-- event-driven -->
2. WHEN o perfil for alternado por teclado ou por clique THEN o sistema SHALL anunciar a mudança de perfil por uma região `aria-live="polite"`. <!-- event-driven -->
3. O sistema SHALL comunicar o perfil ativo por texto, ícone e estado visual combinados, nunca só por cor. <!-- ubiquitous -->

**Independent Test**: Navegar da barra de contexto até um item de navegação usando só o teclado, alternar o perfil com `Enter` e confirmar foco visível, ordem de leitura e anúncio por leitor de tela (via árvore de acessibilidade).

---

## Edge Cases

- IF a chamada de rede para o segurado sintético padrão retornar erro 5xx ou timeout THEN o sistema SHALL exibir estado de indisponibilidade com causa e ação de nova tentativa (coberto em P1 "Apresentar o segurado sintético padrão", AC3).
- IF o valor salvo em `localStorage` for um perfil desconhecido (ex. corrompido) THEN o sistema SHALL tratar como ausência de preferência e usar "Administrador" como padrão.
- WHEN a pessoa alternar o perfil repetidamente em sequência rápida THEN o sistema SHALL sempre refletir a última seleção, sem travar em um estado intermediário.
- IF o modal "Restaurar dados sintéticos" estiver aberto no momento da troca de perfil THEN o sistema SHALL fechá-lo automaticamente como parte da limpeza de estado transitório (coberto em P1, AC4).

---

## Requirement Traceability

Each requirement gets a unique ID for tracking across design, tasks, and validation.

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| CTX-01 | P1: Alternar entre Administrador e Segurado | Tasks | Implementing |
| CTX-02 | P1: Alternar entre Administrador e Segurado | Tasks | Verified |
| CTX-03 | P1: Alternar entre Administrador e Segurado | Tasks | Implementing |
| CTX-04 | P1: Alternar entre Administrador e Segurado | Tasks | Implementing |
| CTX-05 | P1: Alternar entre Administrador e Segurado | Tasks | Implementing |
| CTX-06 | P1: Alternar entre Administrador e Segurado | Tasks | Implementing |
| CTX-07 | P1: Apresentar o segurado sintético padrão | Tasks | Implementing |
| CTX-08 | P1: Apresentar o segurado sintético padrão | Tasks | Implementing |
| CTX-09 | P1: Apresentar o segurado sintético padrão | Tasks | Implementing |
| CTX-10 | P1: Persistir o perfil localmente sem criar identidade | Tasks | Implementing |
| CTX-11 | P1: Persistir o perfil localmente sem criar identidade | Tasks | Implementing |
| CTX-12 | P1: Persistir o perfil localmente sem criar identidade | Tasks | Implementing |
| CTX-13 | P1: Bloquear contexto ausente ou incompatível | Tasks | Implementing |
| CTX-14 | P1: Bloquear contexto ausente ou incompatível | Tasks | Implementing |
| CTX-15 | P1: Bloquear contexto ausente ou incompatível | Tasks | Implementing |
| CTX-16 | P2: Operar em larguras de desktop suportadas | Tasks | Implementing |
| CTX-17 | P2: Operar em larguras de desktop suportadas | Tasks | Implementing |
| CTX-18 | P2: Operar o seletor e a navegação por teclado | Tasks | Verified |
| CTX-19 | P2: Operar o seletor e a navegação por teclado | Tasks | Implementing |
| CTX-20 | P2: Operar o seletor e a navegação por teclado | Tasks | Implementing |

**ID format:** `CTX-[NUMBER]`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 20 total, 0 mapped to tasks, 20 unmapped ⚠️ (mapeamento ocorre na fase de Tasks)

---

## Success Criteria

How we know the feature is successful:

- [ ] A pessoa demonstradora alterna Administrador ↔ Segurado a qualquer momento sem qualquer texto de login/autenticação/autorização visível.
- [ ] Toda superfície implementada mostra a barra de contexto e a faixa fixa, e o perfil sobrevive a um F5.
- [ ] Testes automatizados cobrem as duas direções de alternância, limpeza de contexto incompatível, atualização de página, contexto inválido e as faixas de largura suportadas (1024 px, 1279 px, largura ampla, <1024 px) — refletindo o AC de testes da História 1.4 em `epics.md`.
- [ ] Nenhuma decisão de domínio no backend lê o perfil de apresentação do frontend.
