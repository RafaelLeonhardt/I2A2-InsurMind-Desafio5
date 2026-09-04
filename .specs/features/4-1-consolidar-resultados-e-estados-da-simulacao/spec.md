# História 4.1: Consolidar resultados e estados da simulação — Specification

## Problem Statement

A História 3.6 executa a simulação e persiste entregas simuladas, mas nada ainda consolida esses dados numa visão de resultados confiável. Sem essa história, Marina não teria como confirmar que todo o lote aprovado foi de fato processado, nem distinguir uma entrega simulada de uma falha técnica local — arriscando que a demonstração pareça sugerir uma confirmação real de provedor externo.

## Goals

- [ ] Toda mensagem aprovada confirma atomicamente a sequência de exibição `Preparada`/`Processada`/`Enviada — simulação`, nunca representando confirmação de provedor externo nem ficando parcialmente confirmada
- [ ] Marina abre Resultados e vê totais por canal e por estado, reconciliáveis com a quantidade efetivamente aprovada e simulada
- [ ] Mensagens rejeitadas, excluídas ou em exceção nunca contam como entrega simulada, mas permanecem contabilizadas separadamente no resumo do lote
- [ ] Falha local antes da confirmação atômica deixa a execução em `falhou_simulacao`, sem entrega parcial, mensagens ainda `aprovada`, nunca apresentada como falha de canal real
- [ ] Resultados reconstroem do DuckDB a cada consulta/recarga, sem repetir transição nem reabrir/regredir estado terminal
- [ ] A tabela de resultados é acessível (cabeçalhos, ordenação, contagens, ações de linha com nomes acessíveis) e "Enviada — simulação" aparece por extenso com texto, ícone e cor
- [ ] Uma divergência entre totais e entregas persistidas é detectada e exibida como estado consultável `totais_divergentes`, com correlação e impacto, nunca corrigida ou ocultada silenciosamente

## Out of Scope

| Feature | Reason |
| --- | --- |
| Execução da simulação em si | História 3.6 — esta história só consolida e exibe o que já foi simulado |
| Detalhe individual de uma mensagem/resultado | História 4.2 |
| Visualização pelo segurado | História 4.3 |
| Linha do tempo completa da execução | História 4.4 |
| Correção automática de divergência detectada | Explicitamente proibido pelo AC — a divergência é reportada, nunca corrigida silenciosamente |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Onde vive o estado de exibição `Preparada`/`Processada`/`Enviada — simulação` | Um campo de vocabulário de exibição derivado da existência da linha em `entregas_simuladas` (3.6) — como a criação já é atômica (3.6: "só após o sucesso da transação as mensagens aprovadas mudam para `simulada_entregue`"), a entrega, ao existir, já percorreu a sequência inteira; não são três estados persistidos sequencialmente, e sim o rótulo textual da garantia atômica já implementada | Cumpre "confirmar atomicamente a sequência" sem introduzir uma segunda máquina de estados paralela à de `EstadoMensagem` (AD-004/3.2) já aprovada | n — decisão técnica de modelagem, revisável no Design |
| Onde vive `totais_divergentes` | Um estado de **exibição da superfície de Resultados**, calculado a cada consulta (contagem de `entregas_simuladas` vs. contagem de `mensagens` em `simulada_entregue`), não um novo valor de `EstadoExecucao` (AD-004) | `EstadoExecucao` já é um enum fixado por decisão de projeto (AD-004), reusado por múltiplas histórias; introduzir um valor novo exigiria uma nova decisão arquitetural (AD) só para um caso de inconsistência técnica que, por definição, nunca deveria ocorrer sob operação normal | n — decisão técnica de modelagem, revisável no Design |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Confirmação atômica e totais reconciliáveis por canal/estado ⭐ MVP

**User Story**: Como Marina, quero ver totais por canal e por estado que sempre batem com o que foi realmente aprovado e simulado, para confirmar que o lote inteiro foi processado sem sugerir uma entrega real.

**Why P1**: É o núcleo de confiança da história — sem reconciliação correta, os números exibidos não significam nada.

**Acceptance Criteria**:

1. WHEN um lote aprovado for processado com sucesso pela simulação local THEN todas as mensagens aprovadas SHALL confirmar atomicamente a sequência de exibição `Preparada`, `Processada` e `Enviada — simulação`, sem nenhuma transição representando confirmação de um provedor externo e sem ficar parcialmente confirmada.
2. WHEN Marina abrir Resultados de uma simulação concluída THEN a interface SHALL exibir totais por canal e por estado para todas as mensagens do lote, com a soma dos totais reconciliável com a quantidade efetivamente aprovada e simulada.
3. IF houver mensagens rejeitadas, excluídas ou em exceção no lote THEN os totais da simulação SHALL não contá-las como entrega simulada, mas SHALL mantê-las contabilizadas separadamente no resumo do lote para explicar a diferença.

**Independent Test**: Simular um lote de 5 mensagens (3 aprovadas+simuladas, 1 rejeitada, 1 em `falhou_conteudo`) e confirmar que os totais mostram 3 "Enviada — simulação" e as outras 2 contabilizadas separadamente, sem aparecer como entrega simulada.

---

### P1: Falha local sem entrega parcial e sem falha fictícia de canal ⭐ MVP

**User Story**: Como Marina, quero que uma falha local na simulação nunca pareça uma falha de WhatsApp/e-mail/SMS, para nunca confundir um problema técnico interno com uma falha real de provedor.

**Why P1**: É a garantia de honestidade da simulação — sem ela, a demonstração poderia enganar sobre a natureza da falha.

**Acceptance Criteria**:

1. IF a simulação local falhar antes da confirmação atômica THEN a execução SHALL estar no terminal `falhou_simulacao`, sem entregas parciais, com as mensagens ainda `aprovada`.
2. The system SHALL nunca apresentar a falha técnica local como falha fictícia de WhatsApp, e-mail ou SMS.

**Independent Test**: Forçar uma falha local (3.6) e confirmar, na superfície de Resultados, que nenhuma entrega parcial aparece e nenhum texto sugere falha de canal real.

---

### P1: Reidratação sem repetição e sem regressão de estado terminal ⭐ MVP

**User Story**: Como Marina, quero atualizar a página de Resultados a qualquer momento e ver sempre o mesmo resultado real, para confiar na consistência da consulta.

**Why P1**: É a garantia de que Resultados é uma visão pura de leitura, sem efeito colateral.

**Acceptance Criteria**:

1. WHEN a página de Resultados for atualizada ou consultada novamente THEN os resultados SHALL ser reconstruídos a partir do DuckDB sem repetir nenhuma transição.
2. The system SHALL nunca permitir que um estado terminal regrida ou reabra por efeito de uma consulta.

**Independent Test**: Consultar Resultados duas vezes seguidas para a mesma execução concluída e confirmar, por contagem de entregas, que nenhuma nova linha foi criada pela segunda consulta.

---

### P2: Acessibilidade da tabela e divergência consultável

**User Story**: Como Marina, quero navegar a tabela de resultados com teclado/leitor de tela, e ser avisada explicitamente se algo não bater, para operar com confiança mesmo diante de um problema técnico.

**Why P2**: Reforça usabilidade e transparência sobre o núcleo de reconciliação já garantido pelas P1; não bloqueia a primeira demonstração de resultados corretos.

**Acceptance Criteria**:

1. WHEN Marina navegar a tabela de resultados por canal, estado e totais THEN cabeçalhos, ordenação, contagens e ações de linha SHALL possuir nomes acessíveis.
2. The interface SHALL exibir "Enviada — simulação" por extenso, com texto, ícone e cor.
3. IF a superfície detectar uma divergência entre os totais e as entregas persistidas THEN ela SHALL exibir um estado `totais_divergentes` com correlação e impacto, sem corrigir ou ocultar a divergência silenciosamente.

**Independent Test**: Navegar a tabela de resultados inteiramente por teclado e confirmar nomes acessíveis em cada cabeçalho/ação; simular uma divergência de contagem via dado de teste e confirmar que `totais_divergentes` aparece com correlação, sem "corrigir" o número exibido.

---

## Edge Cases

- IF uma execução não tiver nenhuma mensagem aprovada (todas rejeitadas/excluídas/em exceção) THEN os totais SHALL mostrar zero entregas simuladas, sem erro técnico.
- IF duas execuções distintas (origem e retentativa correlacionada) tiverem simulações concluídas THEN os totais de cada uma SHALL ser calculados e exibidos de forma independente, sem misturar contagens.
- WHEN uma consulta de totais ocorrer durante uma simulação ainda em `simulando` (não concluída) THEN a interface SHALL exibir o estado de progresso real (3.6), não um total parcial apresentado como final.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| RESULT-01 | P1: Confirmação atômica e totais reconciliáveis por canal/estado | 3.6 (ServicoSimulacao.confirmar) | Verified |
| RESULT-02 | P1: Confirmação atômica e totais reconciliáveis por canal/estado | Execute (T1, T2, T3) | Verified |
| RESULT-03 | P1: Confirmação atômica e totais reconciliáveis por canal/estado | Execute (T1, T2) | Verified |
| RESULT-04 | P1: Falha local sem entrega parcial e sem falha fictícia de canal | Execute (T2, T3) | Verified |
| RESULT-05 | P1: Falha local sem entrega parcial e sem falha fictícia de canal | Execute (T2, T3) | Verified |
| RESULT-06 | P1: Reidratação sem repetição e sem regressão de estado terminal | Execute (T2, T3) | Verified |
| RESULT-07 | P1: Reidratação sem repetição e sem regressão de estado terminal | Execute (T2, T3) | Verified |
| RESULT-08 | P2: Acessibilidade da tabela e divergência consultável | Execute (T4) | Verified |
| RESULT-09 | P2: Acessibilidade da tabela e divergência consultável | Execute (T2, T3, T4) | Verified |
| RESULT-10 | P2: Acessibilidade da tabela e divergência consultável | Execute (T4) | Verified |

**ID format:** `RESULT-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 10 total, 10 verified (independent Verifier, round 2 — `validation.md`; round 1 flagged a discrimination-sensor gap in RESULT-08's sort test, closed by Fix 1 `27f9968`)

---

## Success Criteria

- [ ] Totais por canal/estado sempre reconciliam com a contagem real de aprovadas/simuladas/rejeitadas/excluídas/em exceção
- [ ] Nenhuma falha local aparece como falha de canal real em nenhum teste ou tela
- [ ] Consultar Resultados repetidamente nunca cria nova entrega nem reabre estado terminal
- [ ] Tabela de resultados navegável inteiramente por teclado/leitor de tela
- [ ] Divergência de totais é sempre reportada como `totais_divergentes`, nunca corrigida silenciosamente
