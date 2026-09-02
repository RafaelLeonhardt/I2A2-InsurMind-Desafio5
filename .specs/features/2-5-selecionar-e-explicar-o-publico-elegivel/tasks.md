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

### T1: Migração `0006_elegibilidade.sql`

**What**: Recriar `elegibilidades_historicas` por recreate-and-copy (AD-015) com `execucao_id` (nulo = linha semeada), `criterios`, `canal` (backfill das linhas semeadas conforme o Design) e `UNIQUE(execucao_id, evento_id, regra_id, segurado_id, apolice_id)` declarada no `CREATE`.
**Where**: `src/backend/central_preventiva/adaptadores/persistencia/migracoes/0006_elegibilidade.sql`
**Depends on**: None
**Reuses**: convenção de migração numerada
**Requirement**: ELEG-04, ELEG-07

**Nota de implementação**: o Design nomeou a migração `0005`, mas a História 2.3 já ocupou esse número (`0005_avaliacao_risco_sem_regra.sql`, commitado antes desta história começar) — o design das 25 histórias foi escrito em lote antes da numeração sequencial real ser conhecida. Renumerada para `0006`, próximo número livre; mesma estratégia de conteúdo do Design, sem outra mudança. `semeador.py` também precisou ganhar as colunas `criterios`/`canal` na `TabelaSemeada` de `elegibilidades_historicas` (não previsto explicitamente no Design, mas necessário: o semeador roda após a migração, contra o schema já `NOT NULL`). `RegraSnapshot` (2.3) também ganhou o campo `cobertura_exigida` — não estava lá porque `avaliar_risco.avaliar` não o usa, mas `AvaliadorElegibilidade` (T2) precisa dele e é a mesma regra ativa consumida pelos dois avaliadores.

**Done when**:

- [x] Migração aplica em transação própria, registrada em `schema_migracoes`
- [x] Recreate-and-copy preserva todas as linhas semeadas com backfill correto: `execucao_id IS NULL`, `criterios = '{"origem": "seed_demonstrativo"}'`, `canal` vindo de `segurados.canal_preferido` (AD-015)
- [x] Teste cobre `INSERT ... ON CONFLICT DO NOTHING` sobre a `UNIQUE` recriada e a não-colisão entre linhas semeadas (`execucao_id` nulo)
- [x] `README.md` de persistência documenta as colunas novas, a `UNIQUE` e a estratégia de recreate
- [x] `testes/test_migracoes.py` cobre a aplicação da migração `0006`
- [x] Gate check passa: `uv run --directory src/backend pytest`

**Tests**: integration
**Gate**: quick

---

### T2: `AvaliadorElegibilidade`

**What**: Função pura que avalia área, tipo/situação da apólice, coberturas e participação em alertas, devolvendo `incluido`/`excluido` com critério a critério; canal preferencial preservado sem afetar o resultado.
**Where**: `src/backend/central_preventiva/dominio/avaliador_elegibilidade.py`
**Depends on**: None
**Reuses**: mesmo padrão estrutural de `AvaliadorRisco` (2.3); reusa `Criterio` (2.3) em vez de duplicar a mesma forma de valor
**Requirement**: ELEG-01, ELEG-02, ELEG-03

**Nota de implementação**: o Design tipava `avaliar(segurado: Segurado, apolice: ApoliceSnapshot, ...)`, mas `dominio/segurado.py` já tinha um `Segurado` (id, nome) construído para um propósito não relacionado (seletor de perfil em `aplicacao/contexto.py`) — estendê-lo ou criar um `ApoliceSnapshot` irmão criaria dois objetos que o avaliador sempre precisa zipar juntos (a spec já trata "segurado+apólice" como uma combinação inseparável, nunca um sem o outro). Substituído por um único `CandidatoElegibilidade` com campos planos, próprio deste avaliador — mesma decisão estrutural de manter tipos de domínio estreitos por consumidor.

**Done when**:

- [x] Segurado+apólice que atendem todos os critérios → `incluido` com todos os critérios satisfeitos
- [x] Cada critério de exclusão testado isoladamente (área fora, apólice não `ativa`, cobertura ausente, `participa_de_alertas = false`) produz `excluido` com o motivo específico
- [x] Canal preferencial diferente não muda o resultado de inclusão/exclusão
- [x] Gate check passa: `uv run --directory src/backend pytest`

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

**Nota de implementação**: o Design não especificava `segurado_id`/`apolice_id` como parâmetros de `salvar` (só `resultado`), mas `ResultadoElegibilidade` não carrega esses ids (são do candidato, não do resultado da avaliação) — `salvar` recebe os dois explicitamente, mesmo padrão de `RepositorioAvaliacoesRisco.salvar` (2.3) que recebe `evento_id`/`regra_id` fora do `resultado`. Extraída `serializacao_criterios.py` compartilhada entre `repositorio_avaliacoes_risco.py` e este módulo, para não duplicar o mesmo formato JSON de `Criterio`.

**Done when**:

- [x] `listar_candidatos` retorna todos os segurados+apólices da área informada
- [x] `salvar` chamado duas vezes para a mesma combinação produz uma única linha (violação de `UNIQUE` tratada como no-op, não erro não tratado)
- [x] `contar_por_execucao` retorna quantidades corretas de incluídos/excluídos
- [x] Gate check passa: `uv run --directory src/backend pytest`

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

**Nota de implementação**: a transição de estado da execução (`avaliando_elegibilidade` → `aguardando_geracao`/`sem_elegiveis`) fica fora deste serviço, como o Design já previu — a História 2.6 decide entre os dois terminais a partir da contagem devolvida por `avaliar_publico`.

**Done when**:

- [x] Evento sem nenhum candidato elegível retorna conjunto vazio válido, sem erro e sem chamada de IA
- [x] Reprocessar a mesma execução não duplica nenhum resultado
- [x] Snapshots (segurado, apólice, evento, regra) preservados mesmo que dados originais mudem depois
- [x] Gate check passa: `uv run --directory src/backend pytest`

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

**Nota de implementação**: `RegistroElegibilidade` (T3) precisou de `nome_segurado`/`codigo_ibge_area`/`regra_versao` — dados de exibição que a tabela não guarda por si (evitar duas fontes de verdade). `listar_por_execucao`/`obter_por_id` passaram a fazer `JOIN` em `segurados`/`apolices`/`regras` no momento da leitura; nenhuma coluna nova na migração.

**Done when**:

- [x] `200` com quantidades e lista completa
- [x] Conjunto vazio retorna `200` com lista vazia, não erro
- [x] `openapi.json` regenerado, `test_openapi_sincronizado.py` verde
- [x] Gate check passa: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`

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

- [x] Quantidades e tabela exibidas com segurado sintético, apólice, localização, canal, resultado
- [x] Explicação de cada linha acessível por teclado, sem depender de hover
- [x] Inclusões/exclusões distinguíveis por texto+ícone+cor
- [x] `npm run gerar-tipos-api --prefix src/frontend` executado; tipos atualizados (gerado via `openapi-typescript` direto do `openapi.json` local)
- [x] Gate check passa: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`

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

---

## Fix Tasks (Verifier Round 1 — FAIL, `validation.md` de 2026-09-02)

O Verificador achou 1 **defeito de produção real** (blocker) e 7 lacunas de asserção/design (3 Major, 4 Minor/lacunas de teste). 3/10 mutantes morreram (dedução por `UNIQUE` e o `404` por execução divergente são reais, não decorativos); 7 sobreviveram. Corrigidas nesta rodada:

- [x] **Fix 1 (Blocker)** — `desserializar_criterios` lançava `TypeError` para **qualquer** linha semeada: o backfill original da migração `0006` gravava `criterios = '{"origem": "seed_demonstrativo"}'` (um objeto JSON), mas o parser espera uma lista. `obter_por_id` propagava a exceção antes de qualquer checagem de negócio, e a rota HTTP devolvia `500` em vez de `404`. Nova migração `0007_elegibilidade_correcoes.sql` corrige o backfill para `'[]'` (mesma convenção de `avaliacoes_risco`, migração `0005`); `semeador.py` também corrigido para futuras seedagens. Teste de regressão no nível do repositório e um teste HTTP que semeia o conjunto real e chama o endpoint de detalhe, confirmando `404` limpo.
- [x] **Fix 2/3 (Major)** — `nome_segurado`/`codigo_ibge_area` eram lidos ao vivo via `JOIN` em `segurados`/`apolices`, violando ELEG-04.3 (AD-11: uma mudança nos dados originais não pode reescrever a explicação histórica). `nome_segurado` virou coluna própria (mesma migração `0007`), gravada por `RepositorioElegibilidades.salvar` no momento da avaliação. `codigo_ibge_area` passou a ser derivado do próprio `criterios` já persistido (o critério "área afetada" é sempre o primeiro elemento) — sem coluna nova, sem releitura ao vivo. Novo teste altera `segurados.nome`/`apolices.codigo_ibge_area` depois de salvar e confirma que a releitura preserva os valores originais.
- [x] **Fix 4 (Major)** — mutante que removia `apolice_id` do `UNIQUE` sobrevivia: nenhum teste persistia duas linhas do mesmo segurado+regra+evento+execução diferindo só por `apolice_id`. Novo teste cobre exatamente o edge case da spec (segurado com duas apólices na área, uma elegível e outra não) e confirma duas linhas distintas.
- [x] **Fix 5 (Major)** — ELEG-09: nenhum teste de frontend conferia a versão da regra no cabeçalho da explicação nem as colunas "valor observado"/"resultado". Fortalecido o teste de abertura de critérios por teclado para checar `regra v3`, o valor observado e "Atende" dentro da seção de explicação.
- [x] **Fix 6 (Major)** — ELEG-05: os testes de exclusão do `AvaliadorElegibilidade` conferiam só o motivo, nunca `len(criterios) == 5` — um critério "engolido" silenciosamente numa exclusão não seria detectado. Adicionada a asserção em todos os 6 testes de exclusão.
- [x] **Fix 7 (Minor)** — ELEG-08: a fixture HTTP usava sempre `incluidos=excluidos=1`, então trocar os dois contadores não quebrava nenhum teste. Estendida para 2 incluídos / 1 excluído.
- [x] **Fix 8 (Minor)** — ELEG-01: nenhum teste dava ao segurado e à apólice códigos de área diferentes, então filtrar por `segurados.codigo_ibge_area` em vez de `apolices.codigo_ibge_area` passaria despercebido. Novo teste cobre exatamente esse caso.

**Gate check (backend, full)**: `uv run --directory src/backend pytest && ruff check . && pyright` — verde (378 testes). **Gate check (frontend, full)**: `npm test -- --run && npm run lint && npm run build` — verde (202 testes, mesmos avisos pré-existentes).

**Commit**: `fix(elegibilidade): fechar lacunas do verificador da historia 2.5`

## Fix Tasks (Verifier Round 2 — FAIL, `validation.md` de 2026-09-02)

Rodada 2 confirmou o blocker genuinamente fechado (reverter `semeador.py` reproduz o `TypeError` original) e 6 dos 7 fixes da Rodada 1 mortos por mutação. Restaram 4 lacunas, todas de asserção — nenhum defeito de produção novo, exceto uma correção de robustez feita por precaução:

- [x] **Fix 9 (Major)** — ELEG-06: o Fix 2/3 da Rodada 1 esqueceu de guardar o `canal` contra mudança nos dados originais (só `nome_segurado`/`codigo_ibge_area` ganharam teste). O código já lia `e.canal` (frozen) corretamente desde a Rodada 1 — só faltava a asserção. Estendido `test_nome_segurado_e_area_persistidos_sobrevivem_a_mudanca_dos_dados_originais` para também alterar `segurados.canal_preferido` depois de salvar e confirmar que o `canal` persistido não muda.
- [x] **Fix 10 (Major)** — `_codigo_ibge_area_de` buscava o critério de área por **posição** (`criterios[0]`), não por nome — com um único critério persistido em cada fixture de teste, `criterios[0]` e `criterios[-1]` são indistinguíveis. Corrigido para buscar pelo `operando` (nova constante `OPERANDO_AREA_AFETADA` em `avaliador_elegibilidade.py`, reusada pelo próprio critério e pelo repositório) — a ordem dos 5 critérios deixa de ser um contrato implícito.
- [x] **Fix 11 (Minor)** — ELEG-08: o Fix 7 da Rodada 1 só chegou ao backend; a fixture do frontend (`SuperficieEventoDecisao.test.tsx`) continuava simétrica (`1`/`1`). Alterada para `incluidos=2`/`excluidos=1`, com asserção do texto completo do parágrafo (não só a presença isolada de cada número).
- [x] **Fix 12 (Minor)** — ELEG-09: o Fix 5 conferia os valores das células mas não o conjunto de cabeçalhos ("colunas estáveis" exigido pela AC). Adicionada asserção `getAllByRole('columnheader')` com a lista exata `['Operando', 'Valor observado', 'Resultado', 'Justificativa']`.

**Gate check (backend, full)**: `uv run --directory src/backend pytest && ruff check . && pyright` — verde (378 testes, mesma contagem — fixes 9/10 fortalecem testes/código já existentes). **Gate check (frontend, full)**: `npm test -- --run && npm run lint && npm run build` — verde (202 testes).

**Commit**: `fix(elegibilidade): fechar lacunas residuais do verificador (Round 2)`

## Round 3 (final) — PASS, com um fechamento opcional pós-verificação

Round 3 confirmou **PASS pleno — 10/10 ELEG verificados**. Um resíduo Minor não bloqueante ficou registrado na "Nota F" do relatório (`_codigo_ibge_area_de` só tinha guarda com fixture de 1 critério; a classe de defeito já estava eliminada por construção e comprovada por contrafactual, mas nenhum teste persistia um snapshot de 5 critérios com "área afetada" fora da primeira posição). Como o próprio relatório trazia a receita de fechamento (~5 linhas) e não exigia nova rodada, foi aplicado depois do PASS, sem reabrir a verificação: `test_codigo_ibge_area_e_correto_mesmo_quando_area_nao_e_o_primeiro_criterio` (`test_repositorio_elegibilidade.py`) persiste um resultado de 5 critérios com "área afetada" no meio da tupla — morto manualmente contra `criterios[0]` **e** `criterios[-1]` antes de commitar (379 testes).

**Commit**: `test(elegibilidade): fechar residuo minor da nota f (round 3)`
