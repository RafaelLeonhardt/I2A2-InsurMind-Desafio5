# História 5.8: Executar e comprovar os cenários ponta a ponta — Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.** Do not search for skill files by filesystem path. The skill is the source of truth for the full flow (per-task cycle, sub-agent delegation, adequacy review, Verifier, discrimination sensor).

**If the skill cannot be activated, STOP and tell the user - do not proceed without it.**

**Pré-condição de Execute (não de planejamento):** esta história só pode ser executada depois que todos os Épicos 1–4 e as Histórias 5.1–5.7 estiverem implementados — os cenários E2E exercitam o sistema completo. A fase de planejamento (este `tasks.md`) não depende disso.

---

**Design**: `.specs/features/5-8-executar-e-comprovar-os-cenarios-ponta-a-ponta/design.md`
**Status**: Approved

---

## Test Coverage Matrix

> Guidelines: `AGENTS.md`, `README.md`. Esta história é, ela mesma, a camada de verificação do projeto — cada task produz o teste/evidência, não código de produção. Nenhuma "Coverage Expectation" pré-existente se aplica; o padrão vem integralmente do próprio `spec.md` desta história.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| --- | --- | --- | --- | --- |
| Dependência Playwright + `@axe-core/playwright` | none | Instalação/configuração, sem teste dedicado | `testes-e2e/playwright.config.ts` | build gate only |
| Cenários de negócio E2E | e2e | 1:1 com os 8 cenários de `E2E-01..09`; sem rede externa real | `testes-e2e/cenarios/*.spec.ts` | `npx playwright test testes-e2e/cenarios` |
| Auditoria de acessibilidade | e2e | Todos os fluxos principais listados no AC; WCAG 2.2 AA | `testes-e2e/acessibilidade/*.spec.ts` | `npx playwright test testes-e2e/acessibilidade` |
| Verificação visual/responsiva | e2e | 1440×1024, larguras ≥1024px, aviso <1024px | `testes-e2e/responsividade/*.spec.ts` | `npx playwright test testes-e2e/responsividade` |
| Script de evidências | none | Orquestração, sem lógica de negócio própria | `scripts/gerar_evidencias.py` | build gate only |

## Gate Check Commands

| Gate Level | When to Use | Command |
| --- | --- | --- |
| E2E (cenários) | Após cada task de cenário de negócio | `npx playwright test testes-e2e/cenarios/<arquivo>` |
| E2E (acessibilidade) | Após a task de auditoria | `npx playwright test testes-e2e/acessibilidade` |
| E2E (responsividade) | Após a task de verificação visual | `npx playwright test testes-e2e/responsividade` |
| Build (fim de fase) | Fim de fase / suíte completa | `uv run --directory src/backend pytest && npm test --prefix src/frontend -- --run && npx playwright test` |

---

## Execution Plan

### Phase 1: Infraestrutura de E2E

```
T1
```

### Phase 2: Cenários de negócio ponta a ponta

```
T2 → T3 → T4 → T5
```

### Phase 3: Resiliência agêntica e de integração

```
T6 → T7 → T8 → T9
```

### Phase 4: Contrato, visual e acessibilidade

```
T10 → T11 → T12
```

### Phase 5: Evidências e suíte completa

```
T13
```

---

## Task Breakdown

### T1: Adicionar Playwright e `@axe-core/playwright`

**What**: Configurar Playwright (`testes-e2e/playwright.config.ts`) contra o backend/frontend locais, com versão estável mais recente verificada no momento da implementação.
**Where**: `testes-e2e/playwright.config.ts`
**Depends on**: None
**Reuses**: nenhuma — primeira infraestrutura de E2E do projeto
**Requirement**: E2E-08

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] `npx playwright test` roda (mesmo que sem nenhum cenário ainda) contra o backend/frontend locais
- [ ] Documentado no README o comando para instalar os navegadores do Playwright
- [ ] Gate check passa: `uv run --directory src/backend pytest && npm test --prefix src/frontend -- --run` (nenhuma regressão na suíte já existente)

**Tests**: none
**Gate**: build

---

### T2: Cenário E2E — chuva intensa residencial

**What**: Teste E2E cobrindo entrada meteorológica→normalização→relevância→elegibilidade→geração→crítica→revisão→simulação→visualização do comunicado, com ao menos um registro não elegível.
**Where**: `testes-e2e/cenarios/chuva-intensa.spec.ts`
**Depends on**: T1
**Reuses**: dublês de INMET/OpenAI já usados nos testes de integração backend (2.1–3.6)
**Requirement**: E2E-01

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Cenário completo verde, do evento até a visualização do comunicado
- [ ] Ao menos um registro não elegível aparece com explicação consultável
- [ ] Gate check passa: `npx playwright test testes-e2e/cenarios/chuva-intensa.spec.ts`

**Tests**: e2e
**Gate**: e2e (cenários)

---

### T3: Cenário E2E — granizo automóvel

**What**: Teste E2E análogo ao de chuva intensa, para o evento de granizo/apólice automóvel, preservando regras/apólices/canais/recomendações específicas.
**Where**: `testes-e2e/cenarios/granizo.spec.ts`
**Depends on**: T2
**Reuses**: mesma infraestrutura de T2
**Requirement**: E2E-02

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Cenário completo verde, do evento até a visualização do comunicado
- [ ] Regras/apólices/canais/recomendações específicas de granizo confirmadas na evidência
- [ ] Gate check passa: `npx playwright test testes-e2e/cenarios/granizo.spec.ts`

**Tests**: e2e
**Gate**: e2e (cenários)

---

### T4: Cenário E2E — sem risco

**What**: Teste E2E de um evento que não atinge nenhuma regra, terminando `sem_risco` com motivo e evidência determinísticos.
**Where**: `testes-e2e/cenarios/sem-risco.spec.ts`
**Depends on**: T3
**Reuses**: mesma infraestrutura de T2
**Requirement**: E2E-03

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Execução termina `sem_risco` com motivo consultável
- [ ] Nenhuma chamada à OpenAI, mensagem ou simulação registrada
- [ ] Gate check passa: `npx playwright test testes-e2e/cenarios/sem-risco.spec.ts`

**Tests**: e2e
**Gate**: e2e (cenários)

---

### T5: Cenário E2E — sem público elegível

**What**: Teste E2E de um evento relevante sem nenhum segurado elegível, terminando `sem_elegiveis` com motivo e evidência determinísticos.
**Where**: `testes-e2e/cenarios/sem-elegivel.spec.ts`
**Depends on**: T4
**Reuses**: mesma infraestrutura de T2
**Requirement**: E2E-03

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Execução termina `sem_elegiveis` com motivo consultável
- [ ] Nenhuma chamada à OpenAI, mensagem ou simulação registrada
- [ ] Gate check passa: `npx playwright test testes-e2e/cenarios/sem-elegivel.spec.ts`

**Tests**: e2e
**Gate**: e2e (cenários)

---

### T6: Cenário E2E — regeneração e esgotamento de tentativas

**What**: Teste E2E de uma mensagem reprovada pelo crítico, demonstrando retorno ao redator, motivos, histórico e limite de 3 tentativas, com esgotamento produzindo exceção.
**Where**: `testes-e2e/cenarios/regeneracao.spec.ts`
**Depends on**: T5
**Reuses**: dublê de crítico configurável já usado em 3.3/3.4
**Requirement**: E2E-04

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Ciclo reprova→regenera visível até a 3ª tentativa
- [ ] Esgotamento produz `falhou_conteudo` com `Exceção`, mensagem fora do lote simulável
- [ ] Gate check passa: `npx playwright test testes-e2e/cenarios/regeneracao.spec.ts`

**Tests**: e2e
**Gate**: e2e (cenários)

---

### T7: Cenário E2E — contingência do INMET

**What**: Teste E2E sobre indisponibilidade controlada do INMET, demonstrando timeout, tentativas, snapshot informativo e ativação explícita do cenário sintético.
**Where**: `testes-e2e/cenarios/contingencia-inmet.spec.ts`
**Depends on**: T6
**Reuses**: dublê de indisponibilidade já usado em 2.2
**Requirement**: E2E-05

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Timeout/tentativas/snapshot informativo visíveis na interface
- [ ] Origem sintética permanece visível até o fim do fluxo
- [ ] Gate check passa: `npx playwright test testes-e2e/cenarios/contingencia-inmet.spec.ts`

**Tests**: e2e
**Gate**: e2e (cenários)

---

### T8: Cenário E2E — indisponibilidade/configuração ausente da OpenAI

**What**: Teste E2E sobre a produção agêntica alcançada sem `OPENAI_API_KEY`/com OpenAI indisponível, confirmando `falhou_preparacao_ia` sem resposta fixa.
**Where**: `testes-e2e/cenarios/indisponibilidade-openai.spec.ts`
**Depends on**: T7
**Reuses**: dublê de indisponibilidade já usado em 3.1
**Requirement**: E2E-06

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Execução termina `falhou_preparacao_ia`, sem nenhum texto fixo simulando resposta da IA
- [ ] Trabalho determinístico anterior (2.1–2.6) permanece consultável
- [ ] Gate check passa: `npx playwright test testes-e2e/cenarios/indisponibilidade-openai.spec.ts`

**Tests**: e2e
**Gate**: e2e (cenários)

---

### T9: Cenário E2E — retentativa correlacionada sem duplicação

**What**: Teste E2E de retentativa a partir de uma falha terminal (preparação ou simulação), confirmando execução correlacionada nova sem reabrir a original, e repetição do comando sem duplicar.
**Where**: `testes-e2e/cenarios/retentativa.spec.ts`
**Depends on**: T8
**Reuses**: mecanismo de execução correlacionada já usado em 2.2/3.1/3.6
**Requirement**: E2E-07

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Nova execução correlacionada criada com `execucao_origem_id`, snapshots válidos, origem permanece terminal
- [ ] Repetir o comando de retentativa não duplica execução nem efeito
- [ ] Gate check passa: `npx playwright test testes-e2e/cenarios/retentativa.spec.ts`

**Tests**: e2e
**Gate**: e2e (cenários)

---

### T10: Verificação de contrato de API e evidências localizáveis

**What**: Teste E2E que navega prontidão, evento e decisão, supervisão, resultados, comunicado, explicação e linha do tempo de um cenário já executado (T2), confirmando que tudo é localizável pela interface, e que `openapi.json`/Swagger UI correspondem à API real.
**Where**: `testes-e2e/cenarios/evidencias-localizaveis.spec.ts`
**Depends on**: T9
**Reuses**: cenário de T2 como base de dado
**Requirement**: E2E-08

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Todas as 7 evidências listadas no AC são alcançáveis pela navegação, sem editar arquivo/banco
- [ ] `openapi.json` gerado corresponde ao contrato realmente executado (reusa `test_openapi_sincronizado.py`)
- [ ] Gate check passa: `npx playwright test testes-e2e/cenarios/evidencias-localizaveis.spec.ts`

**Tests**: e2e
**Gate**: e2e (cenários)

---

### T11: Verificação visual e responsiva

**What**: Testes de viewport (1440×1024, larguras desktop ≥1024px, aviso <1024px) nos fluxos principais, mais inspeção de tokens de `DESIGN.md` (cores, tipografia, espaçamento, raios).
**Where**: `testes-e2e/responsividade/*.spec.ts`
**Depends on**: T10
**Reuses**: infraestrutura de Playwright de T1
**Requirement**: E2E-10, E2E-11, E2E-12

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] Fluxos principais funcionam em 1440×1024 e larguras ≥1024px sem função essencial desaparecer
- [ ] Aviso de resolução não suportada aparece abaixo de 1024px
- [ ] Nenhum componente/estado de `DESIGN.md`/`EXPERIENCE.md` aparece como botão inerte ou dado fixo (checklist por superfície documentado no relatório)
- [ ] Gate check passa: `npx playwright test testes-e2e/responsividade`

**Tests**: e2e
**Gate**: e2e (responsividade)

---

### T12: Auditoria de acessibilidade WCAG 2.2 AA

**What**: `@axe-core/playwright` contra os fluxos principais, mais checklist manual assistida (teclado, foco, contraste, zoom 200%, nomes acessíveis, movimento reduzido) para o que a ferramenta automatizada não cobre sozinha.
**Where**: `testes-e2e/acessibilidade/*.spec.ts`
**Depends on**: T11
**Reuses**: infraestrutura de Playwright de T1
**Requirement**: E2E-13

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] `axe-core` roda sem violação crítica/séria nos fluxos principais listados no AC
- [ ] Checklist manual (teclado/foco/contraste/zoom/nomes/movimento reduzido) documentado por fluxo, com todo desvio explicitamente registrado
- [ ] Gate check passa: `npx playwright test testes-e2e/acessibilidade`

**Tests**: e2e
**Gate**: e2e (acessibilidade)

---

### T13: Script de evidências e suíte completa

**What**: `scripts/gerar_evidencias.py` roda a suíte completa (`pytest`+`vitest`+Playwright) e organiza `docs/evidencias/` com um relatório por cenário citando `file:line`; README atualizado com todos os comandos reproduzíveis em PT-BR.
**Where**: `scripts/gerar_evidencias.py`
**Depends on**: T12
**Reuses**: todos os comandos já documentados nas tasks anteriores
**Requirement**: E2E-09

**Tools**: MCP: NONE — Skill: NONE

**Done when**:

- [ ] `python3 scripts/gerar_evidencias.py` roda a suíte completa e produz `docs/evidencias/` com um relatório por cenário
- [ ] Cada relatório cita `file:line` do(s) teste(s) que comprovam o cenário
- [ ] README lista o comando único e os comandos individuais, todos em português brasileiro
- [ ] Gate check passa: `uv run --directory src/backend pytest && npm test --prefix src/frontend -- --run && npx playwright test`

**Tests**: none
**Gate**: build

**Commit**: `test(e2e): adicionar cenarios ponta a ponta, auditoria de acessibilidade e evidencias estruturadas`

---

## Phase Execution Map

```
Phase 1:  T1
Phase 2:  T2 → T3 → T4 → T5
Phase 3:  T6 → T7 → T8 → T9
Phase 4:  T10 → T11 → T12
Phase 5:  T13
```

Grafo completo de dependências:

```
T1 → T2
T2 → T3
T3 → T4
T4 → T5
T5 → T6
T6 → T7
T7 → T8
T8 → T9
T9 → T10
T10 → T11
T11 → T12
T12 → T13
```

---

## Task Granularity Check

| Task | Scope | Status |
| --- | --- | --- |
| T1: Infraestrutura Playwright | 1 arquivo de config | ✅ Granular |
| T2–T9: Cenários de negócio | 1 arquivo de teste cada | ✅ Granular |
| T10: Evidências localizáveis | 1 arquivo de teste | ✅ Granular |
| T11: Visual/responsivo | 1 diretório de testes coeso | ⚠️ OK — mesmo tema, testes parametrizados |
| T12: Acessibilidade | 1 diretório de testes coeso | ⚠️ OK — mesmo tema |
| T13: Script de evidências | 1 script | ✅ Granular |

---

## Diagram-Definition Cross-Check

| Task | Depends On (task body) | Diagram Shows | Status |
| --- | --- | --- | --- |
| T1 | None | — | ✅ Match |
| T2 | T1 | T1 → T2 | ✅ Match |
| T3 | T2 | T2 → T3 | ✅ Match |
| T4 | T3 | T3 → T4 | ✅ Match |
| T5 | T4 | T4 → T5 | ✅ Match |
| T6 | T5 | T5 → T6 | ✅ Match |
| T7 | T6 | T6 → T7 | ✅ Match |
| T8 | T7 | T7 → T8 | ✅ Match |
| T9 | T8 | T8 → T9 | ✅ Match |
| T10 | T9 | T9 → T10 | ✅ Match |
| T11 | T10 | T10 → T11 | ✅ Match |
| T12 | T11 | T11 → T12 | ✅ Match |
| T13 | T12 | T12 → T13 | ✅ Match |

**Rules confirmed**: toda dependência aponta para trás ou dentro da mesma fase (cadeia linear intencional — cada cenário soma evidência ao relatório final).

---

## Test Co-location Validation

| Task | Code Layer Created/Modified | Matrix Requires | Task Says | Status |
| --- | --- | --- | --- | --- |
| T1: Infraestrutura Playwright | Build/config | none | none | ✅ OK |
| T2–T10: Cenários E2E | E2E | e2e | e2e | ✅ OK |
| T11: Visual/responsivo | E2E | e2e | e2e | ✅ OK |
| T12: Acessibilidade | E2E | e2e | e2e | ✅ OK |
| T13: Script de evidências | Build/config | none | none | ✅ OK |

**Rules confirmed**: `Tests: none` só em T1/T13 (infraestrutura/script, sem lógica de negócio própria), conforme a matriz.
