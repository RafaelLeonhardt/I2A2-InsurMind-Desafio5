# História 1.3: Verificar a Prontidão das Dependências — Specification

## Problem Statement

A pessoa demonstradora precisa saber, antes e durante uma demonstração, se backend, DuckDB, INMET e OpenAI estão prontos — e o que fazer quando algum não está. Hoje só existe `/saude`, que confirma apenas que o processo backend está de pé; não há visão consolidada nem checagem das dependências externas.

## Goals

- [ ] Uma superfície de prontidão mostra, para cada uma das 4 dependências, estado / última verificação / causa conhecida / impacto esperado / ação disponível.
- [ ] Backend e DuckDB respondem em ≤1s p95, sem depender de INMET/OpenAI.
- [ ] INMET e OpenAI são verificados por chamada real (não simulada), assíncrona, sem nunca expor a credencial da OpenAI.

## Out of Scope

| Feature | Reason |
| --- | --- |
| Adaptadores completos de INMET (normalização meteorológica) e OpenAI (LangGraph, prompts) | Pertencem às Histórias 2.1 e 3.1; esta história só precisa de uma sonda de prontidão mínima, não do cliente de produção. |
| Persistência da prontidão entre reinícios do backend | Decisão registrada abaixo: estado em memória, por processo. |
| Autenticação/autorização real | Fora do MVP; ADR AD-4 do épico trata identidade como apresentacional (História 1.4). |
| Métricas/observabilidade externa (Prometheus, etc.) | NFR10 exige logs estruturados correlacionáveis, não um pipeline de métricas. |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Persistência do estado de prontidão | Em memória, por processo do backend | Sonda operacional recomputável, não dado de domínio; evita migração DuckDB para um valor descartável a cada restart | y |
| Granularidade da re-verificação manual | Uma ação por dependência (4 botões independentes) | Evita re-disparar INMET/OpenAI (lentos) só para atualizar backend/DuckDB (rápidos); combina com o layout em linhas do AC | y |
| Classificação Degradada vs Indisponível (INMET/OpenAI) | Degradada = resposta obtida porém lenta (acima do orçamento de latência) ou status transitório (ex. 429/5xx) numa única tentativa; Indisponível = timeout, falha de conexão, ou erro não transitório (ex. DNS, 401 de credencial inválida) | Preserva a distinção exigida pelo AC com uma regra objetiva e testável | y |
| Mecanismo de checagem INMET | Chamada real HTTP a um endpoint público do INMET, timeout curto, sem retries automáticos (a sonda é um "ping", não o adaptador de produção) | Confirmado pelo usuário: chamada real, não simulada | y |
| Mecanismo de checagem OpenAI | Se `OPENAI_API_KEY` ausente/vazia: reporta indisponível sem chamada de rede. Se presente: uma chamada real de baixo custo (ex. listar modelos) confirma a chave, nunca logando/ecoando o valor | Confirmado pelo usuário | y |
| Disparo das checagens | Automático nas 4 dependências ao carregar a superfície, mais ação manual de re-verificação por dependência | Confirmado pelo usuário; cobre o AC de carregamento e o AC de "solicitar uma nova verificação" | y |
| Transporte de progresso assíncrono | Polling HTTP curto (GET a cada ~2s enquanto o estado for não terminal) | Confirmado pelo usuário; consistente com o estilo REST/JSON já usado no resto da API, sem introduzir SSE/websocket | y |
| Latência-orçamento exato para "degradada" (INMET/OpenAI) e timeout de "indisponível" | Definidos na fase de Design (não são uma decisão de produto, e sim um parâmetro técnico calibrável) | Mantém o spec focado no comportamento observável; o valor numérico entra no design/implementação | y |
| Formato da resposta do progresso assíncrono (job id, forma do polling) | Definido na fase de Design, seguindo os padrões REST/JSON já estabelecidos (recursos plurais, `snake_case`, `Idempotency-Key`) | Decisão técnica de contrato HTTP, não de produto | y |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Ver a prontidão consolidada das 4 dependências ⭐ MVP

**User Story**: Como pessoa demonstradora, quero ver o estado de backend, DuckDB, INMET e OpenAI numa única superfície, para saber se a demonstração pode começar.

**Why P1**: É o núcleo do valor da história — sem isto não há prontidão visível nenhuma.

**Acceptance Criteria**:

1. WHEN a superfície de prontidão for carregada THEN o sistema SHALL apresentar uma linha separada para backend, DuckDB, INMET e OpenAI, cada uma com estado, última verificação, causa conhecida, impacto esperado e ação disponível. <!-- event-driven -->
2. WHILE uma verificação estiver em andamento para uma dependência THE sistema SHALL exibir o estado `Verificando` para essa linha e anunciar a atualização via `aria-live="polite"`, sem bloquear ou perder o estado das demais linhas. <!-- state-driven -->
3. WHEN backend e DuckDB forem consultados THEN o sistema SHALL responder com o estado mais recente em até 1 segundo no percentil 95, usando códigos de estado estáveis e sem chamar INMET ou OpenAI. <!-- event-driven -->
4. IF INMET ou OpenAI estiverem degradados ou indisponíveis THEN o sistema SHALL diferenciar `Degradada` de `Indisponível` por texto, ícone e cor, e explicar quais partes da demonstração continuam disponíveis e quais ficam bloqueadas. <!-- unwanted-behavior -->

**Independent Test**: Abrir a superfície com todas as dependências saudáveis e ver as 4 linhas em `Disponível`; depois derrubar/degradar uma dependência (dublê em teste, indisponibilidade real em demo) e ver a linha correspondente mudar sem afetar as outras.

---

### P1: Proteger a credencial OpenAI ao reportar prontidão ⭐ MVP

**User Story**: Como pessoa demonstradora, quero saber que a produção agêntica está indisponível por falta de credencial, sem que a chave real apareça em lugar nenhum, para não vazar segredo durante uma demonstração pública.

**Why P1**: Requisito de segurança direto (NFR3); um vazamento aqui é grave e imediato.

**Acceptance Criteria**:

1. IF `OPENAI_API_KEY` estiver ausente ou inválida THEN o sistema SHALL reportar que a produção agêntica não está disponível. <!-- unwanted-behavior -->
2. The system SHALL garantir que nenhum valor, fragmento, cabeçalho ou detalhe capaz de revelar a credencial apareça na API, na interface ou em logs, em qualquer estado de prontidão da OpenAI. <!-- ubiquitous -->

**Independent Test**: Rodar sem `OPENAI_API_KEY` definida e confirmar `Indisponível` na linha OpenAI; inspecionar resposta HTTP, DOM renderizado e logs do processo e não encontrar a chave nem fragmentos dela.

---

### P1: Disparar e acompanhar uma nova verificação sem duplicar ⭐ MVP

**User Story**: Como pessoa demonstradora, quero pedir uma nova verificação de uma dependência e acompanhar seu progresso, para atualizar a prontidão sem recarregar a página inteira nem disparar checagens duplicadas por clique repetido.

**Why P1**: Sem isto a superfície é estática; a história pede explicitamente re-verificação assíncrona e idempotente.

**Acceptance Criteria**:

1. WHEN a pessoa solicitar uma nova verificação de uma dependência THEN o sistema SHALL executar a operação externa assincronamente e expor seu progresso para consulta. <!-- event-driven -->
2. IF a mesma chave `Idempotency-Key` for reenviada para a mesma dependência THEN o sistema SHALL retornar a verificação já em andamento ou já concluída, SEM criar uma segunda verificação. <!-- unwanted-behavior -->
3. WHILE uma verificação estiver em andamento THE sistema SHALL permitir consulta de progresso por polling HTTP, com o estado mudando de `Verificando` para um estado terminal (`Disponível`, `Degradada` ou `Indisponível`) ao concluir. <!-- state-driven -->

**Independent Test**: Clicar "verificar novamente" na linha INMET duas vezes seguidas com a mesma chave de idempotência (ex. duplo clique) e confirmar, via API, que apenas uma verificação foi executada; fazer polling até o estado terminal aparecer.

---

### P1: Reportar falha terminal de verificação de forma acionável ⭐ MVP

**User Story**: Como pessoa demonstradora, quero que uma falha inesperada na verificação fique registrada e explicada, para saber o que aconteceu e o que fazer a seguir, mesmo se eu perder um toast.

**Why P1**: NFR11 exige estado terminal explícito para toda falha; sem isto a UI pode "travar" em Verificando.

**Acceptance Criteria**:

1. IF uma verificação atingir uma falha inesperada THEN o sistema SHALL levá-la a um estado terminal consultável na superfície, em português brasileiro, com ocorrência, impacto esperado e próxima ação segura. <!-- unwanted-behavior -->
2. WHERE um toast for usado para reforçar uma falha THE sistema SHALL garantir que o toast seja apenas um reforço, nunca a única evidência do erro (a superfície permanece a fonte de verdade). <!-- optional-feature -->

**Independent Test**: Forçar uma falha inesperada (dublê que lança exceção não mapeada) e confirmar que a linha correspondente mostra estado terminal com causa/impacto/ação, mesmo sem nenhum toast visível.

---

### P2: Operar a superfície por teclado e em zoom 200%

**User Story**: Como pessoa demonstradora usando teclado ou tela ampliada, quero operar toda a superfície de prontidão sem mouse e sem perder controles, para apresentar com acessibilidade real.

**Why P2**: Requisito de acessibilidade (NFR7) real mas não bloqueia a primeira demonstração funcional end-to-end; pode seguir a P1 de perto.

**Acceptance Criteria**:

1. WHEN a pessoa percorrer estados e ações por teclado (`Tab`, `Shift+Tab`, `Enter`) THEN o sistema SHALL manter nome acessível e foco visível em cada controle, com alvo mínimo de 44×44 px. <!-- event-driven -->
2. WHILE a página estiver ampliada em 200% THE sistema SHALL permanecer funcional nas larguras desktop suportadas. <!-- state-driven -->

**Independent Test**: Navegar a superfície inteira só com teclado; ampliar o navegador para 200% e repetir as ações de re-verificação sem perda de funcionalidade.

---

## Edge Cases

- IF a superfície for carregada antes de qualquer verificação ter ocorrido THEN o sistema SHALL mostrar `Verificando` (não um estado indefinido/vazio) para cada dependência ainda sem resultado. <!-- state-driven, coberto pela AC 1.2 acima -->
- IF o backend for reiniciado THEN o sistema SHALL tratar toda dependência como sem resultado anterior e re-verificar do zero (estado em memória, não persistido — ver Assumptions). <!-- unwanted-behavior -->
- IF duas requisições de re-verificação para a MESMA dependência chegarem com `Idempotency-Key` diferentes enquanto uma primeira ainda está em andamento THEN o sistema SHALL rejeitar ou enfileirar a segunda sem interromper a primeira (comportamento exato de conflito fica para o Design, seguindo o padrão REST/JSON já usado por outras mutações da API). <!-- unwanted-behavior -->
- IF INMET ou OpenAI nunca responderem dentro do timeout THEN o sistema SHALL classificar como `Indisponível`, nunca deixar a verificação presa indefinidamente em `Verificando`. <!-- unwanted-behavior, NFR11 -->

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| PRONT-01 | P1: Ver a prontidão consolidada | Pending | Pending |
| PRONT-02 | P1: Ver a prontidão consolidada (verificando + aria-live) | Pending | Pending |
| PRONT-03 | P1: Ver a prontidão consolidada (backend/DuckDB ≤1s p95) | Pending | Pending |
| PRONT-04 | P1: Ver a prontidão consolidada (degradada vs indisponível) | Pending | Pending |
| PRONT-05 | P1: Proteger a credencial OpenAI (sem credencial → indisponível) | Pending | Pending |
| PRONT-06 | P1: Proteger a credencial OpenAI (nunca vazar valor) | Pending | Pending |
| PRONT-07 | P1: Disparar e acompanhar (assíncrono + progresso) | Pending | Pending |
| PRONT-08 | P1: Disparar e acompanhar (idempotência, sem duplicar) | Pending | Pending |
| PRONT-09 | P1: Disparar e acompanhar (polling até estado terminal) | Pending | Pending |
| PRONT-10 | P1: Reportar falha terminal (estado terminal acionável) | Pending | Pending |
| PRONT-11 | P1: Reportar falha terminal (toast é reforço, não única evidência) | Pending | Pending |
| PRONT-12 | P2: Teclado e zoom (foco/alvo mínimo) | Pending | Pending |
| PRONT-13 | P2: Teclado e zoom (200% funcional) | Pending | Pending |

**ID format:** `PRONT-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 13 total, 0 mapped to tasks, 13 unmapped ⚠️ (esperado nesta fase — Tasks ainda não rodou)

---

## Success Criteria

- [ ] As 4 dependências aparecem sempre, com estado / última verificação / causa / impacto / ação, sem depender umas das outras para renderizar.
- [ ] Backend/DuckDB respondem ≤1s p95 sem tocar INMET/OpenAI.
- [ ] Nenhum teste, log, resposta de API ou tela jamais expõe `OPENAI_API_KEY` ou fragmento dela.
- [ ] Clique duplicado em "verificar novamente" com a mesma `Idempotency-Key` nunca cria uma segunda verificação.
- [ ] Nenhuma verificação fica presa indefinidamente em `Verificando`; toda falha chega a um estado terminal explicável em português.
- [ ] Testes cobrem: disponível, degradada, indisponível, ausência de credencial, repetição idempotente e falha terminal — usando dublês para INMET/OpenAI, sem chamada de rede real em teste.
