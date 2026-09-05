# História 4.2: Inspecionar o resultado individual — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/4-2-inspecionar-o-resultado-individual/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`; piso em `testes/test_avaliacao_elegibilidade.py` (2.5, junção de múltiplas fontes) e `testes/test_prontidao_api.py` (não-enumeração de recurso).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| `ServicoDetalheResultado` | unit | Todos os branches; 1:1 com `DETALHE-01..05`; isolamento entre execuções | `testes/test_detalhe_resultado.py` | `uv run --directory src/backend pytest` |
| Roteador HTTP (detalhe) | integration | Caminho feliz (e-mail/WhatsApp/SMS) + inexistente + de outra execução (resposta idêntica) | `testes/test_detalhe_resultado_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com a rota nova | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Drawer de detalhe (frontend) | unit | Foco preso, `Esc` fecha e devolve foco, sem empilhamento; 3 canais renderizados corretamente | `SuperficieDetalheResultado.test.tsx` | `npm test --prefix src/frontend -- --run` |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick (backend) | Tasks isoladas de aplicação | `uv run --directory src/backend pytest` |
| Quick (frontend) | Tasks isoladas de componente | `npm test --prefix src/frontend -- --run` |
| Full (backend) | Tasks de roteador HTTP | `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` |
| Full (frontend) | Tasks de superfície visível | `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |
| Build (fim de fase) | Fim de fase / contrato | Backend + Frontend em paralelo, mesmos comandos acima |

---

## Execution Plan

### Phase 1: Consulta agregada

```
T1
```

### Phase 2: API e frontend

```
T2 → T3
```

---

## Task Breakdown

### T1: `ServicoDetalheResultado`

**What**: Junta mensagem+versões+avaliações críticas+decisões humanas+entrega simulada+elegibilidade+evento+regra por `mensagem_id`, validando pertencimento a `execucao_id`.
**Where**: `src/backend/central_preventiva/aplicacao/detalhe_resultado.py`
**Depends on**: None
**Reuses**: `RepositorioMensagens` (3.2), `RepositorioAvaliacoesCriticas` (3.3), `RepositorioDecisoesHumanas` (3.5), `RepositorioEntregasSimuladas` (3.6), `RepositorioElegibilidades` (2.5), `RepositorioAvaliacoesRisco` (2.3)
**Requirement**: DETALHE-01, DETALHE-02, DETALHE-03, DETALHE-04, DETALHE-05

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Mensagem de e-mail retorna assunto+corpo, segurado, apólice, canal, horários, estado, evento, versão da regra, aprovação agêntica e humana
- [x] Mensagem de WhatsApp/SMS retorna corpo+limite validado, sem nenhum campo de telefone real
- [x] Mensagem com 3 versões (2 reprovadas + 1 aprovada) retorna as 3 relacionadas às suas críticas/decisões, na ordem correta
- [x] `mensagem_id` de outra `execucao_id` retorna o mesmo resultado (`None`) que um `mensagem_id` inexistente
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T2: Endpoint HTTP de detalhe

**What**: `GET /api/v1/execucoes/{execucao_id}/mensagens/{mensagem_id}/detalhe`.
**Where**: `src/backend/central_preventiva/adaptadores/http/detalhe_resultado.py`
**Depends on**: T1
**Reuses**: padrão de roteador existente
**Requirement**: DETALHE-05

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] `200` com o detalhe completo quando a mensagem pertence à execução
- [ ] `404` `application/problem+json` idêntico para inexistente e para "de outra execução"
- [ ] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [ ] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T3: Drawer de detalhe do resultado individual

**What**: Painel/drawer que exibe o detalhe completo (prévia por canal, versões, aprovações), com foco preso, `Esc` fechando e devolvendo o foco à origem, sem empilhar camada modal adicional.
**Where**: `src/frontend/src/funcionalidades/resultados/SuperficieDetalheResultado.tsx`
**Depends on**: T2
**Reuses**: cliente HTTP central, `Modal`/drawer existente (Épico 1) como base de foco preso
**Requirement**: DETALHE-01, DETALHE-02, DETALHE-03, DETALHE-06, DETALHE-07, DETALHE-08

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Prévia de e-mail mostra assunto+corpo rotulados como simulação; WhatsApp/SMS mostram corpo+limite sem telefone
- [ ] `Tab` não sai do drawer aberto; `Esc` fecha e devolve o foco ao elemento de origem
- [ ] Abrir o drawer a partir de duas origens diferentes nunca empilha uma segunda camada modal
- [ ] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(resultados): adicionar detalhe individual do resultado simulado`

---

## Phase Execution Map

```
Phase 1:  T1
Phase 2:  T2 → T3
```

Grafo completo de dependências:

```
T1 → T2
T2 → T3
```

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: `ServicoDetalheResultado` | 1 caso de uso | ✅ Granular |
| T2: Endpoint de detalhe | 1 componente | ✅ Granular |
| T3: Drawer de detalhe | 1 componente | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | — | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |

**Rules confirmed**: toda dependência aponta para trás ou dentro da mesma fase.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: `ServicoDetalheResultado` | Aplicação | unit | unit | ✅ OK |
| T2: Endpoint de detalhe | Roteador HTTP | integration | integration | ✅ OK |
| T3: Drawer de detalhe | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: nenhum `Tests: none` nesta história; nenhuma task adia teste.
