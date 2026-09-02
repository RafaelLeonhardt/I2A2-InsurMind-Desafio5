# História 2.4: Configurar, testar e versionar regras preventivas — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

---

**Design**: `.specs/features/2-4-configurar-testar-e-versionar-regras-preventivas/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`; piso em `testes/test_repositorio_execucao_preventiva.py` (concorrência otimista, 2.2).

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| `ValidadorRegra` | unit | Todos os branches; cada classe de invalidez (tipo, faixa, combinação, coerência evento↔produto) | `testes/test_validador_regra.py` | `uv run --directory src/backend pytest` |
| `RepositorioRegras` (extensão de escrita) | integration | `criar_nova_versao` com versão correta/incorreta (409), histórico preservado | `testes/test_repositorio_regras.py` (estendido) | `uv run --directory src/backend pytest` |
| `ServicoGestaoRegras` | unit | Todos os branches; 1:1 com `REGRA-07..10`; teste determinístico, ativação, idempotência | `testes/test_gestao_regras.py` | `uv run --directory src/backend pytest` |
| Roteador HTTP (regras) | integration | Consulta, teste, ativação: caminho feliz + cada invalidez + 409 concorrência/idempotência | `testes/test_regras_api.py` | `uv run --directory src/backend pytest` |
| Contrato OpenAPI | integration | Sincronia com as rotas novas | `testes/test_openapi_sincronizado.py` | `uv run --directory src/backend pytest` |
| Superfície "Regras" | unit | Tabela, formulário, teste — navegação por teclado, foco visível, erros por campo | `SuperficieRegras.test.tsx` | `npm test --prefix src/frontend -- --run` |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| Quick (backend) | Tasks isoladas de domínio/aplicação/adaptador | `uv run --directory src/backend pytest` |
| Quick (frontend) | Tasks isoladas de componente | `npm test --prefix src/frontend -- --run` |
| Full (backend) | Tasks de roteador HTTP | `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` |
| Full (frontend) | Tasks de superfície visível | `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend` |
| Build (fim de fase) | Fim de fase / contrato | Backend + Frontend em paralelo, mesmos comandos acima |

---

## Execution Plan

### Phase 1: Validação e escrita versionada

```
T1
T2
```

### Phase 2: Caso de uso

```
T3
```

### Phase 3: API

```
T4
```

### Phase 4: Frontend

```
T5
```

---

## Task Breakdown

### T1: `ValidadorRegra`

**What**: Validação de tipos, faixas, combinações obrigatórias e coerência evento↔produto, com mensagens por campo em português brasileiro.
**Where**: `src/backend/central_preventiva/dominio/validador_regra.py`
**Depends on**: None
**Reuses**: nada — primeira validação de regra
**Requirement**: REGRA-05, REGRA-06

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Configuração válida não produz erro
- [x] Cada classe de invalidez (tipo errado, faixa fora do limite, combinação obrigatória ausente, evento↔produto incoerente) produz erro específico com o campo identificado
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T2: `RepositorioRegras` — escrita versionada

**What**: `listar`, `obter_por_id`, `criar_nova_versao` (concorrência otimista por `versao_esperada`, transação única: substitui a anterior e insere a nova ativa).
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_regras.py` (extensão de 2.3)
**Depends on**: None
**Reuses**: padrão de concorrência otimista de `RepositorioExecucaoPreventiva` (2.2)
**Requirement**: REGRA-09, REGRA-11

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] `criar_nova_versao` com `versao_esperada` correta cria nova linha `ativa` e marca a anterior `substituida`, na mesma transação
- [x] `criar_nova_versao` com `versao_esperada` incorreta levanta `ConflitoVersao`, sem mutar nenhuma linha
- [x] `listar`/`obter_por_id` retornam versões anteriores inalteradas
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T3: `ServicoGestaoRegras`

**What**: `testar` (aplica `AvaliadorRisco` de 2.3 a cenários sintéticos do `evento_tipo`) e `ativar` (bloqueia se inválida ou não testada; idempotente).
**Where**: `src/backend/central_preventiva/aplicacao/gestao_regras.py`
**Depends on**: T1, T2
**Reuses**: `AvaliadorRisco` (2.3), `RepositorioIdempotencia`
**Requirement**: REGRA-07, REGRA-08, REGRA-12, REGRA-13

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Configuração inválida bloqueia `testar`/`ativar` com motivo específico, sem criar versão
- [x] `testar` retorna, por cenário sintético, operando/valor observado/resultado/justificativa
- [x] `ativar` após teste válido cria nova versão ativa
- [x] Repetir `ativar` com a mesma `Idempotency-Key` e conteúdo idêntico devolve a resposta registrada; conteúdo diferente retorna `409`
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: unit
**Gate**: quick

---

### T4: Roteador HTTP `regras`

**What**: `GET /api/v1/regras`, `GET /api/v1/regras/{id}`, `POST /api/v1/regras/{id}/testar`, `POST /api/v1/regras/{id}/ativar` (idempotente, `versao_esperada` no corpo).
**Where**: `src/backend/central_preventiva/adaptadores/http/regras.py`
**Depends on**: T3
**Reuses**: padrão de roteador existente, fixture `autouse` de bloqueio de rede real
**Requirement**: REGRA-11, REGRA-12, REGRA-13

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Ativação concorrente com `versao_esperada` desatualizada retorna `409`
- [x] Ativação com `Idempotency-Key` repetida segue o contrato de idempotência
- [x] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [x] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

**Tests**: integration
**Gate**: full

---

### T5: Superfície "Regras"

**What**: Tabela de regras (tipo, severidade, limiar, área, produto, coberturas, antecedência, canal, versão, estado), formulário de edição com erro por campo, painel de teste com resultado por cenário; tudo operável por teclado com foco visível.
**Where**: `src/frontend/src/funcionalidades/regras/SuperficieRegras.tsx`
**Depends on**: T4
**Reuses**: cliente HTTP central, padrão de tabela/formulário existente
**Requirement**: REGRA-01, REGRA-02, REGRA-03, REGRA-04, REGRA-14

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [x] Regra ativa identificada por texto+ícone+indicador, não só cor
- [x] Erro de validação aparece junto ao campo sem descartar os demais valores
- [x] Navegação, edição e confirmação totalmente por teclado, com foco visível
- [x] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados (gerado via `openapi-typescript` direto do `openapi.json` local, sem servidor ao vivo)
- [x] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

**Tests**: unit
**Gate**: full

**Commit**: `feat(regras): adicionar gestao versionada de regras preventivas`

---

## Phase Execution Map

```
Phase 1:  T1   T2
Phase 2:  T3
Phase 3:  T4
Phase 4:  T5
```

Grafo completo de dependências:

```
T1 → T3
T2 → T3
T3 → T4
T4 → T5
```

(T1 e T2 são independentes entre si na Fase 1.)

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: `ValidadorRegra` | 1 componente | ✅ Granular |
| T2: `RepositorioRegras` escrita | 1 arquivo, extensão coesa | ✅ Granular |
| T3: `ServicoGestaoRegras` | 1 caso de uso | ✅ Granular |
| T4: Roteador `regras` | 1 componente | ✅ Granular |
| T5: Superfície "Regras" | 1 componente | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | — | ✅ Match |
| T2 | None | — | ✅ Match |
| T3 | T1, T2 | T1 → T3, T2 → T3 (grafo completo) | ✅ Match |
| T4 | T3 | T3 → T4 | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |

**Rules confirmed**: toda dependência aponta para trás ou dentro da mesma fase.

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: `ValidadorRegra` | Domínio | unit | unit | ✅ OK |
| T2: `RepositorioRegras` escrita | Repositório | integration | integration | ✅ OK |
| T3: `ServicoGestaoRegras` | Aplicação | unit | unit | ✅ OK |
| T4: Roteador `regras` | Roteador HTTP | integration | integration | ✅ OK |
| T5: Superfície "Regras" | Componente React | unit | unit | ✅ OK |

**Rules confirmed**: nenhum `Tests: none` nesta história; nenhuma task adia teste.

---

## Fix Tasks (Verifier Round 1 — FAIL, `validation.md` de 2026-09-02)

O núcleo de segurança (concorrência otimista, coerência AD-013, hash de idempotência) foi mutado e sobreviveu — os gaps eram todos de asserção, não de comportamento em produção. Corrigidas nesta rodada:

- [x] **Fix 1 (Major)** — REGRA-14: nenhuma citação `file:line` para operação por teclado. Adicionado teste em `SuperficieRegras.test.tsx` que foca o botão `Editar` (`toHaveFocus()`), abre o formulário com `keyboard('{Enter}')`, foca o campo e o botão `Testar` e dispara o teste por `{Enter}`, confirmando o painel de resultado — mesmo padrão já usado em `SuperficieFonteMeteorologica.test.tsx`.
- [x] **Fix 2 (Major)** — REGRA-04: mutante sobrevivente (M6) colapsando os dois ícones da tabela no mesmo símbolo. Adicionado `data-icone-nome` distinto em cada ícone (`check-circle`/`clock-counter-clockwise`) e um teste que assere `iconeAtiva !== iconeSubstituida`. Mutação reaplicada manualmente e confirmada morta.
- [x] **Fix 3 (Major)** — REGRA-02: mutante sobrevivente (M5) alargando a faixa de `antecedencia_horas` em uma unidade nos dois extremos. Adicionado teste com os valores imediatamente abaixo (`0`) e acima (`169`) da fronteira `[1, 168]`. Mutação reaplicada e confirmada morta.
- [x] **Fix 4 (Major)** — mutante sobrevivente (M4) removendo o filtro `proveniencia = 'sintetico'` de `listar_sinteticos_por_tipo`. Adicionados dois testes em `test_repositorio_meteorologia.py`: um insere um evento sintético e um real do mesmo tipo e confere que só o sintético volta; outro confere o filtro por `tipo`. Mutação reaplicada e confirmada morta.
- [x] **Fix 5 (Minor)** — REGRA-03: nenhum teste conferia o conjunto de colunas nem os valores derivados da tabela. Adicionado teste que assere as 11 colunas exatas e os valores de severidade/cobertura/antecedência/canal/versão da regra ativa.
- [x] **Fix 6 (Minor)** — a docstring de `ServicoGestaoRegras.ativar` e a `description` publicada no OpenAPI afirmavam "reexecuta o teste determinístico", mas a sonda do Verificador mediu zero chamadas a `avaliar` durante `ativar`. Corrigido pela opção (b): `ativar` agora chama `self.testar(...)` internamente (reuso, não duplicação de lógica) antes de criar a nova versão, tornando a afirmação verdadeira. Novo teste com um `avaliar` espião confirma exatamente 1 chamada por cenário sintético.
- [x] **Fix 7 (Minor)** — REGRA-11 só tinha o caminho equivalente (`versao_esperada` obsoleta), não o cenário literal de duas tentativas com a mesma versão; REGRA-10 não tinha nenhum teste nesta história. Adicionados: um teste HTTP com duas ativações concorrentes usando `versao_esperada=1` e chaves de idempotência distintas (`200` depois `409`); um teste de repositório que salva uma avaliação de risco, ativa uma nova versão da regra e relê a avaliação, confirmando `regra_id`/`regra_versao` inalterados (AD-11).
- [x] **Fix 8 (Minor)** — `GET /regras` e `POST .../testar` asseriam só contagens. Fortalecidas para conferir `estado`/`versao` de cada regra e os valores reais de `valor_observado`/`justificativa` do critério de intensidade.

**Gate check (backend, full)**: `uv run --directory src/backend pytest && ruff check . && pyright` — verde (340 testes). **Gate check (frontend, full)**: `npm test -- --run && npm run lint && npm run build` — verde (189 testes, mesmos avisos pré-existentes).

**Commit**: `fix(regras): fechar lacunas do verificador da historia 2.4`

## Fix Tasks (Verifier Round 2 — FAIL, `validation.md` de 2026-09-02)

Rodada 2 confirmou 7 dos 8 fixes da Rodada 1 genuínos (reinjeção dos mutantes M4/M5/M6 mortos; mutantes novos M7/M8/M9 mortos). Restou 1 lacuna Minor:

- [x] **Fix 9 (Minor)** — REGRA-04: o "indicador visual" (terceiro sinal além de texto+ícone) não tinha nenhuma asserção — `data-indicador` e a classe `regra-estado-badge--{estado}` existiam no componente desde a Rodada 1, mas nunca eram checados no teste. Adicionadas as asserções `toHaveAttribute('data-indicador', ...)` e `toHaveClass('regra-estado-badge--...')` para ambos os estados em `SuperficieRegras.test.tsx`. Mutação de verificação (colapsar as duas badges na mesma classe, sem `data-indicador`) aplicada manualmente e confirmada morta antes de reverter.

**Gate check**: backend 340 testes verde (inalterado); frontend 189 testes verde. **Commit**: `fix(regras): asserir o indicador visual da regra ativa (REGRA-04, Round 2)`
