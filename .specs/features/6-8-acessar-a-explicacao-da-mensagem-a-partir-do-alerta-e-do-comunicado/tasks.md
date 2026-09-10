# História 6.8: Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/6-8-acessar-a-explicacao-da-mensagem-a-partir-do-alerta-e-do-comunicado/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Generated from codebase sampling (`repositorio_entregas_simuladas.py`/`test_repositorio_entregas_simuladas.py`, `alerta_segurado.py`/`test_alerta_segurado.py`, `lista_alertas_segurado.py`/`test_lista_alertas_segurado_api.py`, `SuperficieAlertas.test.tsx`, `SuperficieComunicado.test.tsx`, `.specs/LESSONS.md`). Guidelines found: `.specs/LESSONS.md` (todo módulo `api/*.ts` precisa de teste próprio para `snake_case`→`camelCase`; montar toda região `aria-live` sempre presente e vazia).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Backend — repositório (`RepositorioEntregasSimuladas`) | integration | Elegibilidade com mensagem `simulada_entregue` devolve o id certo; sem mensagem devolve `None`; múltiplas entregas devolve a mais recente | `src/backend/testes/test_repositorio_entregas_simuladas.py` | `uv run --directory src/backend pytest` |
| Backend — aplicação (`ServicoAlertaSegurado`) | unit | `montar_para_registro` popula `entrega_simulada_id` quando a porta devolve um id; `None` quando não devolve | `src/backend/testes/test_alerta_segurado.py` | `uv run --directory src/backend pytest` |
| Backend — HTTP (`RespostaAlerta`, ambos os roteadores) | integration | Campo `entrega_simulada_id` presente e correto na resposta de `GET /alerta-mais-relevante` e de `GET /alertas`/`GET /alertas/{id}` | `src/backend/testes/test_alerta_segurado_api.py`, `src/backend/testes/test_lista_alertas_segurado_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia do campo novo com o snapshot versionado | `src/backend/testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Frontend — api (`alertaSegurado.ts`, `listaAlertasSegurado.ts`) | unit | Tradução `entrega_simulada_id` → `entregaSimuladaId` (presente e `null`) nos dois tradutores | `src/frontend/src/api/alertaSegurado.test.ts`, `src/frontend/src/api/listaAlertasSegurado.test.ts` | `npm test --prefix src/frontend -- --run` |
| Frontend — componente (`SuperficieAlertas`) | unit | Botão só aparece com `entregaSimuladaId` não nulo; abre o drawer com `seguradoId`+`entregaSimuladaId` do alerta certo; fecha ao trocar de segurado (Edge Case) | `src/frontend/src/funcionalidades/segurado/SuperficieAlertas.test.tsx` | `npm test --prefix src/frontend -- --run` |
| Frontend — componente (`SuperficieComunicado`) | unit | Mesmo botão, mesma condição, `entregaSimuladaId` já vindo da prop; fecha ao trocar de segurado | `src/frontend/src/funcionalidades/segurado/SuperficieComunicado.test.tsx` | `npm test --prefix src/frontend -- --run` |

## Gate Check Commands

> Generated from codebase - confirm before Execute.

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick (backend) | Tasks isoladas de repositório/aplicação | `uv run --directory src/backend pytest` |
| Quick (frontend) | Tasks isoladas de api/componente | `npm test --prefix src/frontend -- --run` |
| Full (backend) | Tasks de roteador HTTP ou schema | `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` |
| Full (frontend) | Tasks de superfície visível | `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |
| Build (fim de fase) | Fim de fase | Backend + Frontend em paralelo, mesmos comandos Full acima, mais `npm run verificar-tipos-api --prefix src/frontend` (backend no ar) |

---

## Execution Plan

### Phase 1: Backend — resolver e expor `entrega_simulada_id`

```
T1 → T2 → T3
```

### Phase 2: Frontend — origem "comunicado" (sem dependência de backend)

```
T4
```

### Phase 3: Frontend — origem "alerta" (depende do contrato do backend, Phase 1)

```
T3 → T5 → T6
```

---

## Task Breakdown

### T1: `RepositorioEntregasSimuladas.obter_id_mais_recente_por_elegibilidade`

**What**: Novo método que devolve o `id` da entrega simulada mais recente cuja mensagem de origem está em `simulada_entregue` para a elegibilidade dada, ou `None`.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_entregas_simuladas.py`
**Depends on**: None
**Reuses**: Mesmo JOIN `entregas_simuladas`×`mensagens` de `listar_por_segurado`; mesmo padrão de conexão/leitura do resto do repositório.
**Requirement**: ABRIREXP-01, ABRIREXP-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] Método devolve o id certo quando há uma mensagem `simulada_entregue` para a elegibilidade
- [x] Devolve `None` quando não há nenhuma mensagem, ou a mensagem existe mas não está em `simulada_entregue`
- [x] Com duas mensagens/canais para a mesma elegibilidade, devolve a entrega da mais recente (`criado_em`)
- [x] Gate check passa: `uv run --directory src/backend pytest` (verde, 4 testes novos)

**Tests**: integration
**Gate**: quick

---

### T2: `AlertaSegurado`/`ServicoAlertaSegurado` ganham `entrega_simulada_id`

**What**: `AlertaSegurado` (dataclass) ganha o campo `entrega_simulada_id: UUID | None`; `PortasAlertaSegurado` ganha a porta `entregas: _RepositorioEntregasSimuladas` (protocolo mínimo com o método de T1); `montar_para_registro` resolve o campo via essa porta.
**Where**: `src/backend/central_preventiva/aplicacao/alerta_segurado.py`
**Depends on**: T1
**Reuses**: `montar_para_registro`, já o único ponto que monta `AlertaSegurado` para as duas origens (VISAO 5.1, ALERTAS 5.2).
**Requirement**: ABRIREXP-01, ABRIREXP-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `montar_para_registro` popula `entrega_simulada_id` com o valor devolvido pela porta
- [x] `None` quando a porta devolve `None`
- [x] Gate check passa: `uv run --directory src/backend pytest` (verde)

**Tests**: unit
**Gate**: quick

> **Nota de execução**: T2 sozinho deixa `PortasAlertaSegurado` com um campo obrigatório novo sem que os dois pontos de composição (T3) o preencham — o app real (e a suíte inteira, via `TestClient`) não compõe até T3 também mudar. Mesmo padrão de "Resolving compilation dependencies" de `implement.md`: T2 e T3 foram implementados e verificados juntos (gate completo passou só depois dos dois), mas commitados como um único commit atômico em vez de dois — a divisão em duas tasks continua válida para leitura/rastreabilidade, só a fronteira de commit foi fundida.

---

### T3: `RespostaAlerta` expõe `entrega_simulada_id`; composição dos dois roteadores

**What**: `RespostaAlerta` (schema compartilhado) ganha `entrega_simulada_id: UUID | None`; `_resposta_alerta` (nos dois roteadores, `alerta_segurado.py` e `lista_alertas_segurado.py`) traduz o campo; as duas funções `montar_servico_*` passam a compor `RepositorioEntregasSimuladas` na porta `entregas`. Snapshot OpenAPI regenerado.
**Where**: `src/backend/central_preventiva/adaptadores/http/alerta_segurado.py`, `src/backend/central_preventiva/adaptadores/http/lista_alertas_segurado.py`
**Depends on**: T2
**Reuses**: `_resposta_alerta` já existente nos dois roteadores; `RepositorioEntregasSimuladas` já existente (3.6/5.5), só mais uma instância composta.

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [x] `GET /segurados/{id}/alerta-mais-relevante` inclui `entrega_simulada_id` na resposta (VISAO, fora de escopo de UI, mas o contrato precisa ficar consistente)
- [x] `GET /segurados/{id}/alertas` e `GET /segurados/{id}/alertas/{elegibilidade_id}` incluem `entrega_simulada_id` correto por item
- [x] Snapshot OpenAPI regenerado: `uv run --directory src/backend python -m central_preventiva.composicao.openapi_export`
- [x] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` (1118 testes, 0 ruff, 0 pyright)

**Tests**: integration
**Gate**: full

**Commit**: `feat(alertas): expose entrega_simulada_id on alerta contracts`

---

### T4: `SuperficieComunicado` abre a explicação a partir do comunicado

**What**: Em `SuperficieComunicado`, quando `estadoCarregamento === 'disponivel'`, exibir o botão "Ver como esta mensagem foi criada"; estado local `explicacaoAberta`; montar `SuperficieExplicacaoComunicado` com `seguradoId`/`entregaSimuladaId` (prop já existente) e `onFechar` fechando o estado; `useEffect` fechando o drawer quando `seguradoId` mudar.
**Where**: `src/frontend/src/funcionalidades/segurado/SuperficieComunicado.tsx`
**Depends on**: None
**Reuses**: `SuperficieExplicacaoComunicado` (5.4) sem alteração; `entregaSimuladaId` já é prop obrigatória do componente.
**Requirement**: ABRIREXP-04, ABRIREXP-05, ABRIREXP-06, ABRIREXP-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Botão sempre visível quando o comunicado carrega com sucesso (a prop já garante um `entregaSimuladaId` válido)
- [ ] Acioná-lo abre o drawer com `seguradoId`/`entregaSimuladaId` daquele comunicado
- [ ] Fechar o drawer devolve o foco ao botão
- [ ] Trocar `seguradoId` com o drawer aberto o fecha (Edge Case da spec)
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(comunicado): open message explanation from SuperficieComunicado`

---

### T5: `api/alertaSegurado.ts`/`api/listaAlertasSegurado.ts` traduzem `entregaSimuladaId`

**What**: Regenerar `api/tipos-gerados.ts` (backend no ar) e `openapi.json`; `AlertaSegurado` (tipo TS) ganha `entregaSimuladaId: string | null`; os dois tradutores (`paraAlertaSegurado` em `alertaSegurado.ts`, `paraAlerta` em `listaAlertasSegurado.ts`) mapeiam o campo novo.
**Where**: `src/frontend/src/api/alertaSegurado.ts`, `src/frontend/src/api/listaAlertasSegurado.ts`, `src/frontend/src/api/tipos-gerados.ts` (gerado)
**Depends on**: T3
**Reuses**: Mesmo padrão `snake_case → camelCase` de todo campo já existente nos dois tradutores.
**Requirement**: ABRIREXP-01, ABRIREXP-03

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] `npm run gerar-tipos-api --prefix src/frontend` executado com o backend no ar; `tipos-gerados.ts` atualizado
- [ ] Os dois tradutores mapeiam `entrega_simulada_id` → `entregaSimuladaId`, presente e `null`
- [ ] `npm run verificar-tipos-api --prefix src/frontend` sem divergência
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run`

**Tests**: unit
**Gate**: quick

---

### T6: `SuperficieAlertas` abre a explicação a partir do detalhe do alerta

**What**: No detalhe do alerta (`estadoDetalhe === 'pronto' && detalhe`), exibir o botão "Ver como esta mensagem foi criada" só quando `detalhe.alerta.entregaSimuladaId` não for nulo; estado local `explicacaoAberta`; montar `SuperficieExplicacaoComunicado`; fechar ao trocar `seguradoId`.
**Where**: `src/frontend/src/funcionalidades/segurado/SuperficieAlertas.tsx`
**Depends on**: T5
**Reuses**: `SuperficieExplicacaoComunicado` sem alteração; `idSeguradoResolvidoRef`/`seguradoId` já resolvidos pela superfície.
**Requirement**: ABRIREXP-01, ABRIREXP-02, ABRIREXP-03, ABRIREXP-06, ABRIREXP-07

**Tools**:

- MCP: NONE
- Skill: NONE

**Done when**:

- [ ] Botão aparece só quando o alerta selecionado tem `entregaSimuladaId` não nulo (Edge Case: alertas distintos do mesmo segurado abrem a explicação certa cada um)
- [ ] Botão ausente quando `entregaSimuladaId` é `null` (alerta `ainda_nao_simulado`)
- [ ] Acioná-lo abre o drawer com `seguradoId`/`entregaSimuladaId` do alerta selecionado
- [ ] Fechar o drawer devolve o foco ao botão daquele alerta
- [ ] Trocar `seguradoId` com o drawer aberto o fecha (Edge Case da spec)
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: build

**Commit**: `feat(alertas): open message explanation from alert detail`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3

Phase 1:  T1 → T2 → T3
Phase 2:  T4
Phase 3:  T3 → T5 → T6
```

Execution is strictly sequential - one agent, one task at a time, in order. Phase 2 (T4) has no dependency on Phase 1 and could run first or interleaved; it is sequenced after Phase 1 only to keep the backend contract change and its consumers close together in the commit history.

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: `obter_id_mais_recente_por_elegibilidade` | 1 method, 1 file | ✅ Granular |
| T2: `AlertaSegurado`/`ServicoAlertaSegurado` extend | 1 file (dataclass + 1 method) | ✅ Granular |
| T3: `RespostaAlerta` + 2 roteadores' composição | 2 files, 1 cohesive contract change | ✅ OK (cohesive — same field, same commit) |
| T4: `SuperficieComunicado` button + drawer | 1 component | ✅ Granular |
| T5: api translators + generated types | 2 hand-written files + 1 generated file, 1 cohesive contract sync | ✅ OK (cohesive — same field) |
| T6: `SuperficieAlertas` button + drawer | 1 component | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | No incoming arrow | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 | None | No incoming arrow (Phase 2 standalone) | ✅ Match |
| T5 | T3 | T3 → T5 (cross-phase, Phase 1 → Phase 3) | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: `obter_id_mais_recente_por_elegibilidade` | Backend — repositório | integration | integration | ✅ OK |
| T2: `AlertaSegurado`/`ServicoAlertaSegurado` | Backend — aplicação | unit | unit | ✅ OK |
| T3: `RespostaAlerta` + roteadores | Backend — HTTP + contrato OpenAPI | integration | integration | ✅ OK |
| T4: `SuperficieComunicado` | Frontend — componente | unit | unit | ✅ OK |
| T5: api translators | Frontend — api | unit | unit | ✅ OK |
| T6: `SuperficieAlertas` | Frontend — componente | unit | unit | ✅ OK |
