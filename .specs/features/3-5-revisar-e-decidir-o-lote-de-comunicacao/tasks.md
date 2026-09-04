# História 3.5: Revisar e decidir o lote de comunicação — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/3-5-revisar-e-decidir-o-lote-de-comunicacao/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`; piso em `testes/test_repositorio_regras.py` (2.4, concorrência otimista) e `testes/test_restauracao.py` (Épico 1, transação única tudo-ou-nada).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Migração `0011_decisoes_humanas.sql` | integration | Aplicação, tabela nova | `testes/test_migracoes.py` | `uv run --directory src/backend pytest` |
| `RepositorioDecisoesHumanas` | integration | Salvar/obter, resultado distinto da avaliação crítica | `testes/test_repositorio_decisoes_humanas.py` | `uv run --directory src/backend pytest` |
| `ServicoRevisaoLote.obter_lote` | unit | Ordenação por atenção; 1:1 com `REVISAO-01..04` | `testes/test_revisao_lote.py` | `uv run --directory src/backend pytest` |
| `ServicoRevisaoLote.decidir_lote` | unit | Todos os branches; 1:1 com `REVISAO-05..14`; justificativa obrigatória, limite de tentativas, guarda de regeneração ativa, atomicidade, conclusão vs. confirmação | `testes/test_revisao_lote.py` | `uv run --directory src/backend pytest` |
| Roteador HTTP (lote e decisão) | integration | `GET` do lote + `POST` de decisão individual/lote: caminho feliz + cada erro + `409` de conflito | `testes/test_revisao_lote_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com as rotas novas | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Superfície do revisor e do lote | unit | Seções separadas, validação inline de justificativa, foco/teclado acessíveis | `SuperficieRevisaoLote.test.tsx` | `npm test --prefix src/frontend -- --run` |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick (backend) | Tasks isoladas de aplicação/adaptador | `uv run --directory src/backend pytest` |
| Quick (frontend) | Tasks isoladas de componente | `npm test --prefix src/frontend -- --run` |
| Full (backend) | Tasks de roteador HTTP ou schema | `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` |
| Full (frontend) | Tasks de superfície visível | `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |
| Build (fim de fase) | Fim de fase / contrato | Backend + Frontend em paralelo, mesmos comandos acima |

---

## Execution Plan

### Phase 1: Schema e persistência de decisão

```
T1 → T2
```

### Phase 2: Caso de uso do lote

```
T3 → T4
```

### Phase 3: API

```
T5
```

### Phase 4: Frontend

```
T6
```

---

## Task Breakdown

### T1: Migração `0011_decisoes_humanas.sql` ✅

**What**: Criar `decisoes_humanas`; atualizar `README.md` de persistência.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/migracoes/0011_decisoes_humanas.sql`
**Depends on**: None
**Reuses**: convenção de migração numerada
**Requirement**: REVISAO-07

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Migração aplica em transação própria, registrada em `schema_migracoes`
- [x] `README.md` documenta a tabela nova
- [x] `testes/test_migracoes.py` cobre a aplicação da migração `0013` (renumerada de `0011`)
- [x] Gate check passa: `uv run --directory src/backend pytest` (742 passed)

**Tests**: integration
**Gate**: quick

---

### T2: `RepositorioDecisoesHumanas` ✅

**What**: `salvar`/`obter_por_mensagem`.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_decisoes_humanas.py`
**Depends on**: T1
**Reuses**: padrão de conexão explícita
**Requirement**: REVISAO-07

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] `salvar` persiste perfil, resultado, justificativa (quando aplicável), versão da mensagem
- [x] `obter_por_mensagem` retorna todas as decisões, distintas de `avaliacoes_criticas` (3.3)
- [x] Gate check passa: `uv run --directory src/backend pytest` (756 passed)

**Tests**: integration
**Gate**: quick

---

### T3: `ServicoRevisaoLote.obter_lote` ✅

**What**: Monta o lote (evento, regra, público, distribuição por canal, aprovações agênticas, exceções) ordenado com itens de atenção primeiro.
**Where**: `src/backend/central_preventiva/aplicacao/revisao_lote.py`
**Depends on**: None
**Reuses**: `RepositorioMensagens`, `RepositorioAvaliacoesCriticas` (3.3), `RepositorioElegibilidades` (2.5)
**Requirement**: REVISAO-01, REVISAO-02, REVISAO-03, REVISAO-04

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Lote com exceções + reprovações históricas + aprovações limpas retorna nessa ordem exata
- [x] Cada item expõe destinatário sintético, conteúdo, versões, verificações determinísticas, avaliações críticas, dados de origem e proveniência
- [x] Gatilho agregado do REVISAO-01 implementado em `ServicoGeracaoMensagens.abrir_revisao_se_lote_completo` (SPEC_DEVIATION documentado no módulo): nenhuma task o atribuía, e sem ele a execução nunca sairia de `processando_mensagens`
- [x] Gate check passa: `uv run --directory src/backend pytest` (781 passed)

**Tests**: unit
**Gate**: quick

---

### T4: `ServicoRevisaoLote.decidir_lote` ✅

**What**: Aplica decisões (aprovar/rejeitar/excluir/regenerar) numa única transação; regenerar reusa `incrementar_tentativa`+reentrada em `gerar` (3.4); após aplicar, decide `concluida`/`aguardando_confirmacao` com base no estado real das mensagens.
**Where**: `src/backend/central_preventiva/aplicacao/revisao_lote.py` (mesmo arquivo de T3)
**Depends on**: T2, T3
**Reuses**: `RepositorioMensagens.transicionar`/`incrementar_tentativa` (3.2/3.4), `RepositorioExecucaoPreventiva.transicionar` (2.2), `RepositorioIdempotencia`
**Requirement**: REVISAO-05, REVISAO-06, REVISAO-08, REVISAO-09, REVISAO-10, REVISAO-11, REVISAO-12, REVISAO-13, REVISAO-14

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Decisão sem justificativa (rejeitar/excluir/regenerar) é rejeitada antes de qualquer mutação
- [x] Regeneração com `tentativas < 3` transiciona atomicamente para `gerando`, incrementa uma única vez, volta o agregado a `processando_mensagens`
- [x] Regeneração idempotente reenviada com a mesma `Idempotency-Key` não incrementa a tentativa duas vezes
- [x] Mensagem com 3 tentativas: `regenerar` rejeitado com motivo específico, sem afetar as demais decisões válidas do mesmo lote
- [x] Lote com item de `versao_esperada` desatualizada: `409`, nenhuma decisão do lote aplicada (testado verificando que as demais também não foram persistidas)
- [x] Agregado retorna a `aguardando_revisao` só quando nenhuma regeneração permanecer ativa
- [x] Todas decididas sem nenhuma aprovada → `concluida` sem simulação
- [x] Ao menos uma aprovada e todas decididas → `aguardando_confirmacao`, contendo só as aprovadas por crítico e Marina
- [x] Gate check passa: `uv run --directory src/backend pytest` (812 passed)

**Tests**: unit
**Gate**: quick

---

### T5: Roteador HTTP — lote e decisão

**What**: `GET /api/v1/execucoes/{id}/revisao` (lote ordenado) e `POST /api/v1/execucoes/{id}/revisao/decisoes` (lote de decisões, idempotente, `versao_esperada` por item).
**Where**: `src/backend/central_preventiva/adaptadores/http/revisao_lote.py`
**Depends on**: T4
**Reuses**: padrão de roteador existente, fixture `autouse` de bloqueio de rede real
**Requirement**: REVISAO-01, REVISAO-12, REVISAO-13

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] `GET` retorna o lote ordenado com todos os campos do AC
- [ ] `POST` com conflito de versão em qualquer item retorna `409` sem efeito parcial (verificado via `GET` subsequente)
- [ ] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [ ] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T6: Superfície do revisor e do lote

**What**: Lista do lote (itens de atenção primeiro) + revisor individual com destinatário/conteúdo/contexto de IA separados visualmente; ações aprovar/rejeitar/excluir/regenerar com validação inline de justificativa e rascunho preservado; seleção múltipla para decisão em lote; foco/teclado acessíveis.
**Where**: `src/frontend/src/funcionalidades/revisao-lote/SuperficieRevisaoLote.tsx`
**Depends on**: T5
**Reuses**: cliente HTTP central, padrão de formulário validado de `SuperficieRegras` (2.4)
**Requirement**: REVISAO-02, REVISAO-03, REVISAO-04, REVISAO-05, REVISAO-06, REVISAO-09

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Seções destinatário/conteúdo-versionamento/contexto-IA visualmente separadas
- [ ] Rejeitar/excluir/regenerar sem justificativa bloqueia inline; rascunho preservado ao navegar sem confirmar
- [ ] Ação "regenerar" indisponível com explicação acessível quando `tentativas = 3`
- [ ] Nenhum campo de edição de texto da mensagem existe na interface
- [ ] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(revisao): adicionar revisao humana e decisao em lote das mensagens`

---

## Phase Execution Map

```
Phase 1:  T1 → T2
Phase 2:  T3 → T4
Phase 3:  T5
Phase 4:  T6
```

Grafo completo de dependências:

```
T1 → T2
T2 → T4
T3 → T4
T4 → T5
T5 → T6
```

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Migração `0011` | 1 arquivo `.sql` + doc | ✅ Granular |
| T2: `RepositorioDecisoesHumanas` | 1 componente | ✅ Granular |
| T3: `obter_lote` | 1 método, arquivo novo | ✅ Granular |
| T4: `decidir_lote` | 1 método, mesmo arquivo de T3 | ✅ Granular |
| T5: Roteador de revisão | 1 componente | ✅ Granular |
| T6: Superfície do revisor | 1 componente | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | — | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | None | — | ✅ Match |
| T4 | T2, T3 | T2 → T4, T3 → T4 (grafo completo) | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |

**Rules confirmed**: toda dependência aponta para trás ou dentro da mesma fase.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: Migração `0011` | Migração/schema | integration | integration | ✅ OK |
| T2: `RepositorioDecisoesHumanas` | Repositório | integration | integration | ✅ OK |
| T3: `obter_lote` | Aplicação | unit | unit | ✅ OK |
| T4: `decidir_lote` | Aplicação | unit | unit | ✅ OK |
| T5: Roteador de revisão | Roteador HTTP | integration | integration | ✅ OK |
| T6: Superfície do revisor | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: nenhum `Tests: none` nesta história; nenhuma task adia teste.
