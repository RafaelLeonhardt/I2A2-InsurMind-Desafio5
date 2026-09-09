# História 6.2: Acompanhar a execução e a decisão do evento — Specification

## Problem Statement

`SuperficieExecucao` e `SuperficieEventoDecisao` (`src/frontend/src/funcionalidades/execucao/`, `.../evento-decisao/`) já existem, testados unitariamente, e reproduzem a tela `EventPage`/imagem `02-analise-evento-regra-publico` do protótipo: evidências meteorológicas, condições da regra aplicada e a prévia do público elegível. Nenhuma delas é montada por `App.tsx`/`PerfilContexto.tsx` (`.specs/STATE.md`, "Known open items") — hoje só são alcançáveis dentro da própria suíte de testes. Sem esta história, um administrador não tem como auditar por que um evento gerou (ou não) uma execução preventiva.

## Goals

- [ ] A partir da lista de eventos (História 6.1), abrir um evento com execução associada mostra o progresso real da execução (`SuperficieExecucao`) e a decisão de risco/regra aplicada (`SuperficieEventoDecisao`)
- [ ] A prévia do público elegível (nome, bairro, apólice, canal, motivo de elegibilidade) fica visível a partir dessa tela
- [ ] Uma execução em qualquer estado não-terminal (`EstadoExecucao`) mostra sua etapa corrente sem exigir que o admin saiba interpretar o enum interno

## Out of Scope

| Feature | Reason |
| --- | --- |
| Edição da regra a partir desta tela | História 6.3 — aqui a regra é só consultada/referenciada, nunca editada |
| Geração/revisão de mensagens | História 6.5 — esta história para na decisão do evento, antes da produção agêntica |
| Retentativa de execução falha na coleta (`falhou_coleta`) | Já coberta pelo backend (AD-009); esta história expõe o estado, não adiciona um novo mecanismo de retry além do que a API já resolve |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Composição das duas superfícies | `SuperficieExecucao` já embute `SuperficieEventoDecisao` (`embutido`) condicionalmente por etapa (`src/frontend/src/funcionalidades/execucao/SuperficieExecucao.tsx:225`) — a história reusa exatamente essa composição existente, sem duplicar a tela de decisão em outro lugar | O componente já resolve isso; reimplementar a composição seria retrabalho não justificado | y — verificado no código-fonte |
| Motivo de elegibilidade por segurado (visto na imagem 02, coluna "Motivo de elegibilidade") | Exibido quando o backend de elegibilidade já o fornecer (`avaliacao_elegibilidade`/`elegibilidade`); se o campo não existir na resposta, a coluna não aparece — não é inventado no frontend | Este é exatamente o item D.3-#20 do levantamento de gaps: incerto se o backend já persiste o motivo. Assumir sem confirmar romperia AD-009-like "nunca inferir dado" já em vigor no projeto | y — segue o princípio "nunca preencher lacuna com inferência", já formalizado em EXPLICACAO-05 |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Abrir a execução de um evento a partir da lista ⭐ MVP

**User Story**: Como administrador, quero abrir a execução preventiva de um evento específico para acompanhar seu progresso e entender a decisão automática por trás dela.

**Why P1**: É a continuação direta da História 6.1 — sem ela, a lista de eventos não leva a lugar nenhum.

**Acceptance Criteria**:

1. WHEN o administrador selecionar um evento com execução associada na lista de eventos THEN a interface SHALL abrir `SuperficieExecucao` para essa execução, mostrando a etapa corrente e o histórico de marcos já persistidos.
2. WHILE a execução estiver em uma etapa de decisão de risco/regra the interface SHALL exibir `SuperficieEventoDecisao` com as evidências meteorológicas e as condições da regra avaliada.
3. IF a execução tiver terminado em um estado de falha (ex.: `falhou_coleta`, `falhou_preparacao_ia`) THEN a interface SHALL mostrar o estado terminal e, quando existir, a execução de retentativa correlacionada (`execucao_origem_id`, AD-009).

**Independent Test**: A partir do cenário sintético padrão, abrir um evento relevante com execução em andamento e confirmar que a etapa exibida corresponde ao estado real persistido no backend (`GET` da execução).

---

### P1: Consultar o público elegível da decisão ⭐ MVP

**User Story**: Como administrador, quero ver a prévia dos segurados elegíveis dessa decisão para confirmar que a regra aplicada selecionou o público correto antes de qualquer comunicação ser gerada.

**Why P1**: É o núcleo de auditoria da tela — sem essa prévia, a decisão automática permanece uma caixa-preta para o admin.

**Acceptance Criteria**:

1. WHEN a decisão do evento tiver identificado um público elegível THEN a interface SHALL exibir uma tabela com nome, bairro, apólice e canal de cada segurado elegível.
2. WHERE o backend de elegibilidade expuser o motivo da elegibilidade (evento, regra, condição atendida) the interface SHALL exibir essa coluna; caso contrário, ela SHALL permanecer ausente em vez de exibir um valor inventado.

**Independent Test**: Abrir a decisão de um evento com público elegível não vazio e confirmar que cada linha da tabela corresponde a um segurado de fato elegível segundo a API, sem segurado fora do critério aparecendo.

---

## Edge Cases

- IF o evento identificado for do tipo `dado_invalido` ou `sem_risco` (RISCO-12/13) THEN a interface SHALL mostrar por que nenhuma execução foi criada, sem apresentar uma tela de decisão vazia como se fosse um erro.
- WHEN a execução estiver bloqueada por uma exceção (marco de bloqueio) THEN a causa exibida SHALL vir do marco persistido, nunca de um texto inventado no frontend.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| PAINELEXEC-01 | P1: Abrir a execução de um evento a partir da lista | Execute | ✅ Verified — navegação da 6.1 (`SuperficieEventos.tsx:83-85,162-168` → `App.tsx:54-55` → `SuperficieExecucao`), evidência própria em `SuperficieEventos.test.tsx:61-87` |
| PAINELEXEC-02 | P1: Abrir a execução de um evento a partir da lista | Execute | ✅ Verified — `mostrarDecisaoDeRisco` ampliado para cobrir toda etapa pós-coleta (`SuperficieExecucao.tsx:190-191,280`), evidência em `SuperficieExecucao.test.tsx:302-321` |
| PAINELEXEC-03 | P1: Abrir a execução de um evento a partir da lista | Execute | ✅ Verified — estados `falhou_*` tratados como exceção (`SuperficieExecucao.tsx:78-84`) + seção "Execuções correlacionadas" navegável (`:243-278`), evidência em `SuperficieExecucao.test.tsx:279-377` |
| PAINELEXEC-04 | P1: Consultar o público elegível da decisão | Execute | ✅ Verified — já satisfeito por `SuperficieEventoDecisao` (2.5), tabela segurado/apólice/localização/canal (`SuperficieEventoDecisao.tsx:281-323`), evidência em `SuperficieEventoDecisao.test.tsx:274-287` |
| PAINELEXEC-05 | P1: Consultar o público elegível da decisão | Execute | ✅ Verified (com nota de spec-precision) — já satisfeito por `SuperficieEventoDecisao` (2.5), explicação expansível "Ver critérios" por segurado (`SuperficieEventoDecisao.tsx:311-358`); ver `validation.md` — mecanismo real é uma explicação sempre presente, não a coluna condicional descrita literalmente no AC (o campo `motivo` nunca existe no tipo da API) |

**ID format:** `PAINELEXEC-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 5 total, 5 mapped, 0 unmapped — Design feito inline (Medium, reusa AD-016; sem decisão de arquitetura nova), Tasks feito inline (3 mudanças atômicas em `SuperficieExecucao.tsx`), Execute concluído. **Verifier: PASS** (`.specs/features/6-2-acompanhar-a-execucao-e-a-decisao-do-evento/validation.md`, 2026-09-09) — 5/5 ACs com evidência `file:line`, 3/3 mutações do sensor mortas, 0 sobreviventes.

---

## Success Criteria

- [ ] Toda execução não-terminal listada em 6.1 é abrível e mostra sua etapa real
- [ ] A prévia de elegíveis nunca mostra um segurado fora do critério da regra aplicada
- [ ] Nenhum dado de motivo de elegibilidade é inventado quando o backend não o fornece
