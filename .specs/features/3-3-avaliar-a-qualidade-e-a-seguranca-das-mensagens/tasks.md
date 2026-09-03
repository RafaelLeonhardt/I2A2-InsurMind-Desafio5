# História 3.3: Avaliar a qualidade e a segurança das mensagens — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/3-3-avaliar-a-qualidade-e-a-seguranca-das-mensagens/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`; piso em `testes/test_agente_redator.py` e `testes/test_grafo_geracao_mensagem.py` (3.2) — mesmo padrão de dublê para o `ChatOpenAI`.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Migração `0009_avaliacoes_criticas.sql` | integration | Aplicação, tabela nova, `UNIQUE` | `testes/test_migracoes.py` | `uv run --directory src/backend pytest` |
| `AgenteCritico` | unit | Chamada estruturada com dublê do `ChatOpenAI` (sem rede real) | `testes/test_agente_critico.py` | `uv run --directory src/backend pytest` |
| Extensão de `GrafoGeracaoMensagem` (nó `criticar`) | unit | Todos os branches; 1:1 com `CRIT-01..07`; aprovação, reprovação, saída inválida, falha de transporte | `testes/test_grafo_geracao_mensagem.py` (estendido) | `uv run --directory src/backend pytest` |
| `RepositorioAvaliacoesCriticas` | integration | Salvar/obter, `UNIQUE` por versão | `testes/test_repositorio_avaliacoes_criticas.py` | `uv run --directory src/backend pytest` |
| Roteador HTTP (detalhe da avaliação) | integration | `GET` do detalhe: caminho feliz + ausência de avaliação | `testes/test_avaliacoes_criticas_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com a rota nova | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Superfície de detalhe da avaliação | unit | Versão, critérios, decisão, motivos, agente, modelo, duração; separação IA/regras determinísticas visível | `SuperficieAvaliacaoCritica.test.tsx` | `npm test --prefix src/frontend -- --run` |

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

### Phase 1: Schema e agente crítico

```
T1
T2
```

### Phase 2: Grafo e persistência

```
T3
T4
```

### Phase 3: API e frontend

```
T5 → T6
```

---

## Task Breakdown

### T1: Migração `0009_avaliacoes_criticas.sql`

**What**: Criar `avaliacoes_criticas` (`UNIQUE(versao_mensagem_id)`); atualizar `README.md` de persistência.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/migracoes/0009_avaliacoes_criticas.sql`
**Depends on**: None
**Reuses**: convenção de migração numerada
**Requirement**: CRIT-06

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Migração aplica em transação própria, registrada em `schema_migracoes`
- [x] `README.md` documenta a tabela nova e a `UNIQUE`
- [x] `testes/test_migracoes.py` cobre a aplicação da migração (renumerada para `0011`: `0009` e
      `0010` já haviam sido consumidas por 3.1 e 3.2 — `SPEC_DEVIATION` registrada no `.sql` e no
      `README.md`)
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T2: `AgenteCritico`

**What**: Chama `ChatOpenAI.with_structured_output(AvaliacaoCritica)` com o conteúdo da mensagem e o contexto mínimo, avaliando os 7 critérios (categorias fechadas).
**Where**: `src/backend/central_preventiva/adaptadores/ia/agente_critico.py`
**Depends on**: None
**Reuses**: `Configuracao`, mesmo padrão estrutural de `AgenteRedator` (3.2)
**Requirement**: CRIT-01, CRIT-02, CRIT-03

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Testado com um dublê do `ChatOpenAI` (sem rede real) para aprovação e para cada uma das 7 categorias de reprovação
- [x] Contexto passado ao agente não contém nenhum campo de risco/elegibilidade/cobertura/limite de canal além do necessário à avaliação de conteúdo (garantido por construção: sem `ValidadorSaidaCanal` na assinatura, sem número de limite no prompt, sem categoria de risco/elegibilidade/cobertura/limite no enum fechado)
- [x] Exceção de transporte propagada sem tratamento (decidida pelo wrapper de retry)
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Decisão de forma do retorno**: `avaliar(...)` devolve `AvaliacaoCritica | None`, não um embrulho
com métricas ao estilo de `RespostaRedator` (3.2). `None` significa "o modelo respondeu, mas a
saída não é interpretável com segurança" (CRIT-07); levantar exceção seria lido pelo
`RetryComBackoff` como falha de transporte (levando a `falhou_integracao_ia`, terminal que o Edge
Case da spec reserva ao transporte) e um sentinel `aprovada = False` seria exatamente a reprovação
estruturada de que CRIT-07 distingue a falha. Não há embrulho porque `avaliacoes_criticas` não
persiste métrica de uso — não há o que carregar junto. `SPEC_DEVIATION` registrada no módulo.

**Tests**: unit
**Gate**: quick

---

### T3: Extensão de `GrafoGeracaoMensagem` — nó `criticar`

**What**: Adicionar o nó `criticar` ao grafo por mensagem (3.2): chama `AgenteCritico` via `RetryComBackoff`; interpreta aprovação/reprovação/saída inválida/falha de transporte.
**Where**: `src/backend/central_preventiva/aplicacao/grafos/geracao_mensagem.py` (extensão de 3.2)
**Depends on**: T2
**Reuses**: `RetryComBackoff[T]` (3.1), `EstadoGrafoMensagem` (3.2)
**Requirement**: CRIT-01, CRIT-04, CRIT-05, CRIT-07

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Saída aprovada resulta em resultado "aprovada" com motivos vazios
- [ ] Saída reprovada resulta em resultado "reprovada" com motivos estruturados por categoria
- [ ] Saída inválida/não interpretável resulta em "falha da tentativa", nunca "aprovada"
- [ ] Falha de transporte esgotada resulta em "falhou_integracao_ia", mesmo tratamento de 3.2
- [ ] Reprovação determinística de 3.2 (mensagem já inválida) nunca chega a este nó — testado que o grafo não invoca `criticar` para uma saída inválida do redator
- [ ] Nenhum teste chama a OpenAI real
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T4: `RepositorioAvaliacoesCriticas` e transição de estado

**What**: `salvar`/`obter_por_versao`; `ServicoGeracaoMensagens` (3.2) estendido para, após aprovação do crítico, transicionar a mensagem para `aguardando_revisao` via `RepositorioMensagens.transicionar` (3.2).
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_avaliacoes_criticas.py`, `src/backend/central_preventiva/aplicacao/geracao_mensagens.py` (extensão)
**Depends on**: T1, T3
**Reuses**: `RepositorioMensagens.transicionar` (3.2), sem alteração
**Requirement**: CRIT-05, CRIT-06

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Avaliação aprovada persiste `aprovada=true` e transiciona a mensagem para `aguardando_revisao`
- [ ] Avaliação reprovada persiste `aprovada=false` com motivos, mensagem permanece disponível (sem transicionar para `aguardando_revisao`)
- [ ] `obter_por_versao` recupera a avaliação persistida sem recalcular
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T5: Endpoint HTTP de detalhe da avaliação

**What**: `GET /api/v1/mensagens/{mensagem_id}/versoes/{versao_id}/avaliacao-critica` retornando versão, critérios, decisão, motivos, agente, modelo, duração.
**Where**: `src/backend/central_preventiva/adaptadores/http/avaliacoes_criticas.py`
**Depends on**: T4
**Reuses**: padrão de roteador existente
**Requirement**: CRIT-08, CRIT-09

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] `200` com todos os campos do AC quando a avaliação existe
- [ ] `404`/`application/problem+json` quando a versão ainda não foi avaliada
- [ ] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [ ] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T6: Superfície de detalhe da avaliação crítica

**What**: Componente que exibe versão, critérios, decisão, motivos, agente, modelo, duração, distinguindo visualmente aprovação agêntica de decisão humana futura e separando decisão de IA de regra determinística.
**Where**: `src/frontend/src/funcionalidades/avaliacao-critica/SuperficieAvaliacaoCritica.tsx`
**Depends on**: T5
**Reuses**: cliente HTTP central, padrão de `SuperficieEventoDecisao` (2.3/2.5) para exibição de critérios
**Requirement**: CRIT-06, CRIT-08, CRIT-09

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Todos os campos do AC exibidos em linguagem acessível
- [ ] Aprovação agêntica visualmente distinta de aprovação humana (cor/ícone/rótulo diferentes)
- [ ] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(critica): adicionar agente critico e avaliacao estruturada de mensagens`

---

## Phase Execution Map

```
Phase 1:  T1   T2
Phase 2:  T3   T4
Phase 3:  T5 → T6
```

Grafo completo de dependências:

```
T2 → T3
T1 → T4
T3 → T4
T4 → T5
T5 → T6
```

(T1 e T2 são independentes entre si na Fase 1.)

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Migração `0009` | 1 arquivo `.sql` + doc | ✅ Granular |
| T2: `AgenteCritico` | 1 componente | ✅ Granular |
| T3: Extensão do grafo (nó `criticar`) | 1 arquivo, extensão coesa | ✅ Granular |
| T4: Repositório + transição | 2 arquivos, mesma mudança lógica | ⚠️ OK — coesos |
| T5: Endpoint HTTP | 1 componente | ✅ Granular |
| T6: Superfície de detalhe | 1 componente | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | — | ✅ Match |
| T2 | None | — | ✅ Match |
| T3 | T2 | T2 → T3 (grafo completo) | ✅ Match |
| T4 | T1, T3 | T1 → T4, T3 → T4 (grafo completo) | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |

**Rules confirmed**: toda dependência aponta para trás ou dentro da mesma fase.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: Migração `0009` | Migração/schema | integration | integration | ✅ OK |
| T2: `AgenteCritico` | Adaptador de IA | unit | unit | ✅ OK |
| T3: Extensão do grafo | Aplicação (grafo) | unit | unit | ✅ OK |
| T4: Repositório + transição | Repositório/aplicação | integration | integration | ✅ OK |
| T5: Endpoint HTTP | Roteador HTTP | integration | integration | ✅ OK |
| T6: Superfície de detalhe | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: nenhum `Tests: none` nesta história; nenhuma task adia teste.
