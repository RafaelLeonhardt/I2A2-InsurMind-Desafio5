# História 2.1: Coletar e normalizar dados do INMET — Validation

**Date**: 2026-09-01
**Spec**: `.specs/features/2-1-coletar-e-normalizar-dados-do-inmet/spec.md`
**Diff range**: `43e3e3b..552b378` (15 commits — T1–T14 + o commit de correção `552b378`)
**Verifier**: sub-agente independente (author ≠ verifier), read-only sobre a árvore real

**Verdict**: ✅ **PASS** — as 4 lacunas bloqueantes da Rodada 1 estão fechadas, com evidência empírica (mutantes mortos), e nenhum problema novo foi introduzido.

---

## Rodada 2 — re-verificação após Fix 1–4 (`552b378`)

Esta é a **segunda rodada** de verificação. A Rodada 1 (`43e3e3b..44fd7af`) devolveu ❌ FAIL com 1 mutante sobrevivente (M2) e 4 lacunas de cobertura ancorada em AC. O orquestrador implementou Fix 1–4 e os entregou como `552b378 fix(meteorologia): fechar lacunas do verificador da historia 2.1`. Este Verifier re-derivou tudo do zero: releu spec, diff e testes, reexecutou os dois gates completos, re-injetou a **mesma** mutação M2 e uma mutação **nova** na área da correção de menor confiança, e mediu a flakiness do teste de polling.

| Fix | Lacuna da Rodada 1 | Status Rodada 2 | Evidência |
| --- | --- | --- | --- |
| Fix 1 | Mutante M2 sobrevivente: `INTERVALO_SEGUNDOS_COLETA` 900→60 indetectável | ✅ **Fechada** | Sensor M2 re-injetado ⇒ **2 testes falham** (ver Sensor) |
| Fix 2 | INMET-04 nunca exercitado com o agendador ativo (`TestClient` sem `lifespan`) | ✅ **Fechada** | `testes/test_meteorologia_api.py:148-180`, `with TestClient(...)`; 5/5 execuções verdes |
| Fix 3 | Cláusula p95 ≤ 1 s de INMET-15 sem asserção | ✅ **Fechada** | `testes/test_meteorologia_api.py:282-307`, `perf_counter` + `assert p95 < 1.0` |
| Fix 4 | INMET-07 campos temporais + INMET-06 estado não-`concluido` (UI imprimia o enum cru) | ✅ **Fechada** | `testes/test_normalizador_inmet.py:48-50`; `SuperficieFonteMeteorologica.tsx:27-32` + `.test.tsx:147,150,153-164`; sensor M3 mata a mutação do rótulo |
| Fix 5 | Prova ao vivo do INMET (T4) não executada — sem egresso de rede | ⏭️ Dívida aceita | Já declarada em `adaptadores/meteorologia/README.md:17-34`; **não re-flagada** (Minor, não bloqueante, decidido na Rodada 1) |

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 `EventoMeteorologico` | ✅ Done | — |
| T2 Migração `0002_meteorologia.sql` | ✅ Done | — |
| T3 Portas de aplicação | ✅ Done | 3 `# SPEC_DEVIATION` (`portas_meteorologia.py:86,95,112`) — justificados e usados; ver nota L-013 abaixo |
| T4 Prova limitada + amostras congeladas | ⚠️ Partial (dívida aceita) | Prova ao vivo não executada; fixtures são reconstrução de melhor esforço, declarada abertamente |
| T5 `NormalizadorInmet` | ✅ Done | Fix 4 acrescentou asserção de valor nos campos temporais |
| T6 `ClienteInmet` + dublê | ✅ Done | — |
| T7 Repositórios DuckDB | ✅ Done | — |
| T8 `ServicoColetaMeteorologica` | ✅ Done | — |
| T9 Roteador HTTP | ✅ Done | — |
| T10 `AgendadorMeteorologico` | ✅ **Done** (era ⚠️ Partial) | Fix 1 fixa o intervalo real de produção: `test_agendador_meteorologico.py:237` + `test_meteorologia_api.py:265` |
| T11 Sincronizar OpenAPI | ✅ Done | — |
| T12 Cliente HTTP do frontend | ✅ Done | — |
| T13 Superfície "Fonte meteorológica" | ✅ **Done** (corrigido desvio real) | A UI passou a exibir os rótulos do spec via `ROTULOS_ESTADO_SINCRONIZACAO` |
| T14 Restauração ao estado inicial completo | ✅ Done | — |

---

## Spec-Anchored Acceptance Criteria

### P1: Coleta automática e sob demanda com contrato registrado

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| INMET-01 — registrar campos, unidades, normalizações e mapeamento | Documento de contrato campo-a-campo | `src/backend/central_preventiva/adaptadores/meteorologia/README.md:36-47` — tabela `Campo INMET → EventoMeteorologico` | ⚠️ PASS com desvio documentado (Fix 5, dívida aceita) |
| INMET-02 — amostras congeladas, parsing determinístico, sem rede | Parsing sobre amostras em disco, zero rede | `testes/test_normalizador_inmet.py:28-31` (`carregar_fixture`); bloqueio de rede em `testes/test_meteorologia_api.py:22-31` | ✅ PASS |
| INMET-03 — coleta na inicialização e no **intervalo configurado** | 1 coleta no boot sem esperar; intervalo de produção = 900 s (15 min) | `testes/test_agendador_meteorologico.py:167` — `assert len(coletor.chamadas) == 1`; **`:237` — `assert relogio.chamadas == [900]` com `AgendadorMeteorologico` instanciado SEM `intervalo_segundos`** (helper propaga `None` ⇒ default de produção, `agendador_meteorologico.py:44`); `test_meteorologia_api.py:265` — `assert proxima_consulta == iniciado_em + timedelta(seconds=900)` | ✅ **PASS** (era ⚠️ parcial) — o `900` esperado é **hardcoded**, não importado de `INTERVALO_SEGUNDOS_COLETA`, então a asserção não acompanha a constante |
| INMET-04 — atualização manual aceita **independentemente do agendamento em curso** | `202` para o POST manual com o agendador rodando; ambas as tentativas persistidas | `testes/test_meteorologia_api.py:161` — `with TestClient(criar_aplicacao(...)) as cliente:` (lifespan real ⇒ `AgendadorMeteorologico` ativo); `:167` — `assert resposta_manual.status_code == 202`; `:178` — `assert {"automatica", "manual"} <= origens`; `:180` — `assert len(ids_requisicao) == len(resultados)` | ✅ **PASS** (era ❌ GAP) |
| INMET-05 — persistir o trabalho antes de responder `202 Accepted` | Linha persistida antes da resposta; HTTP `202` | `testes/test_coleta_meteorologica.py:177`; `testes/test_meteorologia_api.py:117-120`; `testes/test_repositorio_meteorologia.py:103-106` | ✅ PASS |
| INMET-06 — interface exibe `Coletando`/`Normalizando`/`Concluído`/`Falha` refletindo o estado persistido | Rótulos exatos do spec, mapeados do estado real | `SuperficieFonteMeteorologica.tsx:27-32` — `ROTULOS_ESTADO_SINCRONIZACAO` (`coletando→Coletando`, `normalizando→Normalizando`, `concluido→Concluído`, `falha→Falha`), aplicado em `:157` e `:171`; `SuperficieFonteMeteorologica.test.tsx:147,150` — `getByText(/Manual — Concluído — .../)`; `:160,162` — `getByText(/Automática — Falha — .../)` e `/… — motivo: campo_ausente/` | ✅ **PASS** (era ⚠️ spec-precision) — o desvio real (UI imprimia o enum cru) foi corrigido, não apenas coberto por teste |

### P1: Normalização com proveniência e rejeição de dados inválidos

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| INMET-07 — resposta válida vira `EventoMeteorologico` com tipo, área, período, intensidade, medidas, instante observado | Todos os campos, inclusive os temporais | `testes/test_normalizador_inmet.py:43-46` — `tipo == CHUVA_INTENSA`, `area == "9990001"`, `intensidade == 55.4`; **`:48` — `instante_observado == datetime(2026,8,30,18,0)`; `:49` — `periodo_inicio == datetime(2026,8,30,17,0)`; `:50` — `periodo_fim == datetime(2026,8,30,18,0)`** (derivação `DT_MEDICAO`+`HR_MEDICAO` e janela de 1 h agora ancoradas por valor) | ✅ **PASS** (era ⚠️ parcial) |
| INMET-08 — proveniência `real_inmet` | `proveniencia == real_inmet` | `testes/test_normalizador_inmet.py:44`; `testes/test_meteorologia_api.py:225` | ✅ PASS |
| INMET-09 — campo ausente / medida inválida / geografia não reconhecida ⇒ nenhum evento | `evento is None` nos três casos | `testes/test_normalizador_inmet.py:71,81,91,102,111` — `assert resultado.evento is None` | ✅ PASS |
| INMET-10 — rejeição com código e motivo inspecionáveis | Motivo tipado consultável | `testes/test_normalizador_inmet.py:72,82,92,103`; `testes/test_coleta_meteorologica.py:209`; `testes/test_repositorio_meteorologia.py:153` | ✅ PASS |

### P2: Observabilidade, histórico e idempotência da sincronização

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| INMET-11 — persistir início, término, resultado, registros válidos e correlação | Os cinco campos | `testes/test_repositorio_meteorologia.py:103-106,129-131,153` | ✅ PASS |
| INMET-12 — não logar cabeçalhos, credenciais nem corpo externo | Nenhum log com esses conteúdos | `testes/test_coleta_meteorologica.py:265-266` — `assert "CHUVA" not in saida.out / saida.err` | ⚠️ PASS com evidência fraca (carry-over da Rodada 1, Minor, não bloqueante) — asserção sobre um único token e só no caso de uso; sem teste equivalente para `ClienteInmet` |
| INMET-13 — UI exibe tipo, local, período, intensidade, origem e horário | Os seis campos | `SuperficieFonteMeteorologica.test.tsx:102-115` | ✅ PASS |
| INMET-14 — alternativa em lista operável por teclado e leitor de tela | Seleção via teclado, estado exposto à AT | `SuperficieFonteMeteorologica.test.tsx:117-138` — `toHaveFocus()`, `keyboard('{Enter}')`, `aria-pressed`, `aria-selected` | ✅ PASS |
| INMET-15 — 4 marcos, só dados persistidos, **≤ 1 s no p95** | Marcos corretos + orçamento de latência p95 | `testes/test_meteorologia_api.py:252-266` — conjunto exato de chaves, `estado == "concluido"` nos dois marcos, `proxima_consulta == iniciado_em + 900 s`, `len(resultados_anteriores) == 1`; **`:282-307` — `p95_segundos()` com `time.perf_counter()` sobre 20 repetições, `assert p95_segundos(CAMINHO_EVENTOS) < 1.0` e `assert p95_segundos(CAMINHO_SINCRONIZACOES) < 1.0`**; `:274-279` — marcos nulos sem coleta | ✅ **PASS** (era ❌ GAP parcial) |
| INMET-16 — mesma `Idempotency-Key` não inicia outra coleta | Zero segunda coleta; corpo idêntico | `testes/test_meteorologia_api.py:144-145` — `primeira.json() == segunda.json()`, `len(chamadas) == 1`; `testes/test_coleta_meteorologica.py:233-236` | ✅ PASS (evidência forte) |
| INMET-17 — restauração repõe o estado inicial completo (AD-014) | Tabelas fora da lista vazias; exceções intactas | `testes/test_semeador.py:252,274-275,279,147` | ✅ PASS |

**Status**: ✅ 15/17 ACs plenamente ancorados no valor definido pelo spec; 2 residuais **não bloqueantes** (INMET-01 dívida da prova ao vivo — Fix 5 aceito; INMET-12 evidência fraca — carry-over da Rodada 1, mesma classificação de então).

---

## Discrimination Sensor

Depth: lightweight (2 mutações), uma worktree descartável por mutação, árvore real nunca tocada.
Baseline `git status --porcelain` antes do sensor: **vazio**. Após cada mutação e após ambas: **vazio**; `git worktree list` mostra só a árvore principal em `552b378`. `git stash` não foi usado.

| # | File:line | Mutation | Suíte executada | Killed? |
| --- | --- | --- | --- | --- |
| M2 (re-injetada) | `aplicacao/portas_meteorologia.py:64` | `INTERVALO_SEGUNDOS_COLETA = 900` → `60` (15 min → 1 min em produção) — **exatamente a mutação que sobreviveu na Rodada 1** | `uv run --directory src/backend pytest` (suíte completa, 238 testes) | ✅ **Killed** — 2 falhas: `test_agendador_meteorologico.py::test_intervalo_padrao_de_producao_e_900_segundos` e `test_meteorologia_api.py::test_get_sincronizacoes_retorna_200_com_os_campos_esperados_apos_coleta` (`assert proxima_consulta == iniciado_em + timedelta(seconds=900)`) |
| M3 (nova) | `SuperficieFonteMeteorologica.tsx:31` | `ROTULOS_ESTADO_SINCRONIZACAO.falha: 'Falha'` → `'Erro'` (rótulo de estado exigido pelo spec, área da Fix 4 — a de menor confiança por ser um mapa de strings) | `npm test --prefix src/frontend -- --run` (113 testes) | ✅ **Killed** — `SuperficieFonteMeteorologica.test.tsx:160` falhou (`Unable to find an element with the text: /Automática — Falha — .../`) |

**Result**: **2/2 killed** — ✅ PASS. A Rodada 1 fechou em 1/2; o mutante que sobreviveu agora é morto por dois testes independentes (unitário do agendador + rota HTTP), em camadas diferentes.

---

## Flakiness Check (Fix 2 — maior risco de instabilidade)

`test_post_manual_e_aceito_independentemente_do_agendamento_automatico_em_curso` usa um laço de polling (40 iterações × `time.sleep(0.05)` = **2,0 s de orçamento**) contra uma task de segundo plano real dirigida pelo `lifespan`.

| Execução | 1 | 2 | 3 | 4 | 5 |
| --- | --- | --- | --- | --- | --- |
| Resultado | ✅ | ✅ | ✅ | ✅ | ✅ |

**5/5 verdes.** Duração medida do teste: **0,17 s** contra 2,0 s de orçamento — folga de ~12×. O laço tem `break` na condição de sucesso, então o custo real é uma iteração ou duas.

Risco de flakiness da Fix 3 (assert de latência) também medido: 40 requisições em **0,39 s** totais (~10 ms por requisição) contra um limiar de 1,0 s — folga de ~100×. Ambos os testes têm margem larga o bastante para não serem sensíveis a jitter de CI.

---

## Edge Cases (spec.md)

- [x] Resposta 200 com medida fora de faixa fisicamente plausível ⇒ inválida, sem evento — `testes/test_normalizador_inmet.py:75-82` (sensor M1 da Rodada 1 já provou discriminação)
- [x] **Duas coletas (automática e manual) quase simultâneas ⇒ ambas persistidas como tentativas correlacionadas distintas** — **agora coberto** por `testes/test_meteorologia_api.py:178,180`: com o agendador automático rodando via `lifespan`, o POST manual é aceito e `GET /sincronizacoes` devolve as duas origens com `requisicao_id` distintos (era ❌ na Rodada 1)
- [x] Amostra congelada atualizada ⇒ testes determinísticos continuam sem rede — fixtures lidas de disco por `carregar_fixture`

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code (nada além do pedido) | ✅ — a Fix 4 adicionou 6 linhas de produção (`ROTULOS_ESTADO_SINCRONIZACAO`), no mesmo padrão dos mapas `ROTULOS_TIPO`/`ROTULOS_ORIGEM` já existentes |
| Sem abstrações para código de uso único | ✅ — `p95_segundos` é uma função local ao teste, não um utilitário exportado |
| Sem "flexibilidade" desnecessária | ✅ |
| Só arquivos exigidos pelas fixes tocados | ✅ — 3 testes backend, 2 arquivos frontend, mais os artefatos `.specs/` |
| Não "melhorou" código não relacionado | ✅ |
| Segue os padrões existentes | ✅ |
| Aprovaria em revisão sênior? | ✅ |
| Testes mapeiam ACs e não são rasos | ✅ |
| Spec-anchored outcome check (valor asserido = valor do spec) | ✅ — as 4 lacunas fechadas; `900` e `Concluído`/`Falha` são hardcoded, não derivados da própria produção |
| Coverage Expectation por camada | ✅ |
| Todo teste do escopo mapeia a um AC/edge case/Done-when | ✅ — os 3 testes novos declaram o AC no docstring (INMET-03/04/15) |
| Diretrizes documentadas seguidas | ✅ — `AGENTS.md` (PT-BR, dados sintéticos, sem rede real); `README.md` (comandos de verificação) |

**Anti-tautologia verificada explicitamente**: ambos os novos assertos de intervalo hardcodam `900` em vez de importar `INTERVALO_SEGUNDOS_COLETA` — se importassem, a asserção acompanharia a mutação e M2 sobreviveria de novo. Confirmado por `grep`: `INTERVALO_SEGUNDOS_COLETA` não aparece em nenhum arquivo de teste, só em comentários explicando por quê.

**Nenhuma asserção enfraquecida.** A única asserção pré-existente substituída foi `assert corpo["proxima_consulta"] is not None` → `assert proxima_consulta == iniciado_em + timedelta(seconds=900)` (**fortalecida**); e no frontend `concluido` → `Concluído` (agora casa com o rótulo do spec, também **fortalecida**).

---

## Gate Check

Ambos os gates Build reexecutados por este Verifier na árvore real, em `552b378`:

| Gate | Comando | Resultado |
| --- | --- | --- |
| Build (backend) | `uv run --directory src/backend pytest && ruff check . && pyright` | ✅ **238 passed**, 0 failed, 0 skipped, em 5,03 s · `ruff`: `All checks passed!` · `pyright`: `0 errors, 0 warnings, 0 informations` |
| Build (frontend) | `npm test -- --run && npm run lint && npm run build` | ✅ **113 passed** (18 arquivos) · `oxlint`: 6 warnings, **todos pré-existentes** (`react(only-export-components)` ×2 em `PerfilContexto.tsx`, `react(set-state-in-effect)` ×4 em superfícies, incluindo `SuperficieFonteMeteorologica.tsx:49`, cujo `useEffect` é anterior à correção — apenas deslocado 7 linhas pelo mapa novo); **0 warnings novos** · `vite build`: `✓ built in 229ms` |

**Test integrity**:

| Métrica | `43e3e3b` (pré-feature) | `552b378` (pós-fix) | Delta |
| --- | --- | --- | --- |
| `def test_` backend | 149 | 200 | **+51** |
| Casos `it(...)` frontend | 57 | 64 | **+7** |
| pytest coletados | — | 238 | +3 vs. Rodada 1 (235) |
| vitest coletados | — | 113 | +1 vs. Rodada 1 (112) |

Nenhum teste removido; nenhuma asserção enfraquecida; nenhum `skip`.

---

## Observações residuais (Minor, não bloqueantes — nenhuma justifica FAIL)

1. **INMET-12, evidência fraca** (carry-over da Rodada 1, não roteada como fix): o não-vazamento de cabeçalhos/credenciais é asserido por um único token (`"CHUVA"`) e apenas no caso de uso; `ClienteInmet` — o ponto onde cabeçalhos e a URL base efetivamente existem — não tem teste de log equivalente. Classificação inalterada em relação à Rodada 1.
2. **Rótulos `Coletando`/`Normalizando` presentes mas não asseridos**: `ROTULOS_ESTADO_SINCRONIZACAO` mapeia os quatro estados, mas só `Concluído` e `Falha` têm asserção. O spec exige que a UI exiba *um dos quatro*, e os dois estados terminais estão provados; além disso, `EstadoSincronizacao.NORMALIZANDO` (`portas_meteorologia.py:25`) **nunca é persistido por nenhum caminho de código** — o serviço grava `COLETANDO` (`coleta_meteorologica.py:165`) e fecha direto em `CONCLUIDO`/`FALHA`, porque a execução é síncrona. Estado declarado no enum e no `CHECK` da migração, mas inalcançável. Vale registrar no spec ou remover em uma história futura.
3. **Fix 5 (dívida aceita, não re-flagada)**: prova limitada ao vivo contra `apitempo.inmet.gov.br` segue não executada por falta de egresso de rede; declarada em `adaptadores/meteorologia/README.md:17-34`.
4. **L-013 ainda aberta**: os 3 `# SPEC_DEVIATION` em `portas_meteorologia.py:86,95,112` continuam no código e `design.md` **não** registra os métodos adicionados (`buscar_por_id`, `listar_ativas`, `listar`) — `grep` por esses nomes em `design.md` devolve 0 ocorrências. Lição L-013 pede exatamente o oposto (dobrar a descoberta de volta ao documento de design em vez de deixar o marcador como registro). Documentação, não comportamento; Minor.

---

## Lessons Layer

L-009 a L-013 seguem em `.specs/lessons.json` com `status: candidate` — ciclo de vida normal (viram `promoted` só após recorrência). As condições concretas que originaram L-009 a L-012 estão **fechadas** neste commit (provado pelo sensor e pelas asserções acima). L-013 permanece **aberta** na sua condição de fundo (item 4 das observações residuais). Nenhuma lição nova foi destilada: esta rodada é um PASS limpo e não produziu nenhuma falha fundamentada nova (mutante sobrevivente, AC descoberta, ou desvio de spec inédito).

---

## Requirement Traceability Update

| Requirement | Rodada 1 | Rodada 2 |
| --- | --- | --- |
| INMET-01 | ⚠️ Verified com desvio documentado | ⚠️ Verified com desvio documentado (Fix 5, dívida aceita) |
| INMET-02 | ✅ Verified | ✅ Verified |
| INMET-03 | ⚠️ Needs Fix (Fix 1) | ✅ **Verified** |
| INMET-04 | ❌ Needs Fix (Fix 2) | ✅ **Verified** |
| INMET-05 | ✅ Verified | ✅ Verified |
| INMET-06 | ⚠️ Needs Fix (Fix 4) | ✅ **Verified** |
| INMET-07 | ⚠️ Needs Fix (Fix 4) | ✅ **Verified** |
| INMET-08 | ✅ Verified | ✅ Verified |
| INMET-09 | ✅ Verified | ✅ Verified |
| INMET-10 | ✅ Verified | ✅ Verified |
| INMET-11 | ✅ Verified | ✅ Verified |
| INMET-12 | ⚠️ Verified (evidência fraca) | ⚠️ Verified (evidência fraca — inalterada) |
| INMET-13 | ✅ Verified | ✅ Verified |
| INMET-14 | ✅ Verified | ✅ Verified |
| INMET-15 | ❌ Needs Fix (Fix 3) | ✅ **Verified** |
| INMET-16 | ✅ Verified | ✅ Verified |
| INMET-17 | ✅ Verified | ✅ Verified |

---

## Summary

**Overall**: ✅ **Ready**

**Spec-anchored check**: 15/17 ACs plenamente ancorados; 2 residuais não bloqueantes (INMET-01 dívida aceita, INMET-12 evidência fraca inalterada). Rodada 1: 10/17.
**Sensor**: **2/2 mutantes mortos** (M2 re-injetado ⇒ killed por 2 testes em camadas distintas; M3 novo ⇒ killed). Rodada 1: 1/2.
**Gate**: backend 238 passed / 0 failed, ruff limpo, pyright 0 erros; frontend 113 passed, lint com 6 warnings pré-existentes (0 novos), build OK.
**Flakiness**: Fix 2 verde 5/5, folga de ~12× no orçamento de polling; Fix 3 com folga de ~100× no limiar de latência.

**O que funciona**: intervalo de coleta de produção agora é comportamento observável e protegido em duas camadas; INMET-04 é exercitado com o agendador realmente rodando, o que também fecha o edge case das duas coletas quase simultâneas; a cláusula p95 tem asserção de verdade; a UI passou a exibir os rótulos exatos do spec (correção de um desvio real, não só de cobertura); todo o resto verificado na Rodada 1 permanece intacto, sem regressão nem enfraquecimento de asserção.

**Problemas encontrados**: nenhum bloqueante. Quatro observações Minor registradas acima, das quais duas (Fix 5 e INMET-12) são carry-over já classificados na Rodada 1, uma é documentação (L-013) e uma é um estado de enum inalcançável (`normalizando`).

**Next steps**: marcar a História 2.1 como concluída. Levar as observações 2 e 4 para o backlog de arrumação; a observação 3 (prova ao vivo) quando houver rede.
