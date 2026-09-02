# História 2.2: Operar com segurança durante indisponibilidades meteorológicas — Validation

**Date**: 2026-09-02
**Spec**: `.specs/features/2-2-operar-com-seguranca-durante-indisponibilidades-meteorologicas/spec.md`
**Diff range**: `e7a3410..50e31fa` (8 commits: T1–T7 + `50e31fa` "fix(meteorologia): fechar lacunas do verificador da historia 2.2")
**Verifier**: independent sub-agent (author ≠ verifier), read-only sobre a árvore real
**Rodada**: **Round 2 — re-verificação após Fix 1–6** (commit `50e31fa` sobre `2a6efa8`). A Round 1 (`e7a3410..2a6efa8`) reportou FAIL; este relatório a substitui.

**Verdict**: ❌ **FAIL (Minor)** — todos os 3 gaps *Major* da Round 1 estão genuinamente fechados e verificados de forma independente, mas o **Fix 2 introduziu um novo mutante sobrevivente**: os três limiares de `calcularIdade` (1 min / 60 min / 24 h) não são exercitados nos seus valores exatos, então `<` pode virar `<=` em qualquer um dos três sem que a suíte perceba. Correção de ~3 asserções; nenhum impacto de segurança.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 Migração `0003` | ✅ Done | `testes/test_migracoes.py:118` — recreate-and-copy + `ON CONFLICT DO NOTHING` |
| T2 `RepositorioExecucaoPreventiva` | ✅ Done | 4 testes de integração (criar/transicionar/conflito/terminal) |
| T3 `ColetorComRetry` | ✅ Done | 4 testes unitários com dublês de tempo |
| T4 `AdaptadorCenarioSintetico` | ✅ Done | Desvio documentado (relógio corrente) justificado |
| T5 Extensão do caso de uso | ✅ Done | Antes ⚠️ Partial; "idade calculada" (RESIL-06) fechada pelo Fix 2 no cliente |
| T6 Extensão do roteador | ✅ Done | 7 testes de rota (happy + edge + error) |
| T7 Frontend 6 estados | ✅ Done | Antes ⚠️ Partial; ícone/cor (Fix 4), aviso de desatualizado (Fix 3) e ações ausentes em 2 estados (Fix 5) agora asseridos |
| Fix 1 (precedência `calcularEstadoFonte`) | ✅ Done | 2 testes de interseção — **confirmados matadores** pelo sensor abaixo |
| Fix 2 (`calcularIdade`, RESIL-06) | ⚠️ Partial | Função implementada e renderizada; **limiares não asseridos nos valores exatos** (ver Sensor) |
| Fix 3 (aviso de desatualizado, RESIL-09) | ✅ Done | `role="note"` só em `indisponivel`, presença e ausência asseridas |
| Fix 4 (ícone/cor, RESIL-15) | ✅ Done | `data-icone` + classe + SVG asseridos |
| Fix 5 (ações ausentes, RESIL-16) | ✅ Done | `em_tentativa` e `recuperada` cobertos |
| Fix 6 (matriz de cobertura de repositórios) | ⚠️ Partial | `tentativas_coleta_meteorologica` e `cenarios_sinteticos_ativados` lidos do DuckDB real; **`excecoes_operacionais` continua sem `SELECT` de volta** (só `test_migracoes.py:31` confere a existência da tabela) |

---

## Spec-Anchored Acceptance Criteria

Prefixos: `B/` = `src/backend/`, `F/` = `src/frontend/src/`.
Linhas conferidas em `50e31fa`.

| Critério (RESIL) | Outcome definido na spec | `file:line` + asserção | Result |
| --- | --- | --- | --- |
| **RESIL-01** falha temporária/timeout/resposta inválida → timeout + no máx. 3 tentativas, espera configurável | 3 tentativas totais, backoff 1s/2s | `B/testes/test_coletor_com_retry.py:107` — `assert tentativas.registradas == [(…,1,TIMEOUT),(…,2,ERRO_TRANSPORTE),(…,3,SUCESSO)]`; `:112` — `assert espera.esperas == [1.0, 2.0]`; `:126` — `assert coletor.chamadas == 3`. Timeout de 5s herdado de `ClienteInmet` (2.1), documentado em `B/…/meteorologia/README.md:77` | ✅ PASS |
| **RESIL-02** cada tentativa registra número, início, término, código do resultado e correlação | número + código + `sincronizacao_id`; início/término sem valor preciso na spec | **Fechado pelo Fix 6**: `B/testes/test_repositorio_meteorologia.py:220-222` — `numero_tentativa == 1`, `codigo_resultado == TIMEOUT`, **`iniciado_em == inicio`** e **`finalizado_em == fim`** relidos do DuckDB real; ordenação `:245`; vazio `:252`. Unitário: `test_coletor_com_retry.py:91,107,130` | ✅ PASS (era ⚠️ Parcial) |
| **RESIL-03** intervalo, timeout, tentativas e backoff exatos, configuráveis e documentados | Spec (Assumptions): "configuráveis por variável de ambiente" | Valores exatos: `B/…/aplicacao/coleta_meteorologica.py:31,34`; documentados em `B/…/meteorologia/README.md:73-92`. Configurabilidade externa continua inexistente (constantes de módulo, injetáveis só por construtor) | ⚠️ Spec-precision gap / **desvio assumido e documentado** (README:89-92) — inalterado |
| **RESIL-04** documentação justifica padrões e descreve comportamento observável por tipo de falha | 4 tipos de falha + justificativa dos 3 parâmetros | `B/…/adaptadores/meteorologia/README.md:75-79` e `:83-87` | ✅ PASS |
| **RESIL-05** enquanto houver tentativas → UI mostra tentativa atual e limite de três | texto "tentativa atual / 3" | `F/…/SuperficieFonteMeteorologica.test.tsx:312` — `expect(screen.getByText('Tentativa 2 de 3'))`; backend `B/testes/test_meteorologia_api.py:269` — `limite_tentativas == 3` | ✅ PASS |
| **RESIL-06** snapshot válido antigo continua consultável com **origem, horário e idade calculada** | os 3 atributos acompanhando o snapshot | **Fechado pelo Fix 2**: `F/…/SuperficieFonteMeteorologica.tsx:94-106` (`calcularIdade`) renderizada na coluna "Idade" `:292,309`; unitários `…test.tsx:451,455,459,463` (`'agora mesmo'`, `'30 min atrás'`, `'6 h atrás'`, `'2 d atrás'`); componente `:499` — `findByText('1 h atrás')` com timestamp real de 90 min. Origem/horário: `.tsx:307,308` + `…test.tsx:149` (`'INMET (real)'`). Permanência: `B/testes/test_coleta_meteorologica.py:421` — `assert eventos.salvos == [snapshot_anterior]` | ✅ PASS no comportamento — ⚠️ ver Sensor (limiares não discriminados) |
| **RESIL-07** snapshot antigo consultado durante falha → nenhuma nova avaliação/alerta/mensagem | nenhum evento novo derivado | `B/testes/test_coleta_meteorologica.py:420-421` — estado `FALHA` e a lista permanece exatamente `[snapshot_anterior]`; nenhum caminho de avaliação de risco é invocado | ✅ PASS |
| **RESIL-08** 3 tentativas esgotadas → `falhou_coleta` + `Exceção` com causa, tentativas e impacto | estado `FALHOU_COLETA`, exceção com 3 campos | `B/testes/test_coleta_meteorologica.py:352` — `novo_estado == EstadoExecucao.FALHOU_COLETA`; `:353` — `execucoes.estado_de(execucao_id) == FALHOU_COLETA`; `:355-359` — `len(excecoes.registradas)==1`, `excecao_execucao_id == execucao_id`, `"TimeoutException" in causa`, `tentativas == 3`, **`impacto == IMPACTO_COLETA_INDISPONIVEL`** (Fix 6 substituiu o `!= ""`); monotonicidade: `test_repositorio_execucao_preventiva.py:64` — `pytest.raises(TransicaoInvalida)` | ✅ PASS (era ⚠️ Parcial) — resta a linha de `excecoes_operacionais` nunca relida do DuckDB |
| **RESIL-09** `falhou_coleta` → UI mostra `Indisponível` com o snapshot antigo **claramente identificado como desatualizado** | estado `Indisponível` + marcação de obsolescência | **Fechado pelo Fix 3**: `F/…/SuperficieFonteMeteorologica.tsx:270-276` — `{estadoFonte === 'indisponivel' && <p role="note">… Dados desatualizados …}`; `…test.tsx:479` — `findByText(/Dados desatualizados/)` presente no estado `Indisponível`; `:489` — `queryByText(/Dados desatualizados/)` **ausente** no estado `Operacional`; rótulo `Indisponível` `:240` e função pura `:373` | ✅ PASS |
| **RESIL-10** nova tentativa explícita → nova execução correlacionada em `coletando`, id/chave próprios, sem reabrir a terminal | nova sincronização ≠ origem; origem intocada | `B/testes/test_coleta_meteorologica.py:441-445` — `aceita.sincronizacao.id != origem.id`, `sincronizacoes.estado_de(origem.id).estado == FALHA`, `execucoes.transicoes == execucoes_apos_origem`; rota `test_meteorologia_api.py:402-405` — `202` + `corpo["id"] != sincronizacao_id` + `estado == "concluido"` | ✅ PASS |
| **RESIL-11** repetir a mesma `Idempotency-Key` → não duplica coleta nem efeitos | 1 única coleta; resposta idêntica | `B/testes/test_coleta_meteorologica.py:465-467`; rota `test_meteorologia_api.py:425-427` (`primeira.json() == segunda.json()`); ausência de chave `:384-386` — `422` + `problem+json` + `codigo == "idempotency_key_ausente"` | ✅ PASS |
| **RESIL-12** cenário sintético → coleta separada com proveniência `sintetico`, sem combinar com `real_inmet` | `proveniencia == sintetico`, evento real preservado à parte | `B/testes/test_coleta_meteorologica.py:494-499`; rota `test_meteorologia_api.py:473-474`; adaptador `test_adaptador_cenario_sintetico.py:46-47`; **Fix 6** — persistência real da ativação: `test_repositorio_meteorologia.py:263-268` — `SELECT … FROM cenarios_sinteticos_ativados` com `identificador_cenario == "granizo-demonstrativo"` | ✅ PASS |
| **RESIL-13** cenário ativo → origem sintética visível por texto e indicador acessível | rótulo textual da origem | `F/…/SuperficieFonteMeteorologica.tsx:115` (`sintetico → 'Sintético'`) na coluna Origem; badge `…test.tsx:251` — `findByText('Sintética')`; `:380` — função pura | ⚠️ Parcial — inalterado: o ícone `FlaskIcon` é `aria-hidden` e não há asserção do "indicador acessível" nem da explicação de contingência (dívida aceita na Round 1) |
| **RESIL-14** recuperação real → registra recuperação, retoma agendamento, sem duplicar eventos | 1 única linha em `eventos_meteorologicos` | `B/testes/test_coleta_meteorologica.py:588` — `len(RepositorioEventosMeteorologicos(caminho).listar()) == 1` sobre repositórios DuckDB **reais** (`:526-563`); constraint `test_migracoes.py:151-160`; UI `…test.tsx:290` — `findByText('Recuperada')` | ⚠️ Parcial — inalterado: "retomar o agendamento automático" após falha só tem garantia estrutural (`coleta_meteorologica.py:335-339`), sem teste dedicado (dívida aceita) |
| **RESIL-15** UI distingue os 6 estados por **texto, ícone e cor** | 6 rótulos + ícone + cor por estado | **Fechado pelo Fix 4**: `F/…test.tsx:509-512` — `container.querySelector('[data-icone="indisponivel"]')` + `toHaveClass('estado-fonte-badge--indisponivel')` (cor) + `badge?.querySelector('svg')` (ícone). Texto dos 6: `:229,240,251,273,290,311` e função pura `:359,369,373,380,392,408,443` | ✅ PASS (era ❌) — a asserção de ícone/cor cobre 1 dos 6 estados; a implementação é a mesma expressão parametrizada por `estadoFonte` (`.tsx:219-222`), então a generalização é estrutural |
| **RESIL-16** cada estado expõe somente ações seguras e aplicáveis | ações por estado, nunca inseguras | **Fechado pelo Fix 5**: os 6 estados agora têm asserção de ações — `operacional` `…test.tsx:230-231`, `indisponivel` `:241-242`, `sintetica` `:252-253`, `degradada` `:274`, `em_tentativa` `:528-529`, `recuperada` `:546-547`; payload das ações `:331`, `:352` | ✅ PASS (era ⚠️ Parcial) |
| **RESIL-17** suíte cobre recuperação antes do limite, esgotamento, snapshot, nova tentativa, ativação sintética e recuperação real sem duplicação | 6 cenários presentes | `test_coletor_com_retry.py:97` / `:115`; `test_coleta_meteorologica.py:334`, `:405`, `:424`, `:478`, `:565` | ✅ PASS |
| **RESIL-18** valores-limite de timeout, tentativas e backoff com dublês de tempo, sem tempo real nem INMET real | dublês de tempo; zero rede/sleep | Dublês: `test_coletor_com_retry.py:68-75`, `test_coleta_meteorologica.py:230-232`, `test_adaptador_cenario_sintetico.py:27`; rede bloqueada por fixture `autouse` `test_meteorologia_api.py:31`. 3 testes de rota (`:375,389,408`) ainda aguardam ~3,3s de backoff real | ⚠️ Parcial — inalterado (dívida aceita, registrada na Nota de T6) |

**Status**: ✅ 14/18 em PASS pleno (era 9/18) — 0 GAPs de comportamento (eram 2) — 4 ⚠️ parciais, **todos já aceitos e documentados na Round 1** (RESIL-03, RESIL-13, RESIL-14, RESIL-18). Nenhum AC anteriormente em PASS regrediu.

---

## Discrimination Sensor (Round 2)

Worktree isolado (`git worktree add <scratch> 50e31fa --detach`, `node_modules` por symlink), arquivo revertido com `git checkout --` entre mutações, worktree removido ao final. Baseline `git status --porcelain` da árvore real = **vazio antes e depois**; `git worktree list` volta a listar só o repositório principal; `HEAD` = `50e31fa`.

| # | File:line | Mutação | Testes executados | Killed? |
| --- | --- | --- | --- | --- |
| A | `SuperficieFonteMeteorologica.tsx:67-70` | **Re-injeção do mutante da Round 1**: trocada a ordem `recuperada` ↔ `degradada` | `vitest --run SuperficieFonteMeteorologica.test.tsx` | ✅ **Killed** — `precedência: recuperada vence degradada …` → `AssertionError: expected 'degradada' to be 'recuperada'` (1 failed / 33 passed) |
| A2 | `SuperficieFonteMeteorologica.tsx:63-65` | Trocada a ordem `indisponivel` ↔ `sintetica` | idem | ✅ **Killed** — `precedência: indisponivel vence sintetica …` (1 failed / 33 passed) |
| B | `SuperficieFonteMeteorologica.tsx:99` | `if (diffMinutos < 60)` → `<= 60` | idem | ❌ **Survived** — 34/34 passaram |
| B2 | `SuperficieFonteMeteorologica.tsx:98` | `if (diffMinutos < 1)` → `<= 1` | idem | ❌ **Survived** — 34/34 passaram |
| B3 | `SuperficieFonteMeteorologica.tsx:102` | `if (diffHoras < 24)` → `<= 24` | idem | ❌ **Survived** — 34/34 passaram |
| B4 | `SuperficieFonteMeteorologica.tsx:101` | `Math.floor(diffMinutos / 60)` → `Math.round(...)` | idem | ✅ **Killed** (1 failed / 33 passed) |

**Sensor depth**: lightweight (2 mutações planejadas + 4 de caracterização do achado)
**Result**: **3/6 killed — ❌ FAIL**

**Análise do sobrevivente (novo, introduzido pelo Fix 2)**: os quatro testes de `calcularIdade` (`…test.tsx:450-464`) usam **valores no meio de cada faixa** — 30 s, 30 min, 6 h, 2 d — e não os limiares exatos (1 min, 60 min, 24 h). O teste de componente `:492-500` usa 90 min, também no meio da faixa de horas. Logo os três `<` podem virar `<=` sem quebrar nada: com 60 min exatos a UI passaria a mostrar `60 min atrás` em vez de `1 h atrás`. A afirmação "4 testes de valores-limite" na nota de Fix 2 (`tasks.md:329`) não se sustenta — são testes de faixa, não de fronteira. Severidade **Minor**: a diferença é só de rótulo e não afeta nenhuma garantia de segurança da história; a correção são 3 asserções (`calcularIdade(…, 1 min) === '1 min atrás'`, `(…, 60 min) === '1 h atrás'`, `(…, 24 h) === '1 d atrás'`).

**Confirmação da Round 1 fechada**: o mutante que sobreviveu na Round 1 (mutação #3) foi re-injetado **na sua forma original** e agora morre, assim como a sua variante simétrica. O Fix 1 é real e verificado de forma independente.

---

## Verificação de flakiness do teste de tempo real (Fix 2)

O teste `exibe a idade calculada de cada evento ao lado do horário` (`…test.tsx:492-500`) usa `new Date(Date.now() - 90 * 60_000).toISOString()` em vez de `vi.useFakeTimers()`.

- **Empírico**: 3 execuções consecutivas de `vitest --run SuperficieFonteMeteorologica.test.tsx` → `34 passed` nas 3.
- **Raciocínio**: `calcularIdade` recalcula com `new Date()` no render, ou seja `diffMinutos = floor((90 min + Δ)/1 min)` onde Δ é o tempo entre o `Date.now()` do arranjo e o render (milissegundos). O valor só sairia de `1 h atrás` se Δ ≥ 30 min (para chegar a 120 min) — 4 ordens de grandeza acima do observado. A margem para a fronteira mais próxima (60 min → 120 min) é de 30 minutos inteiros. **Não é frágil.**
- Ressalva de forma, não de estabilidade: por não injetar relógio, o teste não *pode* exercitar a fronteira exata — é exatamente a razão pela qual os mutantes B/B2/B3 sobrevivem. A fronteira deve ser coberta pelos unitários puros (que aceitam `agora` como parâmetro), não por este teste.

---

## Payload / Conjunction Rule (rotas HTTP e repositórios)

| Superfície | Verificação | Resultado |
| --- | --- | --- |
| `POST /{id}/nova-tentativa` | `test_meteorologia_api.py:404-405` (id ≠ origem + `estado`), `:427` (corpos completos idênticos), `:440` (`codigo == "sincronizacao_desconhecida"`) | ✅ |
| `POST /cenarios-sinteticos/{id}/ativar` | `:470,473-474` conferem `estado`, `tipo` e `proveniencia` do evento persistido; `:499` confere ausência de segundo evento | ✅ |
| `GET /sincronizacoes` | `:269-272` — `limite_tentativas == 3` + campos da tentativa | ✅ |
| `RepositorioTentativasColeta` | **Fechado pelo Fix 6** — `test_repositorio_meteorologia.py:207-253`: valores exatos de `iniciado_em`/`finalizado_em`, ordenação por número e caso vazio, contra DuckDB real | ✅ (era ⚠️) |
| `RepositorioCenariosSinteticosAtivados` | **Fechado pelo Fix 6** — `test_repositorio_meteorologia.py:256-268`, `SELECT` direto na tabela | ✅ (era ⚠️) |
| `RepositorioExcecoesOperacionais` | Continua sem `SELECT` de volta em `excecoes_operacionais`; só `test_migracoes.py:31` confere a existência da tabela. O campo `impacto` agora é conferido por valor exato no nível de aplicação (`test_coleta_meteorologica.py:359`) | ⚠️ Gap residual (Minor) — Fix 6 cobriu 2 das 3 tabelas prometidas |

---

## Edge Cases

- [x] **Segunda tentativa no limite exato do timeout → falha de timeout, não sucesso tardio**: coberto por proxy — `httpx.TimeoutException` → `CodigoResultadoTentativa.TIMEOUT` (`test_coletor_com_retry.py:108,131`), nunca sucesso; o limite literal é imposto pelo `timeout=5s` do `ClienteInmet` (2.1). ⚠️ valor-limite literal não exercitado (inalterado).
- [x] **Ativar cenário sintético durante coleta real em `coletando`**: garantia estrutural — `ativar_cenario_sintetico` cria a própria `Sincronizacao` e nunca toca outra (`coleta_meteorologica.py:417-430`); concorrência não exercitada (coleta síncrona, limitação de 2.1).
- [ ] **Reinício do backend com execução em `coletando`**: **não coberto** por código nem por teste. Dívida aceita e registrada na Round 1 (consistente com a limitação síncrona de 2.1).

---

## Code Quality

| Princípio | Status |
| --- | --- |
| Código mínimo | ✅ o Fix tocou 5 arquivos, 3 deles de teste; `+604/−3` |
| Mudanças cirúrgicas | ✅ nenhuma alteração de lógica em `calcularEstadoFonte`; só docstring + código novo aditivo |
| Sem scope creep | ✅ |
| Segue os padrões existentes | ✅ (função pura exportada + teste unitário, mesmo padrão de `calcularEstadoFonte`) |
| Nenhuma asserção enfraquecida | ✅ **verificado no diff**: a única linha removida em `…test.tsx` é o `import` reescrito em bloco; a única remoção em `test_coleta_meteorologica.py` é `impacto != ""` → substituída por igualdade exata (**fortalecida**) |
| Nenhum teste removido | ✅ backend 263 → 267; frontend 136 → 148 |
| Spec-anchored outcome check | ⚠️ 0 gaps de comportamento, 4 parciais aceitos |
| Coverage Expectation por camada | ⚠️ 2 das 3 tabelas da linha de matriz agora relidas; `excecoes_operacionais` pendente |
| Todo teste mapeia a um AC / edge case / Done-when | ✅ os 16 testes novos mapeiam a RESIL-02/06/09/12/15/16 |
| Guidelines documentadas seguidas | ✅ `AGENTS.md`, `README.md` |
| Nota menor (não bloqueante) | `test_repositorio_meteorologia.py:194` — o helper `_criar_sincronizacao` declara `-> object`, obrigando 8 `# type: ignore[attr-defined]` nos 4 testes novos; um retorno tipado eliminaria os ignores. `pyright` está verde, então é estilo, não defeito |

---

## Gate Check (re-executado por este Verifier em `50e31fa`)

| Comando | Resultado |
| --- | --- |
| `uv run --directory src/backend pytest` | **267 passed** em 16,62s — 0 failed, 0 skipped |
| `uv run --directory src/backend ruff check .` | `All checks passed!` |
| `uv run --directory src/backend pyright` | `0 errors, 0 warnings, 0 informations` |
| `npm test --prefix src/frontend -- --run` | **148 passed** (18 arquivos) em 6,04s — 0 failed, 0 skipped |
| `npm run lint --prefix src/frontend` (oxlint) | 8 warnings, **todas de 2 categorias pré-existentes** (`react(set-state-in-effect)`, `react(only-export-components)`). O Fix acrescentou 1 ocorrência: `SuperficieFonteMeteorologica.tsx:94` (`only-export-components`, pela exportação de `calcularIdade`) — mesma categoria já existente em `:56` por `calcularEstadoFonte`. **Nenhuma categoria nova.** |
| `npm run build --prefix src/frontend` | `✓ built in 225ms` |

- **Delta de testes da rodada de correção**: backend +4 (`test_repositorio_meteorologia.py`), frontend +12 (2 de precedência, 4 de `calcularIdade`, 6 no novo `describe`). Total do feature: +~56.
- **Skipped**: nenhum, em nenhuma das duas suítes.
- **Flakiness**: `SuperficieFonteMeteorologica.test.tsx` executado 3× isoladamente — 34/34 nas 3.

---

## Fix Plans

### Fix 7: `calcularIdade` — limiares não discriminados (mutante sobrevivente, novo na Round 2)

- **Root cause**: os 4 testes unitários de `calcularIdade` (`…test.tsx:450-464`) e o teste de componente (`:492`) usam valores no **meio** de cada faixa (30 s, 30 min, 6 h, 2 d, 90 min). Nenhum incide sobre os limiares exatos, então `< 1`, `< 60` e `< 24` podem virar `<=` sem detecção.
- **Fix task**: adicionar 3 asserções na função pura (que já aceita `agora` como parâmetro, portanto determinística):
  - `calcularIdade(agora − 1 min, agora) === '1 min atrás'` (não `'agora mesmo'`)
  - `calcularIdade(agora − 60 min, agora) === '1 h atrás'` (não `'60 min atrás'`)
  - `calcularIdade(agora − 24 h, agora) === '1 d atrás'` (não `'24 h atrás'`)
- **Verify**: re-injetar `< 60` → `<= 60` e confirmar que o novo teste falha.
- **Priority**: **Minor** (rótulo de exibição; zero impacto nas garantias de segurança da história)

### Fix 8 (opcional): `excecoes_operacionais` sem leitura de volta

- **Root cause**: o Fix 6 cobriu `tentativas_coleta_meteorologica` e `cenarios_sinteticos_ativados`, mas não a terceira tabela prometida na Round 1.
- **Fix task**: um teste em `test_repositorio_meteorologia.py` que registre uma exceção via `RepositorioExecucaoPreventiva` e releia `causa`, `tentativas` e `impacto` de `excecoes_operacionais`.
- **Priority**: Minor

---

## Requirement Traceability Update

| Requirement | Round 1 | Round 2 |
| --- | --- | --- |
| RESIL-01 | ✅ Verified | ✅ Verified |
| RESIL-02 | ⚠️ ressalva | ✅ **Verified** (Fix 6) |
| RESIL-03 | ⚠️ desvio assumido | ⚠️ Desvio assumido (inalterado, documentado no README) |
| RESIL-04 | ✅ Verified | ✅ Verified |
| RESIL-05 | ✅ Verified | ✅ Verified |
| RESIL-06 | ❌ Needs Fix | ⚠️ **Verified com ressalva** — comportamento implementado e asserido; limiares sem discriminação (Fix 7) |
| RESIL-07 | ✅ Verified | ✅ Verified |
| RESIL-08 | ⚠️ ressalva | ✅ **Verified** (impacto por valor exato) |
| RESIL-09 | ❌ Needs Fix | ✅ **Verified** (Fix 3) |
| RESIL-10 | ✅ Verified | ✅ Verified |
| RESIL-11 | ✅ Verified | ✅ Verified |
| RESIL-12 | ✅ Verified | ✅ Verified (reforçado pelo Fix 6) |
| RESIL-13 | ⚠️ ressalva | ⚠️ ressalva (inalterada, dívida aceita) |
| RESIL-14 | ⚠️ ressalva | ⚠️ ressalva (inalterada, dívida aceita) |
| RESIL-15 | ❌ Needs Fix | ✅ **Verified** (Fix 1 + Fix 4) |
| RESIL-16 | ⚠️ ressalva | ✅ **Verified** (Fix 5) |
| RESIL-17 | ✅ Verified | ✅ Verified |
| RESIL-18 | ⚠️ ressalva | ⚠️ ressalva (inalterada, dívida aceita) |

---

## Estado das lições da Round 1

| Lição | Condição subjacente | Fechada? |
| --- | --- | --- |
| **L-014** testar a interseção onde duas condições de derivação valem ao mesmo tempo | 2 testes de interseção existem e matam ambas as mutações de ordem | ✅ Fechada (verificado pelo sensor) |
| **L-015** implementar e asserir cada substantivo do outcome do AC, incluindo valores derivados | "idade calculada" implementada, renderizada e asserida | ✅ Fechada |
| **L-016** quando o AC exige texto, ícone e cor, asserir as três dimensões | `data-icone` + classe + SVG asseridos | ✅ Fechada |
| **L-017** definir **na spec** qual estado vence quando mais de uma condição é verdadeira | A precedência foi registrada no **docstring da função** (`.tsx:36-46`), não em `spec.md` — a spec continua silenciosa | ⚠️ **Parcialmente fechada** — a decisão existe e está testada, mas não no artefato que a lição nomeia |
| **L-018** declarar explicitamente se um valor configurável precisa ser configurável em runtime | Não endereçado (dívida aceita: RESIL-03) | ⚠️ Aberta por decisão |

---

## Summary

**Overall**: ⚠️ **Quase pronto** — os 3 bloqueadores *Major* da Round 1 estão fechados e verificados de forma independente; resta **1 gap Minor** introduzido pela própria correção.

**Spec-anchored check**: 14/18 PASS pleno (era 9/18), 0 gaps de comportamento (eram 2), 4 parciais — todos já aceitos e documentados
**Sensor**: 3/6 mutantes mortos — os 2 mutantes de ordem da Round 1 (incluindo a re-injeção exata do sobrevivente) agora morrem; 3 mutantes de fronteira em `calcularIdade` sobrevivem
**Gate**: verde e **re-executado por este Verifier** — 267 backend + 148 frontend, 0 falhas, 0 skips, ruff/pyright/oxlint/build limpos

**O que melhorou nesta rodada**: precedência de `calcularEstadoFonte` documentada e comprovadamente discriminada; "idade calculada" (RESIL-06) implementada como função pura e exibida; aviso `role="note"` de dados desatualizados exclusivo do estado `Indisponível` (RESIL-09), com asserção de presença **e** de ausência; ícone e cor do badge asseridos (RESIL-15); ausência de ações coberta nos 6 estados (RESIL-16); `tentativas_coleta_meteorologica` e `cenarios_sinteticos_ativados` lidas de volta do DuckDB real com valores exatos de instante (RESIL-02); `impacto` conferido por igualdade com a constante de produção (RESIL-08). Nenhuma asserção foi enfraquecida e nenhum teste removido.

**Problema remanescente**: os três limiares de `calcularIdade` (1 min / 60 min / 24 h) são testados no meio da faixa, não na fronteira — `<` vira `<=` sem detecção (Fix 7, Minor). Gap residual opcional: `excecoes_operacionais` sem leitura de volta (Fix 8, Minor).

**Next steps**: aplicar o Fix 7 (3 asserções em `…test.tsx`, describe `calcularIdade`) — e, se conveniente na mesma rodada, o Fix 8. Re-verificar com a re-injeção de `diffMinutos < 60` → `<= 60`. Esta seria a Round 3 de 3 no limite do skill; nenhum dos itens exige mudança de produção.
