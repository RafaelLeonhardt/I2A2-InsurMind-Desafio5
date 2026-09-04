# História 3.4: Regenerar mensagens e registrar a proveniência agêntica — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/3-4-regenerar-mensagens-e-registrar-a-proveniencia-agentica/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`; piso em `testes/test_grafo_geracao_mensagem.py` (3.2/3.3) e `testes/test_gerenciador_execucoes.py` (2.6, retomada).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Migração `0010_excecoes_mensagem.sql` | integration | Aplicação, coluna nova | `testes/test_migracoes.py` | `uv run --directory src/backend pytest` |
| Extensão de `RepositorioMensagens` (`incrementar_tentativa`) | integration | Incremento atômico; `LimiteTentativasExcedido` na 4ª tentativa | `testes/test_repositorio_mensagens.py` (estendido) | `uv run --directory src/backend pytest` |
| Extensão de `GrafoGeracaoMensagem` (aresta condicional) | unit | Todos os branches; 1:1 com `REGEN-01..06`; aprovação na 1ª/2ª/3ª tentativa, 3ª reprovação, falha de integração isolada | `testes/test_grafo_geracao_mensagem.py` (estendido) | `uv run --directory src/backend pytest` |
| Extensão de `GerenciadorExecucoes.retomar_pendentes` | integration | Retomada sem repetir tentativa concluída, sem reabrir terminal | `testes/test_gerenciador_execucoes.py` (estendido) | `uv run --directory src/backend pytest` |
| Roteador HTTP (proveniência) | integration | `GET` de proveniência completa por versão/avaliação, sem segredo | `testes/test_proveniencia_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com a rota nova | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Superfície de acompanhamento do ciclo | unit | Etapa, tentativa, limite, foco preservado, texto+ícone além de cor | `SuperficieGeracaoMensagens.test.tsx` (estendido, 3.2) | `npm test --prefix src/frontend -- --run` |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick (backend) | Tasks isoladas de aplicação/adaptador | `uv run --directory src/backend pytest` |
| Quick (frontend) | Tasks isoladas de componente | `npm test --prefix src/frontend -- --run` |
| Full (backend) | Tasks de roteador HTTP, schema ou lifespan | `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` |
| Full (frontend) | Tasks de superfície visível | `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |
| Build (fim de fase) | Fim de fase / contrato | Backend + Frontend em paralelo, mesmos comandos acima |

---

## Execution Plan

### Phase 1: Schema e incremento atômico

```
T1 → T2
```

### Phase 2: Ciclo automático no grafo

```
T3
```

### Phase 3: Retomada e API

```
T4
T5
```

### Phase 4: Frontend

```
T6
```

---

## Task Breakdown

### T1: Migração `0010_excecoes_mensagem.sql` ✅

**What**: Adicionar `mensagem_id` (nulo) a `excecoes_operacionais`; atualizar `README.md` de persistência.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/migracoes/0010_excecoes_mensagem.sql`
**Depends on**: None
**Reuses**: convenção de migração numerada
**Requirement**: REGEN-04

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Migração aplica em transação própria, registrada em `schema_migracoes`
- [x] `README.md` documenta a coluna nova
- [x] `testes/test_migracoes.py` cobre a aplicação da migração `0012` (renumerada de `0010`)
- [x] Gate check passa: `uv run --directory src/backend pytest` (692 passed)

**Tests**: integration
**Gate**: quick

---

### T2: `RepositorioMensagens.incrementar_tentativa` ✅

**What**: Incremento atômico de `tentativa_atual`, com `LimiteTentativasExcedido` se já em 3.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_mensagens.py` (extensão de 3.2)
**Depends on**: T1
**Reuses**: mesma tabela `mensagens`, mesmo padrão de concorrência otimista
**Requirement**: REGEN-02, REGEN-04

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Incremento de 1→2 e 2→3 funciona atomicamente
- [x] Tentativa de incrementar a partir de 3 levanta `LimiteTentativasExcedido`, sem mutar a linha
- [x] Gate check passa: `uv run --directory src/backend pytest` (696 passed)

**Tests**: integration
**Gate**: quick

---

### T3: Extensão de `GrafoGeracaoMensagem` — ciclo automático

**What**: Aresta condicional `criticar`→`gerar` (reprovada e `tentativa < 3`, via `incrementar_tentativa`, motivos passados ao redator) e `criticar`→`falhou_conteudo` (terceira reprovação); `EstadoGrafoMensagem` ganha `motivos_reprovacao_anterior`.
**Where**: `src/backend/central_preventiva/aplicacao/grafos/geracao_mensagem.py` (extensão de 3.2/3.3)
**Depends on**: T2
**Reuses**: nós `gerar`/`criticar` (3.2/3.3), `RepositorioExcecoesOperacionais` (2.2, com `mensagem_id`)
**Requirement**: REGEN-01, REGEN-02, REGEN-03, REGEN-04, REGEN-05, REGEN-06

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Reprovação na tentativa 1 ou 2 incrementa a tentativa e reentra em `gerar` com os motivos da reprovação anterior no contexto
- [ ] Aprovação em qualquer tentativa encerra o ciclo imediatamente, sem tentativa extra
- [ ] Reprovação na tentativa 3 transiciona a mensagem para `falhou_conteudo` e registra `Exceção` correlacionada por `mensagem_id`
- [ ] Falha de transporte esgotada em `gerar` OU em `criticar`, em qualquer tentativa, transiciona só a mensagem afetada para `falhou_integracao_ia`, distinto de `falhou_conteudo`
- [ ] Nenhum teste chama a OpenAI real
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T4: Extensão de `GerenciadorExecucoes.retomar_pendentes`

**What**: Ao retomar uma execução em `processando_mensagens`, identifica mensagens não terminais e continua cada uma do seu último marco durável.
**Where**: `src/backend/central_preventiva/aplicacao/gerenciador_execucoes.py` (extensão de 2.6)
**Depends on**: T3
**Reuses**: `RepositorioExecucaoPreventiva.listar_nao_terminais` (2.6), `RepositorioMensagens`
**Requirement**: REGEN-08, REGEN-09

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Mensagem persistida com tentativa 2 concluída (reprovada) é retomada continuando na tentativa 3, sem repetir a 1 ou 2
- [ ] Mensagem já em estado terminal (`aguardando_revisao`, `falhou_conteudo`, `falhou_integracao_ia`) nunca é reaberta pela retomada
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T5: Endpoint HTTP de proveniência

**What**: `GET /api/v1/mensagens/{mensagem_id}/proveniencia` retornando, por tentativa, agente, modelo, versão do prompt, categorias de entrada, saída, avaliação, duração e métricas de uso.
**Where**: `src/backend/central_preventiva/adaptadores/http/proveniencia.py`
**Depends on**: T4
**Reuses**: `versoes_mensagem`/`avaliacoes_criticas` (3.2/3.3), sem tabela nova
**Requirement**: REGEN-07, REGEN-08

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Resposta inclui todos os campos do AC, por tentativa
- [ ] Nenhum campo de resposta contém chave, contato ou prompt completo
- [ ] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [ ] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T6: Superfície — acompanhamento do ciclo por item

**What**: Estender `SuperficieGeracaoMensagens` (3.2) com etapa, tentativa atual, limite (3), aprovações e exceções por item, sem mover o foco inesperadamente e sem depender só de cor.
**Where**: `src/frontend/src/funcionalidades/geracao-mensagens/SuperficieGeracaoMensagens.tsx` (extensão de 3.2)
**Depends on**: T5
**Reuses**: componente de 3.2
**Requirement**: REGEN-11, REGEN-12

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Tentativa atual e limite exibidos por item, com texto+ícone além de cor
- [ ] Foco do teclado preservado durante atualizações de estado (testado por simulação de foco antes/depois de uma mudança)
- [ ] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(regeneracao): adicionar ciclo automatico de regeneracao e proveniencia agentica`

---

## Phase Execution Map

```
Phase 1:  T1 → T2
Phase 2:  T3
Phase 3:  T4   T5
Phase 4:  T6
```

Grafo completo de dependências:

```
T1 → T2
T2 → T3
T3 → T4
T4 → T5
T5 → T6
```

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Migração `0010` | 1 arquivo `.sql` + doc | ✅ Granular |
| T2: `incrementar_tentativa` | 1 método, mesmo arquivo | ✅ Granular |
| T3: Extensão do grafo | 1 arquivo, extensão coesa | ✅ Granular |
| T4: Extensão da retomada | 1 arquivo | ✅ Granular |
| T5: Endpoint de proveniência | 1 componente | ✅ Granular |
| T6: Superfície do ciclo | 1 componente (extensão) | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | — | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | T2 → T3 (grafo completo) | ✅ Match |
| T4 | T3 | T3 → T4 (grafo completo) | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |

**Rules confirmed**: toda dependência aponta para trás ou dentro da mesma fase.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: Migração `0010` | Migração/schema | integration | integration | ✅ OK |
| T2: `incrementar_tentativa` | Repositório | integration | integration | ✅ OK |
| T3: Extensão do grafo | Aplicação (grafo) | unit | unit | ✅ OK |
| T4: Extensão da retomada | Aplicação/integração | integration | integration | ✅ OK |
| T5: Endpoint de proveniência | Roteador HTTP | integration | integration | ✅ OK |
| T6: Superfície do ciclo | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: nenhum `Tests: none` nesta história; nenhuma task adia teste.
