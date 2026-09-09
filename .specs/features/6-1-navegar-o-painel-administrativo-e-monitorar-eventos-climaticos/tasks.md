# História 6.1: Navegar o painel administrativo e monitorar eventos climáticos — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/6-1-navegar-o-painel-administrativo-e-monitorar-eventos-climaticos/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Generated from codebase sampling (`README.md` §Testes, `src/backend/pyproject.toml` `[tool.pytest.ini_options]`, `src/frontend/package.json` scripts, e `.specs/LESSONS.md`) - confirm before Execute. Guidelines found: `README.md` (comandos de teste/lint/build por stack), `.specs/LESSONS.md` (todo módulo `api/*.ts` precisa de teste próprio para a tradução `snake_case`→`camelCase`; atualizar `test_openapi_sincronizado.py`/`test_saude.py` junto de qualquer mudança de contrato).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Backend — repositório (DuckDB) | unit/integration | Toda query nova cobre caminho com e sem execução vinculada, dedup por evento reavaliado | `src/backend/testes/test_repositorio_meteorologia.py` | `uv run --directory src/backend pytest testes/test_repositorio_meteorologia.py` |
| Backend — rota HTTP | integration | Happy path (com e sem execução) + contrato do campo novo | `src/backend/testes/test_meteorologia_api.py` | `uv run --directory src/backend pytest testes/test_meteorologia_api.py` |
| Backend — contrato OpenAPI/saúde | integration | Snapshot sincronizado após mudança de schema; nenhuma rota nova a listar | `src/backend/testes/test_openapi_sincronizado.py`, `test_saude.py` | `uv run --directory src/backend pytest testes/test_openapi_sincronizado.py testes/test_saude.py` |
| Frontend — contexto (`PerfilContexto`) | unit | Todo `tipo` de topo + ao menos uma superfície de detalhe válida/ inválida por perfil | `src/frontend/src/contexto/PerfilContexto.test.tsx` | `npm run test --prefix src/frontend -- run PerfilContexto` |
| Frontend — componente (`NavegacaoLateral`) | unit | Todos os itens de topo do admin renderizados, nenhum item de detalhe listado | `src/frontend/src/componentes/NavegacaoLateral.test.tsx` | `npm run test --prefix src/frontend -- run NavegacaoLateral` |
| Frontend — composição (`App`) | unit | Cada novo `case` do switch monta o componente esperado | `src/frontend/src/App.test.tsx` | `npm run test --prefix src/frontend -- run App.test` |
| Frontend — `api/*.ts` (tradução snake_case→camelCase) | unit | Campos novos (`execucao_id`→`execucaoId`, `execucao_estado`→`execucaoEstado`) traduzidos e testados nulo/preenchido | `src/frontend/src/api/meteorologia.test.ts` | `npm run test --prefix src/frontend -- run meteorologia` |
| Frontend — componente novo (`SuperficieEventos`) | unit | Estados carregando/disponível/vazio/erro + navegação ao selecionar um evento com execução | `src/frontend/src/funcionalidades/eventos/SuperficieEventos.test.tsx` | `npm run test --prefix src/frontend -- run SuperficieEventos` |

## Gate Check Commands

> Generated from codebase - confirm before Execute.

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick (backend) | Após tasks backend com teste unitário/integração isolado | `uv run --directory src/backend pytest testes/<arquivo>` |
| Quick (frontend) | Após tasks frontend com teste isolado | `npm run test --prefix src/frontend -- run <arquivo>` |
| Full (backend) | Fim da Fase 1 | `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` |
| Full (frontend) | Fim das Fases 2 e 3 | `npm run test --prefix src/frontend && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |
| Build (ambos, fim da história) | Antes do Verifier | Backend: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` — Frontend: `npm run test --prefix src/frontend && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` (rodáveis em paralelo, stacks independentes) |

---

## Execution Plan

Phases are ordered and run sequentially - each phase completes before the next begins, and tasks within a phase execute in order.

### Phase 1: Backend — vínculo evento→execução

```
T1 → T2 → T3
```

### Phase 2: Frontend — contrato de navegação (AD-016)

```
T4 → T5 → T6
```

### Phase 3: Frontend — tela de eventos

```
T7 → T8
```

---

## Task Breakdown

### T1: Adicionar `mapear_execucoes_por_evento()` ao repositório de eventos ✅ Concluída

**What**: Novo método em `RepositorioEventosMeteorologicos` que consulta `avaliacoes_risco JOIN execucao_preventiva` e devolve `dict[UUID, tuple[UUID, str]]` (evento_id → (execucao_id, estado)), mantendo só a avaliação mais recente por evento.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_meteorologia.py`
**Depends on**: None
**Reuses**: Padrão de conexão `abrir_conexao` já usado por todo o arquivo; `QUALIFY ROW_NUMBER() OVER (...)` (sintaxe DuckDB já compatível com o projeto)
**Requirement**: ADMNAV-04

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Método devolve `{}` quando nenhuma avaliação existir
- [ ] Método devolve a execução mais recente quando um evento tiver mais de uma avaliação (caso de reavaliação)
- [ ] Gate check passa: `uv run --directory src/backend pytest testes/test_repositorio_meteorologia.py`
- [ ] Contagem de testes aumenta em pelo menos 3 (vazio, único vínculo, dedup por reavaliação) — sem exclusão silenciosa de testes existentes

**Tests**: unit
**Gate**: quick

---

### T2: Estender `RespostaEvento` e `consultar_eventos` com o vínculo de execução ✅ Concluída

**What**: `RespostaEvento` ganha `execucao_id: UUID | None` e `execucao_estado: str | None`; `consultar_eventos()` combina `eventos_repo.listar()` com `eventos_repo.mapear_execucoes_por_evento()` (T1) para preencher os dois campos, `None` quando o evento não tiver execução.
**Where**: `src/backend/central_preventiva/adaptadores/http/meteorologia.py`
**Depends on**: T1
**Reuses**: `_resposta_evento()` já existente (estendida, não recriada)
**Requirement**: ADMNAV-04, ADMNAV-05

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `GET /api/v1/meteorologia/eventos` devolve `execucao_id`/`execucao_estado` nulos para um evento sem execução e preenchidos para um evento com execução, em teste de API
- [ ] Snapshot OpenAPI regenerado: `uv run --directory src/backend python -m central_preventiva.composicao.openapi_export`
- [ ] Gate check passa: `uv run --directory src/backend pytest testes/test_meteorologia_api.py`
- [ ] Contagem de testes aumenta em pelo menos 2 (com e sem execução associada)

**Tests**: integration
**Gate**: quick

---

### T3: Sincronizar os testes de contrato OpenAPI/saúde ✅ Concluída

**What**: Confirmar que `test_openapi_sincronizado.py` passa contra o snapshot regenerado em T2 e que `test_saude.py` continua correto (nenhuma rota nova foi criada nesta história, só um schema de resposta existente mudou — o `set` de paths de `test_openapi_em_portugues_nao_antecipa_recursos_futuros` não muda; verificado, não modificado, nesta task).
**Where**: `src/backend/testes/test_openapi_sincronizado.py`
**Depends on**: T2
**Reuses**: Nenhuma mudança de código nestes arquivos é esperada — task de verificação/gate, seguindo a lição consolidada de sempre confirmar os dois juntos após mudança de contrato
**Requirement**: ADMNAV-04

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `uv run --directory src/backend pytest testes/test_openapi_sincronizado.py testes/test_saude.py` passa sem alteração de expectativa de rotas
- [ ] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

**Commit**: `feat(meteorologia): expor execucao_id/execucao_estado em GET /eventos`

---

### T4: Estender `Superficie` para union discriminado com payload (AD-016) ✅ Concluída

**What**: `Superficie` em `PerfilContexto.tsx` vira union de `SuperficieTopo` (sem payload) + `SuperficieDetalhe` (com payload, começando por `{ tipo: 'evento-execucao'; execucaoId: string; perfilPai: Perfil }`); `SUPERFICIES_POR_PERFIL` vira `SUPERFICIES_TOPO_POR_PERFIL` (só tipos de topo, incluindo os 5 novos itens do admin: `eventos`, `regras`, `segurados`, `comunicacoes`, `fontes-de-dados` — usados só como itens de navegação por ora, suas telas chegam em 6.2–6.7); `superficieValida` passa a validar também o caso de detalhe (`perfilPai === perfil`).
**Where**: `src/frontend/src/contexto/PerfilContexto.tsx`
**Depends on**: None (independente da Fase 1)
**Reuses**: `ehPerfilValido`, `lerPerfilArmazenado`, mecanismo de `localStorage` — inalterados
**Requirement**: ADMNAV-01, ADMNAV-03

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `selecionarSuperficie({ tipo: 'evento-execucao', execucaoId, perfilPai: 'administrador' })` é aceito pelo tipo
- [ ] `superficieValida` é `true` para uma superfície de detalhe cujo `perfilPai` bate com o perfil ativo, e `false` quando não bate (ex.: sobrevivência após troca de perfil)
- [ ] Gate check passa: `npm run test --prefix src/frontend -- run PerfilContexto`
- [ ] Contagem de testes aumenta em pelo menos 3 (detalhe válido, detalhe inválido após troca de perfil, item de topo novo listado)

**Tests**: unit
**Gate**: quick

---

### T5: Adicionar os 5 itens de navegação de negócio do Administrador ✅ Concluída

**What**: `NavegacaoLateral.tsx` passa a iterar `SUPERFICIES_TOPO_POR_PERFIL[perfil]` (T4) e ganha rótulos/ícones para `eventos` ("Eventos climáticos"), `regras` ("Regras de negócio"), `segurados` ("Segurados"), `comunicacoes` ("Comunicações"), `fontes-de-dados` ("Fontes de dados") — espelhando `adminNav` do protótipo (`docs/design/prototype/src/App.jsx:18`).
**Where**: `src/frontend/src/componentes/NavegacaoLateral.tsx`
**Depends on**: T4
**Reuses**: Estrutura de `ROTULOS`/`IconeSuperficie` já existente, mesma biblioteca de ícones (`@phosphor-icons/react`) já usada nos demais itens
**Requirement**: ADMNAV-01

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Os 5 novos itens aparecem na navegação quando o perfil ativo é Administrador
- [ ] Nenhum item do perfil Segurado aparece cruzado, e vice-versa
- [ ] Gate check passa: `npm run test --prefix src/frontend -- run NavegacaoLateral`
- [ ] Contagem de testes aumenta em pelo menos 2 (itens do admin presentes; nenhum item cruzado)

**Tests**: unit
**Gate**: quick

---

### T6: Montar as novas superfícies no `App.tsx` ✅ Concluída

**What**: `SuperficieAtiva()` ganha o `case` `'evento-execucao'` (monta `SuperficieExecucao` já existente, passando `execucaoId` do payload); os `case`s `'eventos'`, `'regras'`, `'segurados'`, `'comunicacoes'`, `'fontes-de-dados'` recebem um placeholder mínimo ("Em construção — ver Histórias 6.2–6.7") até suas próprias tasks/histórias os implementarem, para que a navegação de T5 nunca leve a uma tela quebrada. `'eventos'` troca do placeholder para `SuperficieEventos` real em T8, quando o componente passa a existir — não aqui, para não criar uma dependência circular (T6 não pode importar um componente que só nasce em T8).
**Where**: `src/frontend/src/App.tsx`
**Depends on**: T4, T5
**Reuses**: `SuperficieExecucao` (`funcionalidades/execucao/SuperficieExecucao.tsx`) sem nenhuma alteração nele
**Requirement**: ADMNAV-02

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Selecionar qualquer um dos 5 itens de negócio troca a superfície ativa sem erro
- [ ] Uma superfície `{ tipo: 'evento-execucao', execucaoId }` monta `SuperficieExecucao` com o `execucaoId` correto
- [ ] Os 5 itens ainda não implementados (`eventos` incluído, por ora) mostram o placeholder, nunca uma tela em branco ou erro
- [ ] Gate check passa: `npm run test --prefix src/frontend -- run App.test`
- [ ] Contagem de testes aumenta em pelo menos 2 (placeholder para 'eventos'; montagem de 'evento-execucao' com o id correto)

**Tests**: unit
**Gate**: quick

---

### T7: Estender `api/meteorologia.ts` com o vínculo de execução ✅ Concluída

**What**: Após regenerar `src/frontend/src/api/tipos-gerados.ts` (backend rodando localmente, `npm run gerar-tipos-api --prefix src/frontend`, conforme T2), `EventoMeteorologico` (tipo) e `paraEvento()` em `api/meteorologia.ts` ganham `execucaoId: string | null` e `execucaoEstado: string | null`, traduzidos de `execucao_id`/`execucao_estado`.
**Where**: `src/frontend/src/api/meteorologia.ts`
**Depends on**: T3 (schema do backend precisa estar fechado e com snapshot OpenAPI regenerado antes de gerar os tipos)
**Reuses**: `getEventos()`, `paraEvento()`, `clienteApi` já existentes — só estendidos, não recriados
**Requirement**: ADMNAV-04

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] `npm run verificar-tipos-api --prefix src/frontend` passa (tipos versionados batem com o contrato ao vivo do backend)
- [ ] `paraEvento()` traduz `execucao_id: null` para `execucaoId: null` e um UUID presente para a string correspondente
- [ ] Gate check passa: `npm run test --prefix src/frontend -- run meteorologia`
- [ ] Contagem de testes aumenta em pelo menos 2 (evento com execução; evento sem execução)

**Tests**: unit
**Gate**: quick

---

### T8: Criar `SuperficieEventos` (lista de eventos climáticos) ✅ Concluída

**What**: Novo componente que chama `getEventos()` (T7), exibe cada evento (tipo, área, severidade derivada da intensidade, `execucaoEstado` ou "Sem execução iniciada"), com estados `carregando`/`disponivel`/`vazio`/`erro`, e uma ação por linha com execução associada que chama `selecionarSuperficie({ tipo: 'evento-execucao', execucaoId, perfilPai: 'administrador' })`. Substitui o placeholder do `case 'eventos'` em `App.tsx` (deixado por T6) pelo componente real, agora que ele existe.
**Where**: `src/frontend/src/funcionalidades/eventos/SuperficieEventos.tsx` (pasta nova), `src/frontend/src/App.tsx` (troca o placeholder de `'eventos'`)
**Depends on**: T6, T7
**Reuses**: Padrão de estados nomeados já usado em `SuperficieFonteMeteorologica`/`SuperficieApolice`; `usePerfilContexto` (T4)
**Requirement**: ADMNAV-04, ADMNAV-05, ADMNAV-06, ADMNAV-07

**Tools**:
- MCP: NONE
- Skill: NONE

**Done when**:
- [ ] Lista renderiza cada evento com tipo, área e status da execução (ou "Sem execução iniciada")
- [ ] Selecionar um evento com execução associada chama `selecionarSuperficie` com o `execucaoId` correto
- [ ] Estado vazio explícito quando a lista de eventos estiver vazia; estado de erro explícito com ação de tentar novamente quando `getEventos()` rejeitar
- [ ] Gate check passa: `npm run test --prefix src/frontend -- run SuperficieEventos`
- [ ] Contagem de testes: pelo menos 5 (carregando, disponível com execução, disponível sem execução, vazio, erro)
- [ ] Full gate passa nos dois stacks: Backend `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` — Frontend `npm run test --prefix src/frontend && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(admin): navegação de negócio do administrador + lista de eventos climáticos`

---

## Phase Execution Map

```
Phase 1 → Phase 2 → Phase 3

Phase 1:  T1 ------→ T2 ------→ T3
Phase 2:  T4 ------→ T5 ------→ T6
Phase 3:  T7 ------→ T8

T4 → T6
T3 → T7
T6 → T8
```

As três últimas linhas são arestas adicionais que não ficam adjacentes no traçado principal acima: `T4 → T6` (T6 depende diretamente de T4, além de T5), `T3 → T7` (T7 só pode gerar os tipos depois do schema/snapshot da Fase 1 fechados em T3 — dependência entre fases), `T6 → T8` (T8 depende diretamente de T6, além de T7).

Execution is strictly sequential - there is no intra-phase parallelism. A single agent works one task at a time, in order. Total: 8 tasks ⇒ fits a single batch (≤ ~8) — execução inline, sem sub-agentes.

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: `mapear_execucoes_por_evento()` | 1 método, 1 arquivo | ✅ Granular |
| T2: Estender `RespostaEvento`/`consultar_eventos` | 1 endpoint, 1 arquivo | ✅ Granular |
| T3: Sincronizar testes de contrato | 2 arquivos de teste, mesma verificação | ✅ Granular (coeso) |
| T4: `Superficie` com payload | 1 tipo + 1 contexto, 1 arquivo | ✅ Granular |
| T5: 5 itens de navegação | 1 componente, 1 arquivo | ✅ Granular |
| T6: Montar superfícies no `App.tsx` | 1 arquivo (switch) | ✅ Granular |
| T7: Estender `api/meteorologia.ts` | 1 arquivo (tipo + tradutor) | ✅ Granular |
| T8: Criar `SuperficieEventos` | 1 componente novo | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | (início da Fase 1) | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 | None | (início da Fase 2) | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |
| T6 | T4, T5 | T5 → T6 e T4 → T6 (aresta adicional) | ✅ Match |
| T7 | T3 | T3 → T7 (aresta adicional, entre fases) | ✅ Match |
| T8 | T6, T7 | T7 → T8 e T6 → T8 (aresta adicional) | ✅ Match |

**Nota**: T7 depende de T3 (Fase 1) porque os tipos gerados só podem ser regenerados depois que o schema do backend estiver fechado e o snapshot OpenAPI atualizado — uma dependência entre fases, explicitada como aresta adicional na Phase Execution Map acima.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: `mapear_execucoes_por_evento()` | Backend — repositório | unit/integration | unit | ✅ OK |
| T2: `RespostaEvento`/`consultar_eventos` | Backend — rota HTTP | integration | integration | ✅ OK |
| T3: contrato OpenAPI/saúde | Backend — contrato OpenAPI/saúde | integration | integration | ✅ OK |
| T4: `Superficie` com payload | Frontend — contexto | unit | unit | ✅ OK |
| T5: itens de navegação | Frontend — componente (`NavegacaoLateral`) | unit | unit | ✅ OK |
| T6: `App.tsx` | Frontend — composição (`App`) | unit | unit | ✅ OK |
| T7: `api/meteorologia.ts` | Frontend — `api/*.ts` | unit | unit | ✅ OK |
| T8: `SuperficieEventos` | Frontend — componente novo | unit | unit | ✅ OK |
