# Inicializar e Restaurar Dados Sintéticos Specification

## Problem Statement

The Central Preventiva backend has no persistence yet — only the Story 1.1 health-check scaffold exists. Every later epic (risk detection, agentic messaging, simulation, both admin and insured-facing surfaces) needs a versioned DuckDB schema and a reproducible set of synthetic reference data (segurados, apólices, regras, eventos meteorológicos, histórico de elegibilidade) to run against. Without a documented, reproducible init/restore mechanism, the demo cannot be reset between runs and the schema has no safe evolution path.

## Goals

- [ ] First run against an empty/missing DuckDB file applies all versioned migrations and seeds the full synthetic reference dataset in one reproducible step.
- [ ] Re-running initialization, or explicitly restoring via the admin UI, is safe, transactional, and idempotent — no duplicate records, no partial state on failure.
- [ ] The schema-versioning mechanism rejects unsafe states (future schema version, corrupted/missing migration ledger) instead of guessing.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
| --- | --- |
| `ExecucaoPreventiva`'s full behavior and child tables (elegibilidade, mensagem, revisão humana, entrega simulada, marco) | Belongs to Epic 2/Epic 3 stories that implement risk evaluation, messaging, and simulation; this story only creates a minimal `execucao_preventiva` table (id, estado, versão, timestamps) to make the restore guard testable. |
| Coleta e normalização INMET, avaliação de risco, geração/crítica de mensagens, simulação de envio | Epic 2 (`História 2.1`–`2.6`) and Epic 3. |
| Painel de prontidão de dependências (backend/DuckDB/INMET/OpenAI) | História 1.3. |
| Alternância de contexto Administrador/Segurado | História 1.4. |
| Geração de tipos OpenAPI para o frontend e inspeção completa do contrato | História 1.5 (this story exposes the endpoint; 1.5 covers the OpenAPI/Swagger UI experience end-to-end). |
| Coalescência entre gatilho agendado e manual de coleta meteorológica (DW-001) | Targets História 2.1, unrelated to this story's persistence concern. |

---

## Assumptions & Open Questions

Every ambiguity is resolved or recorded here — nothing is left silently unclear.

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Schema scope for this story | Reference/master tables only (`segurados`, `apolices`, `regras`, `eventos_meteorologicos`, `elegibilidades_historicas`) plus a minimal `execucao_preventiva` (id, estado, versão, timestamps) for the restore guard | Keeps this story's blast radius to what the seed needs; later epics extend `execucao_preventiva` and add its children when they're actually built | y |
| Restore-vs-active-execution guard (DW-002) | Implement and test now: restore refuses if any `execucao_preventiva` row has a non-terminal `estado`, proven via a fixture-inserted row | User chose to close DW-002 now rather than leave it open for a later story | y |
| Schema version / migration mechanism (DW-003) | `schema_migracoes` ledger table; each migration in its own transaction; startup refuses (no mutation) if the recorded version is newer than the code's known migrations; a failed migration mid-sequence leaves prior ones committed and halts before the failed one | Standard, auditable migration pattern; matches AD-11's "no partial mutation" invariant | y |
| Exact seed content (specific segurados/apólices/eventos examples, row counts) | Left to Design/Tasks: enough eligible + non-eligible examples for both chuva intensa and granizo scenarios, with unambiguously fictitious identifiers | FR46 requires eligible/non-eligible cases for both event types but not a specific count; concrete content is an implementation detail, not a product decision | y (agent discretion) |
| Confirmation modal component | Reuse the existing `Modal de confirmação` UX contract (`UX-DR20`) rather than a bespoke dialog | Already defined and required to be consistent across the app; no reason to diverge here | y (agent discretion) |
| Restore requested before any initialization has run | Respond with an explicit error directing the operator to run initialization first, rather than silently initializing as a side effect of restore | Restore and initialize are different operations with different guarantees (restore assumes a versioned baseline exists); conflating them would hide a real prerequisite | y (agent discretion) |

**Open questions:** none — all resolved or logged above.

---

## User Stories

### P1: Inicializar esquema versionado e dados sintéticos reproduzíveis ⭐ MVP

**User Story**: As a pessoa demonstradora, quero que a Central Preventiva inicialize seu banco DuckDB e semeie dados sintéticos automaticamente, para repetir os cenários de demonstração sem editar arquivos ou o banco manualmente.

**Why P1**: Every later story (risk detection, messaging, simulation, both UI surfaces) requires this data and schema to exist; nothing else in the product can be demoed without it.

**Acceptance Criteria** (each line is one EARS pattern):

1. WHEN o backend iniciar e o arquivo DuckDB operacional não existir ou estiver vazio THEN o sistema SHALL aplicar, em ordem, todas as migrações de schema versionadas pendentes, cada uma em sua própria transação, e SHALL semear o conjunto sintético de demonstração (segurados, apólices, regras, eventos meteorológicos, histórico de elegibilidade para chuva intensa e granizo, com casos elegíveis e não elegíveis e identificadores inequivocamente fictícios). <!-- event-driven -->
2. WHEN a inicialização for executada novamente sobre um banco já inicializado na mesma versão de seed THEN o sistema SHALL não duplicar nenhum registro e SHALL relatar que os dados já estavam preparados. <!-- event-driven -->
3. IF a versão registrada em `schema_migracoes` for maior que a versão mais alta conhecida pelo código em execução THEN o sistema SHALL recusar a inicialização sem aplicar nenhuma mutação e SHALL apresentar um erro explícito em português brasileiro. <!-- unwanted-behavior -->
4. IF uma migração pendente falhar durante a aplicação em sequência THEN o sistema SHALL preservar como aplicadas somente as migrações anteriores já commitadas, SHALL não registrar a migração falha em `schema_migracoes`, e SHALL interromper a inicialização com um erro que identifique a migração falha. <!-- unwanted-behavior -->
5. The system SHALL manter o arquivo operacional do DuckDB fora do controle de versão e integralmente recriável a partir das migrações e do seed versionados. <!-- ubiquitous -->
6. The system SHALL documentar, para cada tabela criada por esta história, suas colunas, chaves primárias e estrangeiras, restrições, colunas de timestamp e a estratégia de migração local, em um documento versionado no repositório. <!-- ubiquitous -->
7. The system SHALL garantir que todo dado semeado por esta história seja sintético ou anonimizado, sem dado pessoal real, credencial ou contato utilizável. <!-- ubiquitous -->

**Independent Test**: Delete/absent the operational DuckDB file, run the documented init command — schema and seed appear. Run it again — output reports "já preparado", row counts unchanged. Manually set `schema_migracoes` to a future version — next startup refuses with a PT-BR error and no file mutation.

---

### P1: Restaurar a demonstração com segurança transacional e idempotente ⭐ MVP

**User Story**: As a pessoa demonstradora, quero restaurar os dados sintéticos ao conjunto versionado pela interface administrativa, para repetir cenários mesmo depois de alterações locais, sem risco de corromper dados ou duplicar a operação.

**Why P1**: FR46 requires confirmed restoration as part of the reproducible demo baseline; without it, a demonstrator who has made local changes has no safe way back to a known-good state.

**Acceptance Criteria**:

1. WHEN a pessoa demonstradora solicitar a restauração pela interface administrativa THEN o sistema SHALL exibir um modal de confirmação identificando o objeto (dados sintéticos da demonstração) e o impacto (perda das alterações locais) e SHALL bloquear a execução até confirmação explícita. <!-- event-driven -->
2. WHEN a restauração for confirmada e nenhuma linha de `execucao_preventiva` estiver em estado não terminal THEN o sistema SHALL repor exatamente o conjunto de dados de referência versionado em uma única transação DuckDB. <!-- event-driven -->
3. IF existir ao menos uma linha de `execucao_preventiva` em estado não terminal no momento da restauração THEN o sistema SHALL recusar a restauração sem aplicar nenhuma mutação e SHALL informar que uma execução ativa impede a restauração. <!-- unwanted-behavior -->
4. WHEN uma requisição de restauração for repetida com a mesma `Idempotency-Key` THEN o sistema SHALL devolver a resposta previamente registrada sem executar uma nova restauração. <!-- event-driven -->
5. IF a mesma `Idempotency-Key` for reutilizada com conteúdo de requisição diferente THEN o sistema SHALL responder `409` sem efeito. <!-- unwanted-behavior -->
6. IF a transação de restauração não puder ser concluída THEN o sistema SHALL preservar o conjunto de dados anterior íntegro e consultável e SHALL apresentar um estado terminal de falha com ocorrência, impacto e próxima ação segura. <!-- unwanted-behavior -->
7. WHILE a restauração estiver em processamento THE interface SHALL apresentar os estados `Confirmação`, `Restaurando`, `Concluído` ou `Falha`, SHALL prender o foco no modal, SHALL permitir fechamento por `Esc` quando aplicável, e SHALL devolver o foco ao controle de origem ao concluir. <!-- state-driven -->
8. The system SHALL expor a restauração exclusivamente pela API REST/JSON sob `/api/v1`, com JSON em `snake_case`, exigindo `Idempotency-Key` em toda requisição de restauração. <!-- ubiquitous -->

**Independent Test**: Trigger restore from the admin UI after editing a seeded record — confirmation modal appears, blocks until confirmed, then the record reverts inside one transaction. Repeat the same request with the same `Idempotency-Key` — no second restore runs, same response returned. Insert a fixture `execucao_preventiva` row with a non-terminal `estado` — restore is refused with no mutation.

---

## Edge Cases

- IF o banco operacional já existir mas a tabela `schema_migracoes` estiver ausente ou corrompida THEN o sistema SHALL recusar a inicialização com um erro explícito em vez de presumir um estado de schema.
- IF a inicialização for interrompida entre a aplicação de duas migrações (ex.: processo encerrado) THEN a próxima inicialização SHALL retomar a partir da primeira migração pendente, sem reaplicar as já registradas em `schema_migracoes`.
- IF a restauração for solicitada antes de qualquer inicialização bem-sucedida THEN o sistema SHALL responder com um erro explícito orientando a executar a inicialização primeiro.
- WHEN o comando de inicialização for repetido imediatamente após uma inicialização bem-sucedida, sem nenhuma alteração local THEN o sistema SHALL continuar reportando "já preparado" sem qualquer escrita adicional.

---

## Requirement Traceability

Each requirement gets a unique ID for tracking across design, tasks, and validation.

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| SEED-01 | P1: Inicializar esquema e dados sintéticos | Tasks | Implementing |
| SEED-02 | P1: Inicializar esquema e dados sintéticos | Design | Pending |
| SEED-03 | P1: Inicializar esquema e dados sintéticos | Design | Pending |
| SEED-04 | P1: Inicializar esquema e dados sintéticos | Design | Pending |
| SEED-05 | P1: Inicializar esquema e dados sintéticos | Tasks | Implementing |
| SEED-06 | P1: Inicializar esquema e dados sintéticos | Design | Pending |
| SEED-07 | P1: Inicializar esquema e dados sintéticos | Design | Pending |
| SEED-08 | P1: Restaurar a demonstração com segurança | Design | Pending |
| SEED-09 | P1: Restaurar a demonstração com segurança | Design | Pending |
| SEED-10 | P1: Restaurar a demonstração com segurança | Tasks | Implementing |
| SEED-11 | P1: Restaurar a demonstração com segurança | Design | Pending |
| SEED-12 | P1: Restaurar a demonstração com segurança | Design | Pending |
| SEED-13 | P1: Restaurar a demonstração com segurança | Design | Pending |
| SEED-14 | P1: Restaurar a demonstração com segurança | Design | Pending |
| SEED-15 | P1: Restaurar a demonstração com segurança | Design | Pending |

**ID format:** `SEED-[NUMBER]`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 15 total, 0 mapped to tasks, 15 unmapped ⚠️ (expected until Tasks phase runs)

---

## Success Criteria

How we know the feature is successful:

- [ ] Running the documented init command against an empty DuckDB file produces schema + seed in one step; running it again is a no-op that reports "já preparado" with unchanged row counts.
- [ ] Restoring via the admin UI after a local edit reverts reference data to the versioned seed inside one transaction, with the confirmation modal blocking until explicit confirmation.
- [ ] A restore request repeated with the same `Idempotency-Key` never runs a second restore; reuse with different content returns `409`.
- [ ] A fixture non-terminal `execucao_preventiva` row causes restore to be refused with no mutation.
- [ ] A simulated mid-sequence migration failure leaves the database at the last successfully committed version, with startup halting on a clear, identifiable error.
- [ ] Automated tests cover: initial creation, idempotent re-run, future-version rejection, interrupted-migration resume, successful restore, restore blocked by active execution, restore rollback on failure, and `Idempotency-Key` replay/conflict.
