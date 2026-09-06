# História 5.4: Entender como a mensagem foi criada — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/5-4-entender-como-a-mensagem-foi-criada/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`; piso em `testes/test_detalhe_resultado.py` (4.2, junção read-only + não-enumeração).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| `ServicoExplicacaoComunicado` | unit | Todos os branches; 1:1 com `EXPLICACAO-01..05`; lacuna e exceção | `testes/test_explicacao_comunicado.py` | `uv run --directory src/backend pytest` |
| Roteador HTTP (explicação) | integration | Caminho feliz + outro segurado + procedência parcial | `testes/test_explicacao_comunicado_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com a rota nova | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Drawer "Como esta mensagem foi criada" | unit | Separação determinístico/IA, categorias usadas/não usadas, prévia fiel, foco preso, `Esc` | `SuperficieExplicacaoComunicado.test.tsx` | `npm test --prefix src/frontend -- --run` |

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

### T1: `ServicoExplicacaoComunicado`

**What**: Reusa a junção de `ServicoDetalheResultado` (4.2) com verificação de pertencimento por `segurado_id`; rotula seções `DETERMINISTICA`/`AGENTE`; detecta lacuna (`Procedência parcial`/`Exceção`).
**Where**: `src/backend/central_preventiva/aplicacao/explicacao_comunicado.py`
**Depends on**: None
**Reuses**: `ServicoDetalheResultado` (4.2), `RepositorioContextosAgente` (3.1), `RepositorioAvaliacoesCriticas`/`RepositorioDecisoesHumanas` (3.3/3.5)
**Requirement**: EXPLICACAO-01, EXPLICACAO-02, EXPLICACAO-03, EXPLICACAO-04, EXPLICACAO-05

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Explicação de mensagem com 2 tentativas retorna evento/regra rotulados `DETERMINISTICA` e redator/crítico/tentativas/decisão humana rotulados `AGENTE`
- [x] Categorias usadas/não usadas retornadas sem documentos/dados financeiros/pagamentos/credenciais/prompt completo
- [x] Prévia da mensagem final é cópia exata de `entregas_simuladas.apresentacao` (3.6), não recalculada de `versoes_mensagem`
- [x] Lacuna de dado (avaliação crítica intermediária ausente, dado de teste) retorna `Procedência parcial`, sem inferência preenchida
- [x] `obter` de comunicado de outro segurado retorna `None`
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T2: Endpoint HTTP de explicação

**What**: `GET /api/v1/segurados/{segurado_id}/comunicados/{entrega_simulada_id}/explicacao`.
**Where**: `src/backend/central_preventiva/adaptadores/http/explicacao_comunicado.py`
**Depends on**: T1
**Reuses**: padrão de roteador existente
**Requirement**: EXPLICACAO-01

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] `200` com a explicação completa quando pertencer ao segurado
- [x] `404` genérico para comunicado de outro segurado
- [x] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [x] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T3: Drawer "Como esta mensagem foi criada"

**What**: Exibe seções determinístico/IA claramente separadas, categorias de contexto, prévia fiel com aviso "privada, simulada, não é alerta oficial", `Procedência parcial`/`Exceção` quando aplicável; foco preso, `Esc` fecha e devolve foco, título sempre visível, sem segunda camada modal.
**Where**: `src/frontend/src/funcionalidades/segurado/SuperficieExplicacaoComunicado.tsx`
**Depends on**: T2
**Reuses**: cliente HTTP central, `Modal`/drawer existente (Épico 1) como base de foco preso, mesmo padrão de 4.2
**Requirement**: EXPLICACAO-01, EXPLICACAO-02, EXPLICACAO-03, EXPLICACAO-04, EXPLICACAO-05, EXPLICACAO-06, EXPLICACAO-07

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Separação visual determinístico/IA presente em todas as seções
- [x] `Tab` não sai do drawer; `Esc` fecha e devolve o foco à origem; título permanece visível
- [x] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados
- [x] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(segurado): adicionar explicacao de como a mensagem foi criada`

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
| T1: `ServicoExplicacaoComunicado` | 1 caso de uso | ✅ Granular |
| T2: Endpoint de explicação | 1 componente | ✅ Granular |
| T3: Drawer explicativo | 1 componente | ✅ Granular |

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
| T1: `ServicoExplicacaoComunicado` | Aplicação | unit | unit | ✅ OK |
| T2: Endpoint de explicação | Roteador HTTP | integration | integration | ✅ OK |
| T3: Drawer explicativo | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: nenhum `Tests: none` nesta história; nenhuma task adia teste.
