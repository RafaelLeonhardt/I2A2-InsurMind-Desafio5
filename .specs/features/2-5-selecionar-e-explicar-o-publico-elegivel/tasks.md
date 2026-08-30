# História 2.5: Selecionar e explicar o público elegível — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/2-5-selecionar-e-explicar-o-publico-elegivel/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`; piso em `testes/test_avaliador_risco.py` (2.3, motor puro determinístico).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Migração `0005_elegibilidade.sql` | integration | Aplicação, colunas novas, `UNIQUE` | `testes/test_migracoes.py` | `uv run --directory src/backend pytest` |
| `AvaliadorElegibilidade` | unit | Todos os branches; 1:1 com `ELEG-01..07`; cada critério de exclusão isolado, efeito neutro do canal | `testes/test_avaliador_elegibilidade.py` | `uv run --directory src/backend pytest` |
| `RepositorioCandidatosElegibilidade` / `RepositorioElegibilidades` | integration | Listagem por área; salvar com dedução por `UNIQUE`; contagem | `testes/test_repositorio_elegibilidade.py` | `uv run --directory src/backend pytest` |
| `ServicoAvaliacaoElegibilidade` | unit | Todos os branches; conjunto vazio válido; repetição sem duplicidade | `testes/test_avaliacao_elegibilidade.py` | `uv run --directory src/backend pytest` |
| Roteador HTTP (evento e decisão — público) | integration | `GET` contagem + detalhe: caminho feliz + conjunto vazio | `testes/test_elegibilidade_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com a rota nova | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Superfície "Evento e decisão" (público elegível) | unit | Quantidades, tabela, explicação por linha sem hover | `SuperficieEventoDecisao.test.tsx` (estendido) | `npm test --prefix src/frontend -- --run` |

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

### Phase 1: Schema e motor determinístico

```
T1
T2
```

### Phase 2: Persistência

```
T3
```

### Phase 3: Caso de uso e API

```
T4 → T5
```

### Phase 4: Frontend

```
T6
```

---

## Task Breakdown

### T1: Migração `0005_elegibilidade.sql`

**What**: Estender `elegibilidades_historicas` com `execucao_id`, `criterios`, `canal`, e `UNIQUE(execucao_id, evento_id, regra_id, segurado_id, apolice_id)`.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/migracoes/0005_elegibilidade.sql`
**Depends on**: None
**Reuses**: convenção de migração numerada
**Requirement**: ELEG-04, ELEG-07

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Migração aplica em transação própria, registrada em `schema_migracoes`
- [ ] `README.md` de persistência documenta as colunas novas e a `UNIQUE`
- [ ] `testes/test_migracoes.py` cobre a aplicação da migração `0005`
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T2: `AvaliadorElegibilidade`

**What**: Função pura que avalia área, tipo/situação da apólice, coberturas e participação em alertas, devolvendo `incluido`/`excluido` com critério a critério; canal preferencial preservado sem afetar o resultado.
**Where**: `src/backend/central_preventiva/dominio/avaliador_elegibilidade.py`
**Depends on**: None
**Reuses**: mesmo padrão estrutural de `AvaliadorRisco` (2.3)
**Requirement**: ELEG-01, ELEG-02, ELEG-03

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Segurado+apólice que atendem todos os critérios → `incluido` com todos os critérios satisfeitos
- [ ] Cada critério de exclusão testado isoladamente (área fora, apólice não `ativa`, cobertura ausente, `participa_de_alertas = false`) produz `excluido` com o motivo específico
- [ ] Canal preferencial diferente não muda o resultado de inclusão/exclusão
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T3: `RepositorioCandidatosElegibilidade` e `RepositorioElegibilidades`

**What**: Listar candidatos por área; salvar resultado com dedução por `UNIQUE`; contar e listar por execução.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_elegibilidade.py`
**Depends on**: T1
**Reuses**: padrão de conexão explícita
**Requirement**: ELEG-05, ELEG-06

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] `listar_candidatos` retorna todos os segurados+apólices da área informada
- [ ] `salvar` chamado duas vezes para a mesma combinação produz uma única linha (violação de `UNIQUE` tratada como no-op, não erro não tratado)
- [ ] `contar_por_execucao` retorna quantidades corretas de incluídos/excluídos
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T4: `ServicoAvaliacaoElegibilidade`

**What**: Orquestra candidatos → `AvaliadorElegibilidade` → `RepositorioElegibilidades.salvar` para cada combinação; devolve contagem final.
**Where**: `src/backend/central_preventiva/aplicacao/avaliacao_elegibilidade.py`
**Depends on**: T2, T3
**Reuses**: nenhuma porta de IA
**Requirement**: ELEG-04, ELEG-08

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Evento sem nenhum candidato elegível retorna conjunto vazio válido, sem erro e sem chamada de IA
- [ ] Reprocessar a mesma execução não duplica nenhum resultado
- [ ] Snapshots (segurado, apólice, evento, regra) preservados mesmo que dados originais mudem depois
- [ ] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T5: Endpoint HTTP do público elegível

**What**: `GET /api/v1/execucoes/{execucao_id}/elegibilidade` retornando quantidades e a lista com segurado, apólice, localização, canal e resultado; `GET .../elegibilidade/{id}` com a explicação completa por critério.
**Where**: `src/backend/central_preventiva/adaptadores/http/elegibilidade.py`
**Depends on**: T4
**Reuses**: padrão de roteador existente
**Requirement**: ELEG-08, ELEG-09

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] `200` com quantidades e lista completa
- [ ] Conjunto vazio retorna `200` com lista vazia, não erro
- [ ] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [ ] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T6: Superfície "Evento e decisão" — público elegível

**What**: Estender `SuperficieEventoDecisao` (2.3) com quantidades de incluídos/excluídos, tabela do público e explicação por linha (regra/versão, operando, valor, resultado, justificativa) acessível sem hover.
**Where**: `src/frontend/src/funcionalidades/evento-decisao/SuperficieEventoDecisao.tsx` (extensão)
**Depends on**: T5
**Reuses**: componente de 2.3
**Requirement**: ELEG-08, ELEG-09

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Quantidades e tabela exibidas com segurado sintético, apólice, localização, canal, resultado
- [ ] Explicação de cada linha acessível por teclado, sem depender de hover
- [ ] Inclusões/exclusões distinguíveis por texto+ícone+cor
- [ ] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados
- [ ] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(elegibilidade): adicionar avaliacao e explicacao do publico elegivel`

---

## Phase Execution Map

```
Phase 1:  T1   T2
Phase 2:  T3
Phase 3:  T4 → T5
Phase 4:  T6
```

Grafo completo de dependências:

```
T1 → T3
T2 → T4
T3 → T4
T4 → T5
T5 → T6
```

(T1 e T2 são independentes entre si na Fase 1.)

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Migração `0005` | 1 arquivo `.sql` + doc | ✅ Granular |
| T2: `AvaliadorElegibilidade` | 1 componente | ✅ Granular |
| T3: Repositórios de elegibilidade | 1 arquivo, mesma família de porta | ⚠️ OK — coesos |
| T4: `ServicoAvaliacaoElegibilidade` | 1 caso de uso | ✅ Granular |
| T5: Endpoint HTTP | 1 componente | ✅ Granular |
| T6: Superfície "Evento e decisão" (extensão) | 1 componente | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | — | ✅ Match |
| T2 | None | — | ✅ Match |
| T3 | T1 | T1 → T3 (grafo completo) | ✅ Match |
| T4 | T2, T3 | T2 → T4, T3 → T4 (grafo completo) | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |
| T6 | T5 | T5 → T6 (grafo completo) | ✅ Match |

**Rules confirmed**: toda dependência aponta para trás ou dentro da mesma fase.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: Migração `0005` | Migração/schema | integration | integration | ✅ OK |
| T2: `AvaliadorElegibilidade` | Domínio (motor) | unit | unit | ✅ OK |
| T3: Repositórios | Repositório | integration | integration | ✅ OK |
| T4: `ServicoAvaliacaoElegibilidade` | Aplicação | unit | unit | ✅ OK |
| T5: Endpoint HTTP | Roteador HTTP | integration | integration | ✅ OK |
| T6: Superfície (extensão) | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: nenhum `Tests: none` nesta história; nenhuma task adia teste.
