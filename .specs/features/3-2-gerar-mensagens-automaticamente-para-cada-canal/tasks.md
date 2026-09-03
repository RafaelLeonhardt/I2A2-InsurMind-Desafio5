# História 3.2: Gerar mensagens automaticamente para cada canal — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/3-2-gerar-mensagens-automaticamente-para-cada-canal/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`; piso em `testes/test_avaliador_risco.py` (motor determinístico puro) e `testes/test_coletor_com_retry.py` (retry com dublê). Chamadas ao `ChatOpenAI` SEMPRE testadas com um dublê (`FakeChatModel`/transporte falso do LangChain, ou um `AgenteRedator` falso implementando a mesma interface) — nunca rede real.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Migração `0008_mensagens.sql` | integration | Aplicação, tabelas novas, `UNIQUE` | `testes/test_migracoes.py` | `uv run --directory src/backend pytest` |
| `dominio/estados_mensagem.py` | none | Enum sem lógica própria, mesmo piso de `estados_execucao.py` | — | build gate only |
| `ValidadorSaidaCanal` | unit | Todos os branches; 1:1 com `GERAR-01..03,07..09`; fronteiras exatas por canal | `testes/test_validador_saida_canal.py` | `uv run --directory src/backend pytest` |
| `AgenteRedator` | unit | Chamada estruturada por canal, com dublê do `ChatOpenAI` (sem rede real) | `testes/test_agente_redator.py` | `uv run --directory src/backend pytest` |
| `GrafoGeracaoMensagem` (LangGraph) | unit | Nó `gerar`: sucesso, falha de transporte esgotada, saída inválida — grafo compilado testado com dublês | `testes/test_grafo_geracao_mensagem.py` | `uv run --directory src/backend pytest` |
| `RepositorioMensagens` | integration | Criar (com `UNIQUE`), salvar versão, transicionar (concorrência otimista) | `testes/test_repositorio_mensagens.py` | `uv run --directory src/backend pytest` |
| `ServicoGeracaoMensagens` | unit | Todos os branches; 1:1 com `GERAR-04..06,10..12`; contexto ausente isolado | `testes/test_geracao_mensagens.py` | `uv run --directory src/backend pytest` |
| Roteador HTTP (consulta de mensagens) | integration | `GET` de mensagens por execução, reidratação sem reenvio | `testes/test_mensagens_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com a rota nova | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Superfície de acompanhamento da geração | unit | Progresso reconstruído dos dados persistidos ao reidratar, sem duplicar | `SuperficieGeracaoMensagens.test.tsx` | `npm test --prefix src/frontend -- --run` |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick (backend) | Tasks isoladas de domínio/aplicação/adaptador | `uv run --directory src/backend pytest` |
| Quick (frontend) | Tasks isoladas de componente | `npm test --prefix src/frontend -- --run` |
| Full (backend) | Tasks de roteador HTTP ou schema | `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` |
| Full (frontend) | Tasks de superfície visível | `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |
| Build (fim de fase) | Fim de fase / contrato | Backend + Frontend em paralelo, mesmos comandos acima |

---

## Execution Plan

### Phase 1: Schema e domínio

```
T1
T2
```

### Phase 2: Agente e grafo

```
T3
T4 → T5
```

### Phase 3: Persistência e caso de uso

```
T6 → T7
```

### Phase 4: API e frontend

```
T8 → T9
```

---

## Task Breakdown

### T1: Migração `0008_mensagens.sql`

**What**: Criar `mensagens` (com `UNIQUE(elegibilidade_id, canal)`) e `versoes_mensagem`; atualizar `README.md` de persistência.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/migracoes/0008_mensagens.sql`
**Depends on**: None
**Reuses**: convenção de migração numerada
**Requirement**: GERAR-06

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Migração aplica em transação própria, registrada em `schema_migracoes`
- [x] `README.md` documenta as duas tabelas e a `UNIQUE`
- [x] `testes/test_migracoes.py` cobre a aplicação da migração `0008`
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

**Status**: ✅ Completo — a migração entrou como `0010_mensagens.sql`, não `0008`: `0008` e `0009`
já foram consumidos pelas Histórias 2.6 e 3.1 depois do planejamento desta história (mesma
renumeração já registrada desde a 2.4). Gate: 528 testes.

---

### T2: `dominio/estados_mensagem.py`

**What**: `EstadoMensagem` (StrEnum) com os 9 estados do segundo diagrama do AD-4; `ESTADOS_TERMINAIS_MENSAGEM`; `eh_terminal_mensagem`.
**Where**: `src/backend/central_preventiva/dominio/estados_mensagem.py`
**Depends on**: None
**Reuses**: padrão de `dominio/estados_execucao.py` (AD-004)
**Requirement**: GERAR-09

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Os 9 valores batem exatamente com o diagrama do AD-4 (`ARCHITECTURE-SPINE.md`)
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: none
**Gate**: quick

---

### T3: `ValidadorSaidaCanal`

**What**: Valida campos obrigatórios e limite de caracteres Unicode por canal, usando os limites de `Configuracao`.
**Where**: `src/backend/central_preventiva/dominio/validador_saida_canal.py`
**Depends on**: None
**Reuses**: nenhum — primeiro validador de canal
**Requirement**: GERAR-01, GERAR-02, GERAR-03, GERAR-07, GERAR-08

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] WhatsApp/SMS: corpo ausente ou vazio → inválido; corpo no limite exato → válido; corpo 1 caractere acima → inválido
- [ ] E-mail: mesmas fronteiras aplicadas separadamente a assunto e corpo
- [ ] Novos campos de limite adicionados a `Configuracao` com defaults documentados no `.env.example`
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T4: `AgenteRedator`

**What**: Chama `ChatOpenAI(model=..., temperature=...).with_structured_output(schema_do_canal)` com o contexto mínimo, devolvendo `SaidaWhatsApp`/`SaidaSMS`/`SaidaEmail`.
**Where**: `src/backend/central_preventiva/adaptadores/ia/agente_redator.py`
**Depends on**: None
**Reuses**: `Configuracao` (3.1)
**Requirement**: GERAR-07, GERAR-08

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Testado com um dublê do `ChatOpenAI` (sem rede real) para cada um dos 3 canais
- [ ] Schema de saída por canal é um Pydantic model distinto (WhatsApp/SMS: `corpo`; e-mail: `assunto`+`corpo`)
- [ ] Exceção de transporte não é capturada aqui — propagada ao chamador (o wrapper de retry decide)
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T5: `GrafoGeracaoMensagem` (LangGraph)

**What**: `StateGraph` com o nó `gerar`: chama `AgenteRedator` via `RetryComBackoff` (3.1); em falha de transporte esgotada, resultado indica `falhou_integracao_ia`; em saída recebida, aplica `ValidadorSaidaCanal` e retorna resultado válido/inválido.
**Where**: `src/backend/central_preventiva/aplicacao/grafos/geracao_mensagem.py`
**Depends on**: T3, T4
**Reuses**: `RetryComBackoff[T]` (3.1), `AgenteRedator`, `ValidadorSaidaCanal`
**Requirement**: GERAR-05, GERAR-09

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Sucesso na 1ª chamada de transporte com saída válida retorna resultado "válido"
- [ ] Falha de transporte esgotando `RetryComBackoff` retorna resultado "falhou_integracao_ia" sem levantar exceção não tratada
- [ ] Saída estruturalmente inválida ou acima do limite retorna resultado "inválido" com motivo
- [ ] Nenhum teste chama a OpenAI real
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T6: `RepositorioMensagens`

**What**: `criar` (respeitando `UNIQUE`), `salvar_versao`, `transicionar` (concorrência otimista + `eh_terminal_mensagem`).
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_mensagens.py`
**Depends on**: T1, T2
**Reuses**: padrão de concorrência otimista de `RepositorioExecucaoPreventiva` (2.2)
**Requirement**: GERAR-06, GERAR-09

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] `criar` duas vezes para a mesma elegibilidade+canal viola `UNIQUE` (tratado como erro específico, não exceção genérica)
- [ ] `salvar_versao` persiste conteúdo, validade, motivo, duração, modelo, prompt, tokens
- [ ] `transicionar` a partir de um estado terminal de mensagem levanta erro, mesma semântica de `RepositorioExecucaoPreventiva`
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T7: `ServicoGeracaoMensagens`

**What**: Para cada elegibilidade `incluida` da execução, cria a mensagem, roda `GrafoGeracaoMensagem`, persiste versão e transiciona (`criticando` se válida; permanece `gerando` se inválida; `falhou_integracao_ia` se transporte esgotado).
**Where**: `src/backend/central_preventiva/aplicacao/geracao_mensagens.py`
**Depends on**: T5, T6
**Reuses**: `RepositorioElegibilidades.listar_por_execucao` (2.5), `RepositorioContextosAgente` (3.1)
**Requirement**: GERAR-04, GERAR-05, GERAR-06, GERAR-10, GERAR-11, GERAR-12

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Duas elegibilidades incluídas com canais diferentes geram duas mensagens, sem ação manual
- [ ] Cada mensagem gerada permanece associada a execução, elegibilidade, evento (via elegibilidade), regra (via elegibilidade), segurado, apólice, canal
- [ ] Item sem contexto mínimo (3.1) é pulado com exceção isolada, sem chamar a OpenAI
- [ ] Reidratar (chamar `gerar_lote` de novo para uma execução já processada) não duplica nenhuma mensagem
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T8: Endpoint HTTP de consulta de mensagens

**What**: `GET /api/v1/execucoes/{execucao_id}/mensagens` retornando estado, tentativa, canal e versão atual de cada mensagem.
**Where**: `src/backend/central_preventiva/adaptadores/http/mensagens.py`
**Depends on**: T7
**Reuses**: padrão de roteador existente
**Requirement**: GERAR-11, GERAR-12

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] `200` com a lista de mensagens e seus estados/versão atual
- [ ] Chamado antes e depois da geração completa reflete só dados persistidos, nunca estado inventado
- [ ] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [ ] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T9: Superfície de acompanhamento da geração

**What**: Componente que exibe progresso da geração por item (etapa, canal), reconstruído a partir da API a cada carregamento, sem reenviar geração.
**Where**: `src/frontend/src/funcionalidades/geracao-mensagens/SuperficieGeracaoMensagens.tsx`
**Depends on**: T8
**Reuses**: cliente HTTP central, `SuperficieExecucao` (2.6) como referência de layout
**Requirement**: GERAR-11, GERAR-12

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Progresso reconstruído inteiramente da API a cada montagem do componente
- [ ] Nenhuma chamada de geração disparada pelo frontend (só leitura)
- [ ] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(geracao): adicionar agente redator e geracao automatica de mensagens por canal`

---

## Phase Execution Map

```
Phase 1:  T1   T2
Phase 2:  T3   T4 → T5
Phase 3:  T6 → T7
Phase 4:  T8 → T9
```

Grafo completo de dependências:

```
T3 → T5
T4 → T5
T1 → T6
T2 → T6
T5 → T7
T6 → T7
T7 → T8
T8 → T9
```

(T1 e T2 são independentes entre si na Fase 1; T3 e T4 são independentes entre si na Fase 2.)

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Migração `0008` | 1 arquivo `.sql` + doc | ✅ Granular |
| T2: `estados_mensagem.py` | 1 componente | ✅ Granular |
| T3: `ValidadorSaidaCanal` | 1 componente | ✅ Granular |
| T4: `AgenteRedator` | 1 componente | ✅ Granular |
| T5: `GrafoGeracaoMensagem` | 1 componente | ✅ Granular |
| T6: `RepositorioMensagens` | 1 componente | ✅ Granular |
| T7: `ServicoGeracaoMensagens` | 1 caso de uso | ✅ Granular |
| T8: Endpoint HTTP | 1 componente | ✅ Granular |
| T9: Superfície de acompanhamento | 1 componente | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | — | ✅ Match |
| T2 | None | — | ✅ Match |
| T3 | None | — | ✅ Match |
| T4 | None | — | ✅ Match |
| T5 | T3, T4 | T3 → T5, T4 → T5 (grafo completo) | ✅ Match |
| T6 | T1, T2 | T1 → T6, T2 → T6 (grafo completo) | ✅ Match |
| T7 | T5, T6 | T5 → T7, T6 → T7 (grafo completo) | ✅ Match |
| T8 | T7 | T7 → T8 | ✅ Match |
| T9 | T8 | T8 → T9 | ✅ Match |

**Rules confirmed**: toda dependência aponta para trás ou dentro da mesma fase.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: Migração `0008` | Migração/schema | integration | integration | ✅ OK |
| T2: `estados_mensagem.py` | Domínio (enum) | none | none | ✅ OK |
| T3: `ValidadorSaidaCanal` | Domínio | unit | unit | ✅ OK |
| T4: `AgenteRedator` | Adaptador de IA | unit | unit | ✅ OK |
| T5: `GrafoGeracaoMensagem` | Aplicação (grafo) | unit | unit | ✅ OK |
| T6: `RepositorioMensagens` | Repositório | integration | integration | ✅ OK |
| T7: `ServicoGeracaoMensagens` | Aplicação | unit | unit | ✅ OK |
| T8: Endpoint HTTP | Roteador HTTP | integration | integration | ✅ OK |
| T9: Superfície de acompanhamento | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: `Tests: none` só em T2 (enum sem lógica), conforme a matriz; nenhuma task adia teste.
