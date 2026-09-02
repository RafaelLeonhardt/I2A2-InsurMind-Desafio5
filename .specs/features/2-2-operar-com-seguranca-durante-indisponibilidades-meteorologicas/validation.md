# História 2.2: Operar com segurança durante indisponibilidades meteorológicas — Validation

**Date**: 2026-09-02
**Spec**: `.specs/features/2-2-operar-com-seguranca-durante-indisponibilidades-meteorologicas/spec.md`
**Diff range**: `e7a3410..2a6efa8` (7 commits, T1–T7; 27 arquivos, +3332/−335)
**Verifier**: independent sub-agent (author ≠ verifier), read-only sobre a árvore real

**Verdict**: ❌ **FAIL** — 1 mutante sobrevivente + 2 ACs com comportamento não implementado (RESIL-06 "idade calculada", RESIL-09 "snapshot marcado como desatualizado") + 3 gaps de precisão/asserção.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 Migração `0003` | ✅ Done | `testes/test_migracoes.py:118` cobre recreate-and-copy + `ON CONFLICT DO NOTHING` |
| T2 `RepositorioExecucaoPreventiva` | ✅ Done | 4 testes de integração (criar/transicionar/conflito/terminal) |
| T3 `ColetorComRetry` | ✅ Done | 4 testes unitários com dublês de tempo |
| T4 `AdaptadorCenarioSintetico` | ✅ Done | Desvio documentado (relógio corrente em vez do período histórico) justificado e correto |
| T5 Extensão do caso de uso | ⚠️ Partial | Falta o dado de "idade" do snapshot (RESIL-06) |
| T6 Extensão do roteador | ✅ Done | 7 testes de rota novos, happy + edge + error |
| T7 Frontend 6 estados | ⚠️ Partial | Texto coberto; ícone/cor e marcação de snapshot desatualizado não asseguradas |

---

## Spec-Anchored Acceptance Criteria

Prefixos: `B/` = `src/backend/`, `F/` = `src/frontend/`.

| Critério (RESIL) | Outcome definido na spec | `file:line` + asserção | Result |
| --- | --- | --- | --- |
| **RESIL-01** falha temporária/timeout/resposta inválida → timeout + no máx. 3 tentativas, espera configurável | 3 tentativas totais, backoff 1s/2s | `B/testes/test_coletor_com_retry.py:107` — `assert tentativas.registradas == [(…,1,TIMEOUT),(…,2,ERRO_TRANSPORTE),(…,3,SUCESSO)]`; `:112` — `assert espera.esperas == [1.0, 2.0]`; `:126` — `assert coletor.chamadas == 3`. Timeout de 5s herdado de `ClienteInmet` (2.1), documentado em `B/…/meteorologia/README.md:77` | ✅ PASS |
| **RESIL-02** cada tentativa registra número, início, término, código do resultado e correlação | número + código + `sincronizacao_id`; início/término sem valor preciso na spec | `B/testes/test_coletor_com_retry.py:91,107,130` — tuplas `(SINCRONIZACAO_ID, n, codigo)`; `:60-61` — `assert iniciado_em is not None` / `finalizado_em is not None` (só presença); persistência real: `B/testes/test_meteorologia_api.py:271-272` — `tentativas[0]["numero_tentativa"] == 1`, `codigo_resultado == "sucesso"` | ⚠️ Parcial — início/término nunca asseridos por valor nem lidos de volta do banco |
| **RESIL-03** intervalo, timeout, tentativas e backoff exatos, configuráveis e documentados | Spec (Assumptions): "configuráveis por variável de ambiente"; Design (l.14) confirma só os valores 5s/3/1s-2s-4s | Valores exatos: `B/…/aplicacao/coleta_meteorologica.py:31,34`; documentados em `B/…/meteorologia/README.md:73-92`. **Configurabilidade externa não existe** — constantes de módulo, injetáveis só por construtor em teste (README:89-92 assume o desvio) | ⚠️ Spec-precision gap / desvio assumido |
| **RESIL-04** documentação justifica padrões e descreve comportamento observável por tipo de falha | 4 tipos de falha descritos + justificativa dos 3 parâmetros | `B/…/adaptadores/meteorologia/README.md:75-79` (tabela justificada) e `:83-87` (timeout / erro_transporte / status_erro / 3 esgotadas / 200 em qualquer tentativa) | ✅ PASS |
| **RESIL-05** enquanto houver tentativas → UI mostra tentativa atual e limite de três | texto "tentativa atual / 3" | `F/…/SuperficieFonteMeteorologica.test.tsx:308` — `expect(screen.getByText('Tentativa 2 de 3'))`; backend: `B/testes/test_meteorologia_api.py:269` — `limite_tentativas == 3` | ✅ PASS |
| **RESIL-06** snapshot válido antigo continua consultável com **origem, horário e idade calculada** | os 3 atributos acompanhando o snapshot | Permanência: `B/testes/test_coleta_meteorologica.py:420` — `assert eventos.salvos == [snapshot_anterior]`. Origem/horário no payload (`proveniencia`, `instante_observado`, 2.1). **"Idade calculada" não existe** — grep por `idade` em `adaptadores/http`, `api/`, `funcionalidades/` → 0 ocorrências | ❌ GAP (comportamento ausente) |
| **RESIL-07** snapshot antigo consultado durante falha → nenhuma nova avaliação/alerta/mensagem | nenhum evento novo derivado | `B/testes/test_coleta_meteorologica.py:419-420` — estado `FALHA` e a lista de eventos permanece exatamente `[snapshot_anterior]` (nenhum evento novo); nenhum caminho de avaliação de risco existe/é chamado no caso de uso | ✅ PASS |
| **RESIL-08** 3 tentativas esgotadas → execução em `falhou_coleta` + `Exceção` com causa, tentativas e impacto | estado `FALHOU_COLETA`, exceção com 3 campos | `B/testes/test_coleta_meteorologica.py:351` — `assert novo_estado == EstadoExecucao.FALHOU_COLETA`; `:352` — `estado_de(execucao_id) == FALHOU_COLETA`; `:353-358` — `len(excecoes.registradas)==1`, `excecao_execucao_id == execucao_id`, `"TimeoutException" in causa`, `tentativas == 3`, `impacto != ""`; monotonicidade do terminal: `B/testes/test_repositorio_execucao_preventiva.py:64` — `pytest.raises(TransicaoInvalida)` | ⚠️ Parcial — `impacto != ""` é asserção fraca (não confere o texto); linha de `excecoes_operacionais` nunca lida de volta do DuckDB |
| **RESIL-09** ao alcançar `falhou_coleta` → UI mostra `Indisponível` com o snapshot antigo **claramente identificado como desatualizado** | estado `Indisponível` + marcação de obsolescência | `F/…/SuperficieFonteMeteorologica.test.tsx:236` — `findByText('Indisponível')`; `:369` — `calcularEstadoFonte(historicoComFalha(), []) === 'indisponivel'`. **Marcação "desatualizado" não existe** na tabela de eventos (grep `desatualiz` → 0); `design.md:171` exigia-a explicitamente | ❌ GAP (comportamento ausente) |
| **RESIL-10** nova tentativa explícita → nova execução correlacionada em `coletando`, id/chave próprios, sem reabrir a terminal | nova sincronização ≠ origem; origem intocada | `B/testes/test_coleta_meteorologica.py:441` — `aceita.sincronizacao.id != origem.id`; `:444` — `sincronizacoes.estado_de(origem.id).estado == FALHA` (origem não reaberta); `:445` — `execucoes.transicoes == execucoes_apos_origem` (execução terminal anterior não transicionada de novo); rota: `B/testes/test_meteorologia_api.py:402-405` — `202` + `corpo["id"] != sincronizacao_id` + `estado == "concluido"` | ✅ PASS |
| **RESIL-11** repetir a mesma `Idempotency-Key` da nova tentativa → não duplica coleta nem efeitos | 1 única coleta; resposta idêntica | `B/testes/test_coleta_meteorologica.py:465-467` — `chamadas_criar == contagem_antes + 1`, ids e `aceito_em` iguais; rota: `B/testes/test_meteorologia_api.py:425-427` — `202/202` e `primeira.json() == segunda.json()`; ausência de chave: `:384-386` — `422` + `problem+json` + `codigo == "idempotency_key_ausente"` | ✅ PASS |
| **RESIL-12** ativação de cenário sintético → coleta separada com proveniência `sintetico`, sem combinar com `real_inmet` | `proveniencia == sintetico`, evento real preservado à parte | `B/testes/test_coleta_meteorologica.py:494-499` — 2 eventos distintos, `novo_evento.proveniencia == SINTETICO`, `eventos.salvos[0].proveniencia == REAL_INMET`, `cenarios_ativados.registrados == [(sincronizacao.id, IDENTIFICADOR_CENARIO_GRANIZO)]`; rota: `B/testes/test_meteorologia_api.py:473-474` — `tipo == "granizo"`, `proveniencia == "sintetico"`; adaptador: `B/testes/test_adaptador_cenario_sintetico.py:46-47` | ✅ PASS |
| **RESIL-13** com cenário ativo → origem sintética visível por texto e indicador acessível | rótulo textual da origem | `F/…/SuperficieFonteMeteorologica.tsx:88` (`sintetico → 'Sintético'`) renderizado na coluna Origem; badge de estado: `F/…/SuperficieFonteMeteorologica.test.tsx:247` — `findByText('Sintética')`; `:376` — `calcularEstadoFonte(...) === 'sintetica'` | ⚠️ Parcial — o texto "Sintético" na linha do evento não tem asserção própria nesta feature; nenhuma asserção do "indicador acessível" (ícone `FlaskIcon` é `aria-hidden`) nem da explicação de contingência exigida pela spec |
| **RESIL-14** recuperação real → registra recuperação, retoma agendamento automático, sem duplicar eventos com a mesma chave determinística | 1 única linha em `eventos_meteorologicos` | `B/testes/test_coleta_meteorologica.py:585-587` — duas coletas reais concluídas e `len(RepositorioEventosMeteorologicos(caminho).listar()) == 1`, montado sobre **repositórios DuckDB reais** (`_servico_com_repositorios_reais`, `:526-563`) — confirmado: `RepositorioIdempotencia/Areas/Eventos/Sincronizacoes/Tentativas/ExecucaoPreventiva/Excecoes/CenariosSinteticosAtivados`, nenhum dublê; constraint: `B/testes/test_migracoes.py:151-160`. "Recuperada" na UI: `F/…test.tsx:286` | ⚠️ Parcial — "retomar o agendamento automático" após uma falha não tem teste (garantido só estruturalmente: `executar_coleta` nunca propaga exceção, `coleta_meteorologica.py:335-339`) |
| **RESIL-15** UI distingue os 6 estados por **texto, ícone e cor** | 6 rótulos + ícone + cor por estado | Texto: `F/…test.tsx:225,236,247,269,286,307` (`Operacional`/`Indisponível`/`Sintética`/`Degradada`/`Recuperada`/`Em tentativa`) e função pura `:355,365,369,376,388,404,408`. Ícone/cor implementados (`SuperficieFonteMeteorologica.tsx:72-79`, classe `estado-fonte-badge--${estado}` + CSS) mas **sem nenhuma asserção** — grep por `estado-fonte-badge`/`data-icone` no teste → 0 | ⚠️ Parcial — 2 das 3 dimensões exigidas sem evidência |
| **RESIL-16** cada estado expõe somente ações seguras e aplicáveis | ações por estado, nunca inseguras | `F/…test.tsx:226-227` (operacional: nenhuma ação), `:237-238` (indisponível: nova tentativa + cenário sintético), `:248-249` (sintética: só nova tentativa, `queryByRole('Ativar cenário sintético')` ausente), `:270` (degradada: sem nova tentativa); payload das ações: `:327` — `toHaveBeenCalledWith('s2')`, `:348` — `toHaveBeenCalledWith('granizo-demonstrativo', 'a1')` | ⚠️ Parcial — ausência de ações não asserida para `em_tentativa` nem `recuperada` (2 dos 6 estados) |
| **RESIL-17** suíte cobre recuperação antes do limite, esgotamento, snapshot, nova tentativa, ativação sintética e recuperação real sem duplicação | 6 cenários presentes | recuperação antes do limite `test_coletor_com_retry.py:97`; esgotamento `:115` e `test_coleta_meteorologica.py:333`; snapshot `:404`; nova tentativa `:423`; ativação sintética `:477`; recuperação sem duplicação `:564` | ✅ PASS |
| **RESIL-18** valores-limite de timeout, tentativas e backoff com dublês de tempo, sem tempo real nem INMET real | dublês de tempo; zero rede/sleep | Dublês: `test_coletor_com_retry.py:68-75` (`EsperaEspia`, sem `asyncio.sleep`), `test_coleta_meteorologica.py:230-232` (`_sem_espera_real`), `test_adaptador_cenario_sintetico.py:27` (relógio fixo); rede bloqueada por fixture `autouse` em `test_meteorologia_api.py:31`. **Exceção**: 3 testes de rota (`test_meteorologia_api.py:375,389,408`) esgotam o retry pelo caminho de produção e aguardam o backoff real de 1s+2s (~3,3s cada) — desvio registrado na Nota de implementação de T6 | ⚠️ Parcial — "sem aguardar tempo real" violado nos testes de rota (documentado e aceito) |

**Status**: ❌ 2 GAPs de comportamento (RESIL-06, RESIL-09) + 7 parciais/precision gaps; 9 ACs em PASS pleno.

---

## Discrimination Sensor

Worktrees isolados (`git worktree add <scratch> 2a6efa8 --detach`), um ciclo por mutação, removidos imediatamente após cada corrida. Baseline `git status --porcelain` = vazio antes e depois de cada mutação.

| # | File:line | Mutação | Testes executados | Killed? |
| --- | --- | --- | --- | --- |
| 1 | `aplicacao/coleta_meteorologica.py:31` | `MAXIMO_TENTATIVAS_COLETA = 3` → `2` | `pytest testes/test_coletor_com_retry.py` | ✅ Killed (3 falhas: sequência de tentativas, `espera.esperas`, `ultimo_erro`) |
| 2 | `aplicacao/coleta_meteorologica.py:454` | Removido o efeito colateral obrigatório `excecoes.registrar(...)` em `_registrar_falha_terminal` (RESIL-08) | `pytest testes/test_coleta_meteorologica.py` | ✅ Killed (`test_executar_coleta_com_erro_de_transporte_persistente_esgota_retentativas`: `assert len(excecoes.registradas) == 1` → `0 == 1`) |
| 3 | `SuperficieFonteMeteorologica.tsx:55-58` | Trocada a ordem de prioridade `recuperada` ↔ `degradada` em `calcularEstadoFonte` | `vitest --run SuperficieFonteMeteorologica.test.tsx` | ❌ **Survived** — 22/22 passaram com a mutação aplicada |

**Sensor depth**: lightweight (3 mutações)
**Result**: 2/3 killed — ❌ FAIL

**Análise do sobrevivente**: nenhuma fixture do arquivo satisfaz as duas condições ao mesmo tempo. O caso `recuperada` usa `ultima.tentativas.length === 1`; o caso `degradada` usa `resultadosAnteriores[1] === undefined`. O cenário mais realista da própria história — a nova tentativa que recupera após um `falhou_coleta` e precisou de 2 tentativas — cai exatamente na interseção não coberta, e a spec não define a precedência entre `Degradada` e `Recuperada`. Qualquer par de ramos adjacentes de `calcularEstadoFonte` pode ser trocado sem que a suíte perceba.

---

## Payload / Conjunction Rule (rotas HTTP e repositórios)

| Superfície | Verificação | Resultado |
| --- | --- | --- |
| `POST /{id}/nova-tentativa` | Não só o status: `test_meteorologia_api.py:404-405` confere `corpo["id"] != sincronizacao_id` e `estado == "concluido"`; `:440` confere `codigo == "sincronizacao_desconhecida"`; `:427` compara os corpos completos das duas respostas idempotentes | ✅ |
| `POST /cenarios-sinteticos/{id}/ativar` | `:470,473-474` conferem `estado`, `tipo` e `proveniencia` do evento realmente persistido (via `GET /eventos`), não apenas o `202`; `:499` confere que não houve segundo evento | ✅ |
| `GET /sincronizacoes` | `:269-272` conferem `limite_tentativas == 3` e os campos da tentativa persistida, não a mera presença da chave | ✅ |
| Repositórios (execução preventiva) | `test_repositorio_execucao_preventiva.py:37-38,50-51,63-64,76-77` releem o snapshot após cada operação e conferem estado **e** versão, inclusive nos caminhos de erro (linha não mutada) | ✅ |
| Repositório de exceções operacionais | `RepositorioExcecoesOperacionais.registrar` é executado contra DuckDB real apenas de forma implícita (`test_meteorologia_api.py:363-372`), sem nenhum `SELECT` de volta na tabela `excecoes_operacionais` | ⚠️ Gap |
| Repositório de tentativas | `RepositorioTentativasColeta` verificado só via `GET /sincronizacoes`; a linha da Test Coverage Matrix que prometia `testes/test_repositorio_meteorologia.py` (estendido) não foi cumprida — o arquivo não aparece no diff | ⚠️ Gap |

---

## Edge Cases

- [x] **Segunda tentativa no limite exato do timeout → falha de timeout, não sucesso tardio**: coberto por proxy — `httpx.TimeoutException` é classificado como `CodigoResultadoTentativa.TIMEOUT` (`test_coletor_com_retry.py:108,131`) e nunca como sucesso; o limite exato é imposto pelo `timeout=5s` do `ClienteInmet` (2.1), fora desta camada. ⚠️ o valor-limite literal não é exercitado.
- [x] **Ativar cenário sintético durante coleta real em `coletando` → operação correlacionada distinta, sem interromper a real**: estruturalmente garantido — `ativar_cenario_sintetico` cria a própria `Sincronizacao` e nunca toca outra (`coleta_meteorologica.py:417-430`); nenhum teste exercita a concorrência (coleta é síncrona ponta a ponta, limitação conhecida de 2.1).
- [ ] **Reinício do backend com execução em `coletando` → retoma do último marco durável sem perder a contagem**: **não coberto** por teste nem por código — nenhuma rotina de recuperação de execuções órfãs foi adicionada. Consistente com a limitação conhecida de 2.1 (coleta síncrona; `coletando` é inobservável), mas o edge case da spec fica sem tratamento.

---

## Code Quality

| Princípio | Status |
| --- | --- |
| Código mínimo | ✅ |
| Mudanças cirúrgicas | ✅ (`salvar` → `ON CONFLICT DO NOTHING` em T1 é efeito direto da constraint, justificado na Nota) |
| Sem scope creep | ✅ |
| Segue os padrões existentes | ✅ (portas/adaptadores, dublês, `problem+json`, idempotência AD-002) |
| Spec-anchored outcome check | ⚠️ 2 gaps + 7 parciais (tabela acima) |
| Coverage Expectation por camada | ⚠️ rotas cobrem happy+edge+error; a linha de matriz de `RepositorioTentativasColeta`/`RepositorioExcecoesOperacionais` não foi cumprida |
| Todo teste mapeia a um AC / edge case / Done-when | ✅ nenhum teste órfão encontrado |
| Guidelines documentadas seguidas | ✅ `AGENTS.md`, `README.md`; sem threshold dedicado — defaults fortes aplicados |

---

## Gate Check

- **Gate command (Build)**: Backend `uv run --directory src/backend pytest && ruff check . && pyright` — Frontend `npm test --prefix src/frontend -- --run && npm run lint && npm run build`
- **Result**: verde, confirmado pelo orquestrador ao longo de toda a implementação e imediatamente antes deste despacho (não re-executado aqui para aprovação: este relatório é a verificação profunda que o gate não faz).
- **Smoke manual (já executado pelo orquestrador)**: servidores de dev reais, ciclo `ativar_cenario_sintetico` → `GET /sincronizacoes` → `GET /eventos` conferido campo a campo; compilação do módulo pelo Vite; banco de desenvolvimento restaurado.
- **Delta de testes**: +~40 testes (5 arquivos estendidos, 3 novos). Nenhum teste removido; nenhuma asserção enfraquecida detectada na comparação do diff.
- **Skipped**: nenhum.
- **Execuções deste Verifier**: apenas em worktrees descartáveis, sob mutação (ver Sensor).

---

## Fix Plans

### Fix 1: Ordem de prioridade de `calcularEstadoFonte` não é discriminada (mutante sobrevivente)

- **Root cause**: nenhuma fixture satisfaz duas condições de estado simultaneamente; a spec não define a precedência entre `Degradada` e `Recuperada` (nem entre `Indisponível` e `Sintética`).
- **Fix task**: (a) decidir e registrar na spec a precedência quando mais de uma condição vale; (b) adicionar testes de interseção a `SuperficieFonteMeteorologica.test.tsx` — pelo menos "última concluída com 2 tentativas logo após uma falha" (esperado `Recuperada`) e "última em `falha` com evento sintético mais recente" (esperado `Indisponível`).
- **Priority**: Major

### Fix 2: RESIL-06 — "idade calculada" do snapshot não existe

- **Root cause**: nem o payload de `GET /eventos`/`GET /sincronizacoes` nem a superfície derivam a idade do último snapshot válido; nenhuma task cobriu esse termo do AC.
- **Fix task**: expor a idade calculada (ou derivá-la no cliente a partir de `instante_observado`) junto de origem e horário, com teste que confira o valor.
- **Priority**: Major

### Fix 3: RESIL-09 — snapshot antigo não é marcado como desatualizado

- **Root cause**: a tabela de eventos renderiza igual em qualquer estado da fonte; `design.md:171` previa a marcação, T7 não a implementou.
- **Fix task**: no estado `Indisponível`, marcar os eventos exibidos como desatualizados (texto + indicador acessível) e asserir a marcação no teste do estado `Indisponível`.
- **Priority**: Major

### Fix 4: RESIL-15 — ícone e cor por estado sem asserção

- **Root cause**: os testes asseguram apenas o rótulo textual dos 6 estados.
- **Fix task**: asserir, para cada estado, a classe `estado-fonte-badge--${estado}` (cor) e a presença do ícone correspondente.
- **Priority**: Minor

### Fix 5: RESIL-16 — ausência de ações não asserida em `em_tentativa` e `recuperada`

- **Fix task**: adicionar `queryByRole(...).not.toBeInTheDocument()` para os dois botões nesses dois estados.
- **Priority**: Minor

### Fix 6: Linha da Test Coverage Matrix não cumprida (repos de tentativas/exceções)

- **Fix task**: estender `testes/test_repositorio_meteorologia.py` (ou criar cobertura equivalente) lendo de volta `tentativas_coleta_meteorologica` (incluindo `iniciado_em`/`finalizado_em`) e `excecoes_operacionais` (causa/tentativas/impacto) do DuckDB real.
- **Priority**: Minor

---

## Requirement Traceability Update

| Requirement | Previous | New |
| --- | --- | --- |
| RESIL-01 | Implementing | ✅ Verified |
| RESIL-02 | Implementing | ⚠️ Verified com ressalva (início/término só por presença) |
| RESIL-03 | Implementing | ⚠️ Desvio assumido (constantes, não configuráveis externamente) |
| RESIL-04 | Implementing | ✅ Verified |
| RESIL-05 | Implementing | ✅ Verified |
| RESIL-06 | Implementing | ❌ Needs Fix (idade calculada ausente) |
| RESIL-07 | Implementing | ✅ Verified |
| RESIL-08 | Implementing | ⚠️ Verified com ressalva (impacto/linha real não conferidos) |
| RESIL-09 | Implementing | ❌ Needs Fix (marcação de desatualizado ausente) |
| RESIL-10 | Implementing | ✅ Verified |
| RESIL-11 | Implementing | ✅ Verified |
| RESIL-12 | Implementing | ✅ Verified |
| RESIL-13 | Implementing | ⚠️ Verified com ressalva (indicador acessível/explicação sem asserção) |
| RESIL-14 | Implementing | ⚠️ Verified com ressalva (retomada do agendamento sem teste) |
| RESIL-15 | Implementing | ❌ Needs Fix (ícone e cor sem evidência; mutante sobrevivente) |
| RESIL-16 | Implementing | ⚠️ Verified com ressalva (2 de 6 estados sem asserção de ausência) |
| RESIL-17 | Implementing | ✅ Verified |
| RESIL-18 | Implementing | ⚠️ Verified com ressalva (3 testes de rota aguardam backoff real) |

---

## Summary

**Overall**: ❌ Not Ready (correções pontuais; a espinha dorsal de segurança está sólida)

**Spec-anchored check**: 9/18 PASS pleno, 7 parciais/spec-precision, 2 GAPs de comportamento
**Sensor**: 2/3 mutantes mortos (1 sobrevivente)
**Gate**: verde (backend pytest/ruff/pyright; frontend vitest/lint/build) + smoke manual, ambos confirmados pelo orquestrador

**O que funciona**: retry de 3 tentativas com backoff 1s/2s exato e cada tentativa registrada com número/código/correlação; falha terminal em `falhou_coleta` com `Exceção` (causa, tentativas, impacto) e monotonicidade do estado terminal garantida pelo repositório; snapshot anterior preservado sem gerar evento novo; nova tentativa correlacionada que nunca reabre a execução terminal, idempotente por chave em todas as três mutações; cenário sintético isolado de `real_inmet`; deduplicação de recuperação real provada **com repositórios DuckDB reais** (afirmação do autor confirmada, não são dublês) sobre a `UNIQUE` de T1; seis estados derivados de dados persistidos, sem estado especulativo.

**Problemas**: (1) mutante sobrevivente na ordem de prioridade de `calcularEstadoFonte`; (2) "idade calculada" do RESIL-06 nunca implementada; (3) snapshot antigo não marcado como desatualizado (RESIL-09); (4) ícone/cor dos estados sem asserção (RESIL-15); (5) ausência de ações não asserida em 2 dos 6 estados (RESIL-16); (6) linha da matriz de cobertura de `RepositorioTentativasColeta`/`RepositorioExcecoesOperacionais` não cumprida.

**Next steps**: rotear Fix 1–3 (Major) como fix tasks antes de marcar a feature como done; Fix 4–6 (Minor) podem entrar na mesma rodada, pois são só asserções.
