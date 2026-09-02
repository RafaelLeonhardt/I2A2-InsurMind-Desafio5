# História 2.2: Operar com segurança durante indisponibilidades meteorológicas — Validation

**Date**: 2026-09-02
**Spec**: `.specs/features/2-2-operar-com-seguranca-durante-indisponibilidades-meteorologicas/spec.md`
**Diff range (feature completa)**: `e7a3410..5575981` (9 commits: T1–T7 + `50e31fa` Fix 1–6 + `5575981` Fix 7–8)
**Diff range (esta rodada)**: `50e31fa..5575981`
**Verifier**: independent sub-agent (author ≠ verifier), read-only sobre a árvore real
**Rodada**: **Round 3 — FINAL** (limite do skill: máx. 3 iterações fix→re-verify)

**Verdict**: ✅ **PASS**

## Histórico do laço de correção

| Rodada | Commit verificado | Veredito | Resultado |
| --- | --- | --- | --- |
| Round 1 | `e7a3410..2a6efa8` | ❌ FAIL | 1 mutante sobrevivente + 2 gaps de comportamento + 4 gaps de precisão |
| Fix 1–6 | `50e31fa` | — | precedência, `calcularIdade`, aviso de desatualizado, ícone/cor, ações por estado, matriz de repositórios |
| Round 2 | `e7a3410..50e31fa` | ❌ FAIL (Minor) | 14/18 ACs em PASS pleno, **0 gaps de comportamento**; 2 lacunas residuais só de teste |
| Fix 7–8 | `5575981` | — | 3 testes de fronteira em `calcularIdade`; leitura de volta de `excecoes_operacionais` |
| **Round 3** | `e7a3410..5575981` | ✅ **PASS** | ambas as lacunas residuais fechadas e **comprovadas por sensor**; nenhuma regressão |

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 Migração `0003` | ✅ Done | `testes/test_migracoes.py:118` — recreate-and-copy + `ON CONFLICT DO NOTHING` |
| T2 `RepositorioExecucaoPreventiva` | ✅ Done | 4 testes de integração + o novo teste do Fix 8 (5 no arquivo) |
| T3 `ColetorComRetry` | ✅ Done | 4 testes unitários com dublês de tempo |
| T4 `AdaptadorCenarioSintetico` | ✅ Done | Desvio documentado (relógio corrente) justificado |
| T5 Extensão do caso de uso | ✅ Done | "idade calculada" (RESIL-06) fechada pelo Fix 2 e agora discriminada pelo Fix 7 |
| T6 Extensão do roteador | ✅ Done | 7 testes de rota (happy + edge + error) |
| T7 Frontend 6 estados | ✅ Done | ícone/cor, aviso de desatualizado e ações asseridas nos 6 estados |
| Fix 1–6 (Round 1) | ✅ Done | Confirmados genuínos e discriminadores pela Round 2 |
| **Fix 7** (`calcularIdade`, fronteiras) | ✅ **Done** | `SuperficieFonteMeteorologica.test.tsx:466,470,474` — verificado pelo sensor (mutação A) |
| **Fix 8** (`excecoes_operacionais` readback) | ✅ **Done** | `test_repositorio_execucao_preventiva.py:82-103` — verificado pelo sensor (mutação B) |

Nenhuma tarefa bloqueada ou parcial.

---

## Verificação independente do Fix 7–8 (foco desta rodada)

### Fix 7 — fronteiras de `calcularIdade` (RESIL-06)

Implementação sob teste: `src/frontend/src/funcionalidades/fonte-meteorologica/SuperficieFonteMeteorologica.tsx:94-106`
`agora` do bloco de testes = `new Date('2026-08-30T18:30:00+00:00')` (`…test.tsx:448`).

| Teste | `file:line` + asserção | Δ exato | Correto? |
| --- | --- | --- | --- |
| Limite de 1 minuto | `…test.tsx:467` — `expect(calcularIdade('2026-08-30T18:29:00+00:00', agora)).toBe('1 min atrás')` | **60 s = 1 min exato** | ✅ discrimina `diffMinutos < 1` de `<= 1` |
| Limite de 60 minutos | `…test.tsx:471` — `expect(calcularIdade('2026-08-30T17:30:00+00:00', agora)).toBe('1 h atrás')` | **3600 s = 60 min exatos** | ✅ discrimina `diffMinutos < 60` de `<= 60` |
| Limite de 24 horas | `…test.tsx:475` — `expect(calcularIdade('2026-08-29T18:30:00+00:00', agora)).toBe('1 d atrás')` | **86400 s = 24 h exatas** | ✅ discrimina `diffHoras < 24` de `<= 24` |

Os três instantes incidem **exatamente** sobre o limiar (aritmética conferida uma a uma), e o valor esperado é o do lado *superior* da faixa — que é precisamente o valor que a relaxação de `<` para `<=` altera. Os 4 testes de meio de faixa pré-existentes (`:451,455,459,463`) foram mantidos; nenhum foi enfraquecido ou removido.

### Fix 8 — leitura de volta de `excecoes_operacionais` (RESIL-08)

Implementação sob teste: `src/backend/central_preventiva/adaptadores/persistencia/repositorio_execucao_preventiva.py:117-125`

`src/backend/testes/test_repositorio_execucao_preventiva.py:82-103` — cria uma execução real via `ExecutorMigracoes` + `RepositorioExecucaoPreventiva.criar(FALHOU_COLETA)`, chama `RepositorioExcecoesOperacionais(caminho).registrar(...)` e relê a linha com um `SELECT execucao_id, causa, tentativas, impacto FROM excecoes_operacionais` **direto no DuckDB real** (nenhum dublê):

- `:100` — `assert str(linha[0]) == str(execucao_id)` (correlação)
- `:101` — `assert linha[1] == "TimeoutException: timeout"` (causa, valor exato)
- `:102` — `assert linha[2] == 3` (tentativas, valor exato)
- `:103` — `assert linha[3] == "Coleta meteorológica indisponível."` (impacto, valor exato)

Os quatro campos exigidos pelo AC (`causa`, `tentativas`, `impacto` + correlação) são conferidos por **igualdade exata**, na ordem posicional da projeção. Esta é a terceira e última tabela da matriz de repositórios prometida na Round 1 — as outras duas (`tentativas_coleta_meteorologica`, `cenarios_sinteticos_ativados`) já haviam sido fechadas pelo Fix 6.

Observação de forma (não é gap): o Fix 8 ficou em `test_repositorio_execucao_preventiva.py`, e não em `test_repositorio_meteorologia.py` como a Round 2 sugeriu — **escolha correta**, pois `RepositorioExcecoesOperacionais` é definido em `repositorio_execucao_preventiva.py`.

---

## Spec-Anchored Acceptance Criteria (18/18)

Prefixos: `B/` = `src/backend/`, `F/` = `src/frontend/src/`. Linhas conferidas em `5575981`.
Os ACs marcados "inalterado" mantêm a evidência re-derivada na Round 2 (o diff desta rodada é puramente aditivo em 2 arquivos de teste, sem tocar produção); RESIL-01, RESIL-10 e RESIL-12 foram re-conferidos por amostragem nesta rodada.

| Critério (RESIL) | Outcome definido na spec | `file:line` + asserção | Result |
| --- | --- | --- | --- |
| **RESIL-01** falha/timeout/resposta inválida → timeout + máx. 3 tentativas, espera configurável | 3 tentativas totais, backoff 1s/2s | **Re-conferido nesta rodada**: `B/testes/test_coletor_com_retry.py:107-111` — `assert tentativas.registradas == [(…,1,TIMEOUT),(…,2,ERRO_TRANSPORTE),(…,3,SUCESSO)]`; `:112` — `assert espera.esperas == [1.0, 2.0]`; `:126` — `assert coletor.chamadas == 3`; `:127` — `assert excecao.value.tentativas == 3`. Timeout de 5s em `B/…/meteorologia/README.md:77` | ✅ PASS |
| **RESIL-02** cada tentativa registra número, início, término, código e correlação | número + instantes + código + `sincronizacao_id` | `B/testes/test_repositorio_meteorologia.py:220-222` — `numero_tentativa`, `codigo_resultado`, `iniciado_em == inicio`, `finalizado_em == fim` relidos do DuckDB real; ordenação `:245`; vazio `:252` | ✅ PASS |
| **RESIL-03** intervalo, timeout, tentativas e backoff exatos, configuráveis e documentados | Assumptions: "configuráveis por variável de ambiente" | Valores exatos: `B/…/aplicacao/coleta_meteorologica.py:31,34`; documentados em `B/…/meteorologia/README.md:73-92`. Entrega constantes de módulo injetáveis por construtor, não env vars | ⚠️ **Desvio assumido e documentado** (README:89-92) — dívida aceita nas Rounds 1 e 2, inalterada |
| **RESIL-04** documentação justifica padrões e descreve comportamento por tipo de falha | 4 tipos de falha + justificativa dos 3 parâmetros | `B/…/adaptadores/meteorologia/README.md:75-79`, `:83-87` | ✅ PASS |
| **RESIL-05** enquanto houver tentativas → UI mostra tentativa atual e limite de três | texto "tentativa atual / 3" | `F/…/SuperficieFonteMeteorologica.test.tsx:312` — `getByText('Tentativa 2 de 3')`; backend `B/testes/test_meteorologia_api.py:269` — `limite_tentativas == 3` | ✅ PASS |
| **RESIL-06** snapshot antigo consultável com **origem, horário e idade calculada** | os 3 atributos acompanhando o snapshot | Idade: `F/…/SuperficieFonteMeteorologica.tsx:94-106` renderizada em `:292,309`; faixas `…test.tsx:451,455,459,463`; **fronteiras exatas (Fix 7) `:467,471,475`**; componente `:499`. Origem/horário: `.tsx:307,308` + `…test.tsx:149`. Permanência: `B/testes/test_coleta_meteorologica.py:421` — `eventos.salvos == [snapshot_anterior]` | ✅ **PASS pleno** (era ⚠️ na Round 2) — sensor A confirma discriminação |
| **RESIL-07** snapshot consultado durante falha → nenhuma avaliação/alerta/mensagem | nenhum evento novo derivado | `B/testes/test_coleta_meteorologica.py:420-421` — estado `FALHA` e a lista permanece exatamente `[snapshot_anterior]` | ✅ PASS |
| **RESIL-08** 3 tentativas esgotadas → `falhou_coleta` + `Exceção` com causa, tentativas e impacto | `FALHOU_COLETA` + exceção com 3 campos | Aplicação: `B/testes/test_coleta_meteorologica.py:352-359` — `FALHOU_COLETA`, `len(excecoes.registradas)==1`, `"TimeoutException" in causa`, `tentativas == 3`, `impacto == IMPACTO_COLETA_INDISPONIVEL`. **Persistência real (Fix 8)**: `B/testes/test_repositorio_execucao_preventiva.py:100-103` — os 4 campos relidos por `SELECT` do DuckDB. Monotonicidade: `:64` — `pytest.raises(TransicaoInvalida)` | ✅ **PASS pleno** (era ⚠️ na Round 2) — sensor B confirma discriminação |
| **RESIL-09** `falhou_coleta` → UI `Indisponível` com snapshot marcado como desatualizado | estado + marcação de obsolescência | `F/…/SuperficieFonteMeteorologica.tsx:270-276` — `role="note"` condicionado a `indisponivel`; `…test.tsx:479` presença; `:489` **ausência** no estado `Operacional`; rótulo `:240`, função pura `:373` | ✅ PASS |
| **RESIL-10** nova tentativa → nova execução correlacionada em `coletando`, sem reabrir a terminal | nova sincronização ≠ origem; origem intocada | **Re-conferido nesta rodada**: `B/testes/test_coleta_meteorologica.py:442-446` — `aceita.sincronizacao.id != origem.id`, `estado == CONCLUIDO`, `len(eventos.salvos) == 1`, `sincronizacoes.estado_de(origem.id).estado == FALHA`, `execucoes.transicoes == execucoes_apos_origem`; rota `test_meteorologia_api.py:402-405` | ✅ PASS |
| **RESIL-11** mesma `Idempotency-Key` → não duplica coleta nem efeitos | 1 única coleta; resposta idêntica | `B/testes/test_coleta_meteorologica.py:465-467`; rota `test_meteorologia_api.py:425-427` (`primeira.json() == segunda.json()`); chave ausente `:384-386` — `422` + `problem+json` + `codigo == "idempotency_key_ausente"` | ✅ PASS |
| **RESIL-12** cenário sintético → coleta separada `sintetico`, sem combinar com `real_inmet` | `proveniencia == sintetico`, evento real preservado | **Re-conferido nesta rodada**: `B/testes/test_coleta_meteorologica.py:496-499` — `novo_evento.tipo == GRANIZO`, `novo_evento.proveniencia == SINTETICO` e **`eventos.salvos[0].proveniencia == REAL_INMET`** (não-combinação explícita); rota `test_meteorologia_api.py:473-474`; adaptador `test_adaptador_cenario_sintetico.py:46-47`; persistência `test_repositorio_meteorologia.py:263-268` | ✅ PASS |
| **RESIL-13** cenário ativo → origem sintética visível por texto e indicador acessível | rótulo textual da origem | `F/…/SuperficieFonteMeteorologica.tsx:115` (`sintetico → 'Sintético'`); badge `…test.tsx:251`; função pura `:380` | ⚠️ **Parcial — dívida aceita** (inalterada): `FlaskIcon` é `aria-hidden`, sem asserção dedicada do "indicador acessível" nem da explicação de contingência |
| **RESIL-14** recuperação real → registra recuperação, retoma agendamento, sem duplicar eventos | 1 única linha em `eventos_meteorologicos` | `B/testes/test_coleta_meteorologica.py:588` — `len(RepositorioEventosMeteorologicos(caminho).listar()) == 1` sobre repositórios DuckDB reais (`:526-563`); constraint `test_migracoes.py:151-160`; UI `…test.tsx:290` | ⚠️ **Parcial — dívida aceita** (inalterada): "retomar o agendamento automático" após falha tem só garantia estrutural (`coleta_meteorologica.py:335-339`), sem teste dedicado |
| **RESIL-15** UI distingue os 6 estados por texto, ícone e cor | 6 rótulos + ícone + cor | `F/…test.tsx:509-512` — `[data-icone="indisponivel"]` + `toHaveClass('estado-fonte-badge--indisponivel')` (cor) + `badge?.querySelector('svg')` (ícone). Texto dos 6: `:229,240,251,273,290,311`; função pura `:359,369,373,380,392,408,443` | ✅ PASS |
| **RESIL-16** cada estado expõe somente ações seguras e aplicáveis | ações por estado, nunca inseguras | `operacional` `…test.tsx:230-231`, `indisponivel` `:241-242`, `sintetica` `:252-253`, `degradada` `:274`, `em_tentativa` `:528-529`, `recuperada` `:546-547`; payload `:331`, `:352` | ✅ PASS |
| **RESIL-17** suíte cobre os 6 cenários (recuperação, esgotamento, snapshot, nova tentativa, sintético, recuperação real) | 6 cenários presentes | `test_coletor_com_retry.py:97`, `:115`; `test_coleta_meteorologica.py:334`, `:405`, `:424`, `:478`, `:565` | ✅ PASS |
| **RESIL-18** valores-limite de timeout/tentativas/backoff com dublês de tempo, sem tempo real nem INMET real | dublês de tempo; zero rede/sleep | Dublês: `test_coletor_com_retry.py:68-75`, `test_coleta_meteorologica.py:230-232`, `test_adaptador_cenario_sintetico.py:27`; rede bloqueada por fixture `autouse` `test_meteorologia_api.py:31` | ⚠️ **Parcial — dívida aceita** (inalterada): 3 testes de rota (`:375,389,408`) ainda aguardam ~3,3s de backoff real, sem seam de injeção de relógio no wiring de produção |

**Status**: ✅ **14/18 em PASS pleno, 0 GAPs de comportamento, 0 lacunas de cobertura conhecidas.** Os 4 ⚠️ restantes (RESIL-03, 13, 14, 18) são **dívida documentada e aceita explicitamente nas Rounds 1 e 2**, não achados novos. Nenhum AC regrediu: o diff `50e31fa..5575981` é puramente aditivo em 2 arquivos de teste, sem uma única linha de produção alterada (`git diff 50e31fa..5575981 -- src/` = +38/−0, só testes).

---

## Discrimination Sensor (Round 3)

**Método**: `git worktree add <scratch> 5575981 --detach`, um ciclo de worktree por mutação, worktree removido logo após. Baseline `git status --porcelain` da árvore real = **vazio antes e depois**.

| # | File:line | Mutação | Testes executados | Killed? |
| --- | --- | --- | --- | --- |
| **A** | `F/funcionalidades/fonte-meteorologica/SuperficieFonteMeteorologica.tsx:99` | **Re-injeção do mutante sobrevivente da Round 2**: `if (diffMinutos < 60)` → `if (diffMinutos <= 60)` | `vitest --run SuperficieFonteMeteorologica.test.tsx` | ✅ **Killed** — `calcularIdade > no limite exato de 60 minutos…` → `AssertionError: expected '60 min atrás' to be '1 h atrás'` (**1 failed / 36 passed**) |
| **B** | `B/central_preventiva/adaptadores/persistencia/repositorio_execucao_preventiva.py:124` | Troca dos argumentos posicionais `causa` ↔ `impacto` no `INSERT`: `[uuid4(), execucao_id, causa, tentativas, impacto]` → `[uuid4(), execucao_id, impacto, tentativas, causa]` | `pytest testes/test_repositorio_execucao_preventiva.py` | ✅ **Killed** — `test_registrar_excecao_operacional_persiste_causa_tentativas_e_impacto` → `AssertionError: assert 'Coleta meteo...indisponível.' == 'TimeoutException: timeout'` (**1 failed / 4 passed**) |

**Sensor depth**: lightweight (2 mutações dirigidas, exatamente as duas lacunas da Round 2)
**Result**: **2/2 killed — ✅ PASS**

### Nota de método (armadilha encontrada e corrigida na própria rodada)

A primeira tentativa da mutação B reportou "sobreviveu" (268 passed) e foi **descartada como inválida**. Causa: o `.venv` do backend foi inicialmente *copiado* para o worktree, mas ele carrega um install **editable apontando para o caminho absoluto do repositório real**; sob `pytest`, `central_preventiva` resolvia para `/Users/rafael/…/Desafio5/src/backend/…` (confirmado por `m.__file__` impresso de dentro do processo de teste) — ou seja, os testes rodavam contra o código **não mutado**. Refeito com um `.venv` criado do zero dentro do worktree, o mutante morre imediatamente. A árvore real nunca foi mutada em nenhum momento (verificado: `git status --porcelain` vazio e o `INSERT` original intacto em `repositorio_execucao_preventiva.py:124`).

### Isolamento verificado após o sensor

```text
git status --porcelain   → (vazio)
git worktree list        → /Users/rafael/…/Desafio5  5575981 [main]   (só o principal)
git rev-parse HEAD       → 55759816da3001926b6ae9a7bc0fd0cfead99d91
```

---

## Payload / Conjunction Rule (rotas HTTP e repositórios)

| Superfície | Verificação | Resultado |
| --- | --- | --- |
| `POST /{id}/nova-tentativa` | `test_meteorologia_api.py:404-405`, `:427`, `:440` | ✅ |
| `POST /cenarios-sinteticos/{id}/ativar` | `:470,473-474`, `:499` | ✅ |
| `GET /sincronizacoes` | `:269-272` — `limite_tentativas == 3` + campos da tentativa | ✅ |
| `RepositorioTentativasColeta` | `test_repositorio_meteorologia.py:207-253` — instantes exatos, ordenação, caso vazio | ✅ |
| `RepositorioCenariosSinteticosAtivados` | `test_repositorio_meteorologia.py:256-268` — `SELECT` direto | ✅ |
| **`RepositorioExcecoesOperacionais`** | **Fechado pelo Fix 8** — `test_repositorio_execucao_preventiva.py:93-103`, `SELECT` direto com os 4 campos por igualdade exata | ✅ **(era ⚠️)** |

**As 3 tabelas da matriz de repositórios estão agora lidas de volta do DuckDB real.**

---

## Edge Cases

- [x] **Segunda tentativa no limite exato do timeout → falha de timeout, não sucesso tardio**: coberto por proxy — `httpx.TimeoutException` → `CodigoResultadoTentativa.TIMEOUT` (`test_coletor_com_retry.py:108,131`), nunca sucesso; o limite literal é imposto pelo `timeout=5s` do `ClienteInmet` (2.1). ⚠️ valor-limite literal não exercitado (dívida aceita).
- [x] **Ativar cenário sintético durante coleta real em `coletando`**: garantia estrutural — `ativar_cenario_sintetico` cria a própria `Sincronizacao` e nunca toca outra (`coleta_meteorologica.py:417-430`).
- [ ] **Reinício do backend com execução em `coletando`**: **não coberto**. Dívida aceita e registrada nas Rounds 1 e 2, consistente com a limitação de coleta síncrona herdada da História 2.1.

---

## Code Quality

| Princípio | Status |
| --- | --- |
| Código mínimo | ✅ Fix 7–8 tocaram **2 arquivos, ambos de teste**; `+38/−0` em `src/` |
| Mudanças cirúrgicas | ✅ **zero linhas de produção alteradas** nesta rodada |
| Sem scope creep | ✅ os 4 testes novos endereçam exatamente os 2 gaps da Round 2 |
| Segue os padrões existentes | ✅ Fix 7 estende o `describe('calcularIdade')` existente; Fix 8 reusa `preparar_banco` e o padrão de `SELECT` direto já estabelecido pelo Fix 6 |
| Nenhuma asserção enfraquecida | ✅ verificado no diff: **nenhuma linha removida** em nenhum dos dois arquivos |
| Nenhum teste removido | ✅ backend 267 → **268**; frontend 148 → **151** (+4, exatamente os 4 do Fix 7–8) |
| Spec-anchored outcome check | ✅ os 4 testes novos asserem valores exatos (`toBe`/`==`), nunca predicados frouxos |
| Coverage Expectation por camada | ✅ as 3 tabelas da matriz agora relidas; domínio com mapeamento 1:1 a ACs; rotas com happy + edge + error |
| Todo teste mapeia a um AC / edge case / Done-when | ✅ os 3 do Fix 7 → RESIL-06; o do Fix 8 → RESIL-08 |
| Guidelines documentadas seguidas | ✅ `AGENTS.md`, `README.md` |

---

## Gate Check (re-executado integralmente por este Verifier em `5575981`)

| Comando | Resultado |
| --- | --- |
| `uv run --directory src/backend pytest` | **268 passed** em 16,54s — 0 failed, 0 skipped |
| `uv run --directory src/backend ruff check .` | `All checks passed!` |
| `uv run --directory src/backend pyright` | `0 errors, 0 warnings, 0 informations` |
| `npm test --prefix src/frontend -- --run` | **151 passed** (18 arquivos) em 5,39s — 0 failed, 0 skipped |
| `npm run lint --prefix src/frontend` (oxlint) | 8 warnings — **exatamente as mesmas 8 da Round 2**, todas de 2 categorias pré-existentes (`react(set-state-in-effect)`, `react(only-export-components)`). Nenhuma nova |
| `npm run build --prefix src/frontend` | `✓ built in 230ms` |

- **Test count antes da feature**: backend 212, frontend 95 (baseline pré-`e7a3410`, per Round 1)
- **Test count depois**: backend **268**, frontend **151** — **delta total da feature: +112 testes**
- **Delta desta rodada**: backend +1 (Fix 8), frontend +3 (Fix 7) — bate exatamente com o prometido
- **Skipped**: nenhum, em nenhuma das duas suítes
- **Failures**: nenhuma

---

## Fix Plans

Nenhum. Os dois gaps da Round 2 estão fechados e comprovados por sensor. Os 4 itens ⚠️ remanescentes são dívida técnica documentada e **aceita explicitamente** pelo usuário/orquestrador nas Rounds 1 e 2 — não são fix tasks abertas:

| Item | Natureza | Registro |
| --- | --- | --- |
| RESIL-03 | Constantes de módulo em vez de env vars | Documentado em `…/meteorologia/README.md:89-92` |
| RESIL-13 | Ícone sintético `aria-hidden`, sem asserção de acessibilidade dedicada | Round 1 |
| RESIL-14 | Retomada automática do agendamento com garantia só estrutural | Round 1 |
| RESIL-18 | 3 testes de rota aguardam ~3,3s de backoff real (sem seam de relógio no wiring) | Round 1, nota de T6 |
| Edge case 3 | Reinício com execução em `coletando` | Round 1 (limitação herdada de 2.1) |

---

## Requirement Traceability Update

| Requirement | Round 1 | Round 2 | **Round 3 (final)** |
| --- | --- | --- | --- |
| RESIL-01 | ✅ Verified | ✅ Verified | ✅ **Verified** |
| RESIL-02 | ⚠️ ressalva | ✅ Verified | ✅ **Verified** |
| RESIL-03 | ⚠️ desvio assumido | ⚠️ desvio assumido | ⚠️ **Verified com desvio documentado e aceito** |
| RESIL-04 | ✅ Verified | ✅ Verified | ✅ **Verified** |
| RESIL-05 | ✅ Verified | ✅ Verified | ✅ **Verified** |
| RESIL-06 | ❌ Needs Fix | ⚠️ ressalva (limiares) | ✅ **Verified** (Fix 2 + Fix 7, sensor A) |
| RESIL-07 | ✅ Verified | ✅ Verified | ✅ **Verified** |
| RESIL-08 | ⚠️ ressalva | ✅ Verified (sem readback) | ✅ **Verified** (Fix 8, sensor B) |
| RESIL-09 | ❌ Needs Fix | ✅ Verified | ✅ **Verified** |
| RESIL-10 | ✅ Verified | ✅ Verified | ✅ **Verified** |
| RESIL-11 | ✅ Verified | ✅ Verified | ✅ **Verified** |
| RESIL-12 | ✅ Verified | ✅ Verified | ✅ **Verified** |
| RESIL-13 | ⚠️ ressalva | ⚠️ ressalva | ⚠️ **Verified com dívida aceita** |
| RESIL-14 | ⚠️ ressalva | ⚠️ ressalva | ⚠️ **Verified com dívida aceita** |
| RESIL-15 | ❌ Needs Fix | ✅ Verified | ✅ **Verified** |
| RESIL-16 | ⚠️ ressalva | ✅ Verified | ✅ **Verified** |
| RESIL-17 | ✅ Verified | ✅ Verified | ✅ **Verified** |
| RESIL-18 | ⚠️ ressalva | ⚠️ ressalva | ⚠️ **Verified com dívida aceita** |

---

## Estado das lições

| Lição | Condição subjacente | Fechada? |
| --- | --- | --- |
| **L-014** testar a interseção onde duas condições de derivação valem ao mesmo tempo | 2 testes de interseção matam ambas as mutações de ordem | ✅ Fechada (Round 2) |
| **L-015** implementar e asserir cada substantivo do outcome do AC | "idade calculada" implementada, renderizada e asserida | ✅ Fechada (Round 2) |
| **L-016** quando o AC exige texto, ícone e cor, asserir as três dimensões | `data-icone` + classe + SVG asseridos | ✅ Fechada (Round 2) |
| **L-017** definir **na spec** qual estado vence quando mais de uma condição é verdadeira | A precedência está no docstring da função, não em `spec.md` | ⚠️ Parcialmente fechada (inalterada) |
| **L-018** declarar explicitamente se um valor configurável precisa ser configurável em runtime | Não endereçado (dívida aceita: RESIL-03) | ⚠️ Aberta por decisão |
| **L-019** testar um limiar em cada valor de fronteira exato, não só no meio da faixa | 3 testes de fronteira adicionados e **comprovadamente matadores** (sensor A) | ✅ **Fechada nesta rodada** |

Nenhuma lição nova destilada: a Round 3 é um PASS limpo, sem mutante sobrevivente, sem AC descoberto e sem `SPEC_DEVIATION` novo.

---

## Summary

**Overall**: ✅ **Ready**

**Spec-anchored check**: 14/18 em PASS pleno; **0 gaps de comportamento; 0 lacunas de cobertura conhecidas**; 4 ⚠️ de precisão/dívida, todos já aceitos e documentados nas rodadas anteriores
**Sensor**: **2/2 mutantes mortos** — a re-injeção exata do sobrevivente da Round 2 (`< 60` → `<= 60`) agora morre, e a troca `causa` ↔ `impacto` no `INSERT` é detectada pelo novo readback
**Gate**: verde e re-executado integralmente — **268 backend + 151 frontend**, 0 falhas, 0 skips; ruff, pyright, oxlint e build limpos

**O que funciona**: retentativa limitada a 3 tentativas com backoff 1s/2s e registro individual por tentativa (número, instantes, código, correlação) relido do DuckDB real; terminal explícito `falhou_coleta` com `Exceção` cujos `causa`/`tentativas`/`impacto` são conferidos por igualdade exata **tanto na aplicação quanto na tabela**; snapshot antigo preservado com origem, horário e idade calculada — esta última agora discriminada nos três limiares exatos (1 min / 60 min / 24 h) — e comprovadamente incapaz de disparar nova avaliação; nova tentativa explícita idempotente que não reabre a execução terminal; cenário sintético isolado de `real_inmet` com proveniência asserida nos dois lados; recuperação real sem duplicação de eventos sobre repositórios DuckDB reais; os 6 estados da fonte distinguidos por texto, ícone e cor, cada um com seu conjunto de ações asserido por presença **e** por ausência.

**Issues found**: nenhuma bloqueante. Permanecem 4 itens de dívida documentada (RESIL-03 configurabilidade por env var; RESIL-13 asserção de acessibilidade do indicador sintético; RESIL-14 teste dedicado de retomada do agendamento; RESIL-18 seam de relógio nas 3 rotas com backoff real) e 1 edge case não coberto (reinício com execução em `coletando`, herdado da limitação síncrona de 2.1).

**Next steps**: História 2.2 aprovada. Encerrar o laço de verificação (Round 3 de 3, concluído com PASS) e atualizar o status dos 18 requisitos de `Implementing` para `Verified` em `spec.md`. Os itens de dívida acima devem ser levados como entrada para o planejamento da próxima história, não como retrabalho desta.
