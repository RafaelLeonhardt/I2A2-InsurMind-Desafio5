# História 2.1: Coletar e normalizar dados do INMET — Validation

**Date**: 2026-09-01
**Spec**: `.specs/features/2-1-coletar-e-normalizar-dados-do-inmet/spec.md`
**Diff range**: `43e3e3b..44fd7af` (14 commits, T1–T14)
**Verifier**: independent sub-agent (author ≠ verifier), read-only sobre a árvore real

**Verdict**: ❌ **FAIL** — 1 mutante sobrevivente + 4 lacunas de cobertura ancorada em AC.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 `EventoMeteorologico` | ✅ Done | — |
| T2 Migração `0002_meteorologia.sql` | ✅ Done | `testes/test_migracoes.py:74-104` cobre aplicação e idempotência |
| T3 Portas de aplicação | ✅ Done | 3 `# SPEC_DEVIATION` documentados (`portas_meteorologia.py:86,95,112`), todos justificados e usados |
| T4 Prova limitada + amostras congeladas | ⚠️ Partial | A prova ao vivo contra `apitempo.inmet.gov.br` **não foi executada** (sem egresso de rede); as fixtures são "reconstrução de melhor esforço", não captura real — declarado abertamente em `adaptadores/meteorologia/README.md:17-34` |
| T5 `NormalizadorInmet` | ✅ Done | — |
| T6 `ClienteInmet` + dublê | ✅ Done | — |
| T7 Repositórios DuckDB | ✅ Done | — |
| T8 `ServicoColetaMeteorologica` | ✅ Done | — |
| T9 Roteador HTTP | ✅ Done | — |
| T10 `AgendadorMeteorologico` | ⚠️ Partial | Intervalo de produção (`INTERVALO_SEGUNDOS_COLETA = 900`) não é fixado por nenhuma asserção — ver Sensor M2 |
| T11 Sincronizar OpenAPI | ✅ Done | `test_saude.py:33-38` fixa os 3 caminhos novos |
| T12 Cliente HTTP do frontend | ✅ Done | — |
| T13 Superfície "Fonte meteorológica" | ✅ Done | — |
| T14 Restauração ao estado inicial completo | ✅ Done | — |

---

## Spec-Anchored Acceptance Criteria

### P1: Coleta automática e sob demanda com contrato registrado

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| INMET-01 — registrar campos, unidades, normalizações e mapeamento do endpoint escolhido | Documento de contrato campo-a-campo | `src/backend/central_preventiva/adaptadores/meteorologia/README.md:36-47` — tabela `Campo INMET → Mapeamento para EventoMeteorologico` (`CD_ESTACAO`, `CHUVA`/mm, `DT_MEDICAO`+`HR_MEDICAO`) | ⚠️ PASS com desvio documentado — o registro existe, mas a *prova limitada ao vivo* exigida pelo Goal/T4 não foi executada (`README.md:17-34`); nomes de campo não confirmados por chamada HTTP real |
| INMET-02 — amostras congeladas, parsing determinístico, sem rede | Testes de parsing sobre amostras em disco, zero rede | `testes/test_normalizador_inmet.py:17,28-31` — `carregar_fixture` lê `testes/fixtures/inmet/*.json`; nenhum `httpx` importado no módulo. Bloqueio explícito de rede em `testes/test_meteorologia_api.py:22-31` (`raise AssertionError("chamada de rede real bloqueada em teste")`) | ✅ PASS |
| INMET-03 — coleta na inicialização e no intervalo configurado | 1 coleta no boot, sem esperar o intervalo; sono de exatamente `INTERVALO_SEGUNDOS` | `testes/test_agendador_meteorologico.py:167` — `assert len(coletor.chamadas) == 1`; `:188` — `assert relogio.chamadas == [900]`; `:197-198` — `assert len(coletor.chamadas) == 2` / `assert relogio.chamadas == [900, 900]` | ⚠️ PASS parcial — o `900` asserido é o valor **injetado pelo teste** (`montar_agendador(..., intervalo_segundos=900)`), não a constante de produção; mutante M2 sobreviveu |
| INMET-04 — atualização manual aceita independentemente do agendamento em curso | `202` para o POST manual mesmo com o agendador rodando | `testes/test_meteorologia_api.py:117` — `assert resposta.status_code == 202` | ❌ GAP — o `TestClient` é criado **sem** context manager (`test_meteorologia_api.py:71`), logo o `lifespan` (e o agendador) nunca roda nesses testes; nenhuma asserção cobre "independentemente do agendamento automático em curso" |
| INMET-05 — persistir o trabalho antes de responder `202 Accepted` | Linha de sincronização persistida antes da resposta; HTTP `202` | `testes/test_coleta_meteorologica.py:177` — `assert sincronizacoes.chamadas_criar == 1`; `testes/test_meteorologia_api.py:117-120` — `assert resposta.status_code == 202` / `corpo["estado"] == "concluido"` / `corpo["registros_validos"] == 1`; `testes/test_repositorio_meteorologia.py:103-106` — `criar` persiste `estado == COLETANDO`, `registros_validos == 0`, `finalizado_em is None` | ✅ PASS |
| INMET-06 — interface exibe `Coletando`/`Normalizando`/`Concluído`/`Falha` refletindo o estado persistido | Um dos quatro estados, refletindo o estado real | `src/frontend/.../SuperficieFonteMeteorologica.test.tsx:128` — `expect(screen.getByText(/Manual — concluido — 2026-08-30T12:00:00\+00:00/))` | ⚠️ Spec-precision gap — só `concluido` é asserido; a UI imprime o valor cru do enum (`concluido`), sem o rótulo acentuado do spec (`SuperficieFonteMeteorologica.tsx:150,164` — há `ROTULOS_*` para tipo e origem, nenhum para estado); `normalizando` nunca é persistido por nenhum caminho de código (coleta é síncrona) |

### P1: Normalização com proveniência e rejeição de dados inválidos

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| INMET-07 — resposta válida vira `EventoMeteorologico` com tipo, área, período, intensidade, medidas normalizadas, instante observado | Todos os campos do evento normalizados | `testes/test_normalizador_inmet.py:43-46` — `assert evento.tipo == TipoEventoMeteorologico.CHUVA_INTENSA`, `evento.area == "9990001"`, `evento.intensidade == 55.4` | ⚠️ PASS parcial — `periodo_inicio`/`periodo_fim`/`instante_observado` **não têm asserção de valor** em nenhum teste; a derivação `DT_MEDICAO`+`HR_MEDICAO` → `instante_observado` e a janela de 1 h (`normalizador_inmet.py:90-106`) ficam sem cobertura de valor |
| INMET-08 — proveniência `real_inmet`, sem expor o formato externo ao domínio | `proveniencia == real_inmet` | `testes/test_normalizador_inmet.py:44` — `assert evento.proveniencia == ProvenienciaEvento.REAL_INMET`; `testes/test_meteorologia_api.py:187` — `assert eventos[0]["proveniencia"] == "real_inmet"` | ✅ PASS |
| INMET-09 — campo ausente / medida inválida / geografia não reconhecida ⇒ nenhum evento | `evento is None` nos três casos | `testes/test_normalizador_inmet.py:68` (campo ausente), `:78` (fora de faixa), `:88` (não numérico), `:99` (geografia), `:108` (corpo malformado) — todos `assert resultado.evento is None` | ✅ PASS |
| INMET-10 — rejeição termina com código e motivo inspecionáveis | Motivo tipado consultável, sem avançar | `testes/test_normalizador_inmet.py:69` — `assert motivo_rejeicao == MotivoRejeicao.CAMPO_AUSENTE`; `:79`/`:89` — `MEDIDA_INVALIDA`; `:100` — `GEOGRAFIA_NAO_RECONHECIDA`; `testes/test_coleta_meteorologica.py:209` — `assert resultado.motivo_falha == "campo_ausente"`; `testes/test_repositorio_meteorologia.py:153` — `assert atualizada.motivo_falha == "campo_ausente"` (persistido) | ✅ PASS |

### P2: Observabilidade, histórico e idempotência da sincronização

| Criterion | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| INMET-11 — persistir início, término, resultado, registros válidos e `requisicao_id` | Todos os cinco campos persistidos | `testes/test_repositorio_meteorologia.py:103-106` — `sincronizacao.requisicao_id == requisicao_id`, `estado == COLETANDO`, `registros_validos == 0`, `finalizado_em is None`; `:129-131` — `estado == CONCLUIDO`, `registros_validos == 1`, `finalizado_em is not None`; `:153` — `motivo_falha == "campo_ausente"` | ✅ PASS |
| INMET-12 — não logar cabeçalhos, credenciais nem corpo externo integral | Nenhum log com esses conteúdos | `testes/test_coleta_meteorologica.py:265-266` — `assert "CHUVA" not in saida.out` / `not in saida.err` | ⚠️ PASS fraco — asserção sobre um único token (`CHUVA`) e só no caso de uso; nenhum teste equivalente para `ClienteInmet` (`cliente_inmet.py`) nem para o roteador, que são os pontos onde cabeçalhos/credenciais existiriam |
| INMET-13 — UI exibe tipo, local, período, intensidade, origem e horário | Os seis campos por evento | `SuperficieFonteMeteorologica.test.tsx:90-95` — `getByText('Chuva intensa')`, `getByText('9990001')`, `getByText(/2026-08-30T17:00:00\+00:00.*2026-08-30T18:00:00\+00:00/)`, `getByText('55.4')`, `getByText('INMET (real)')`, `getAllByText('2026-08-30T18:00:00+00:00')` | ✅ PASS |
| INMET-14 — alternativa em lista operável por teclado e leitor de tela | Seleção via teclado, estado exposto à AT | `SuperficieFonteMeteorologica.test.tsx:107-118` — `expect(botaoSelecionar).toHaveFocus()`, `keyboard('{Enter}')`, `toHaveAttribute('aria-pressed','true')`, `getByRole('row', …)).toHaveAttribute('aria-selected','true')` | ✅ PASS |
| INMET-15 — última tentativa, última válida, próxima consulta e resultados anteriores, só com dados persistidos, ≤ 1 s p95 | Os 4 marcos + latência p95 ≤ 1 s | `testes/test_meteorologia_api.py:214-223` — `set(corpo) == {ultima_tentativa, ultima_valida, proxima_consulta, resultados_anteriores}`, `corpo["ultima_tentativa"]["estado"] == "concluido"`, `corpo["ultima_valida"]["estado"] == "concluido"`, `len(corpo["resultados_anteriores"]) == 1`; `:233-236` — marcos nulos sem coleta | ❌ GAP parcial — a cláusula **`em até 1 segundo no percentil 95`** não tem nenhuma asserção em todo o repositório (nenhum `perf_counter`/`elapsed`/`p95` nos testes); `proxima_consulta` só é asserido como `is not None` (`:222`), nunca como `iniciado_em + 900 s` |
| INMET-16 — mesma `Idempotency-Key` não inicia outra coleta e devolve a resposta registrada | Zero segunda coleta; corpo idêntico | `testes/test_meteorologia_api.py:141-142` — `assert primeira.json() == segunda.json()` e `assert len(chamadas) == 1` (dublê de transporte instrumentado); `testes/test_coleta_meteorologica.py:233-236` — `len(coletor.chamadas) == 1`, `sincronizacoes.chamadas_criar == 1`, `segunda.sincronizacao.id == primeira.sincronizacao.id`, `segunda.aceito_em == primeira.aceito_em` | ✅ PASS (evidência forte) |
| INMET-17 — restauração repõe o estado inicial completo, wipe por catálogo com lista de exceções | Tabelas fora da lista vazias; exceções intactas; reseed determinístico | `testes/test_semeador.py:252` — `assert depois[0] == 0` (`sincronizacoes_meteorologicas`); `:274-275` — `assert area is not None` e `versao_depois == versao_antes` (`areas_monitoradas_inmet` + `schema_migracoes`); `:279` — `assert frozenset({"schema_migracoes","areas_monitoradas_inmet"}) == TABELAS_EXCECAO_RESTAURACAO`; `:147` — `contagens(caminho) == contagens_originais` (reseed) | ✅ PASS |

**Status**: ❌ 2 GAPs (INMET-04, INMET-15/p95) + 4 PASS-parcial/spec-precision (INMET-01, INMET-03, INMET-06, INMET-07, INMET-12); 10 ACs plenamente ancorados.

---

## Payload/Conjunction Rule (rotas + repositórios)

| Camada | Verificação | Resultado |
| --- | --- | --- |
| `POST /api/v1/meteorologia/coletas` | Além do `202`, asserta `corpo["estado"] == "concluido"` e `corpo["registros_validos"] == 1` (`test_meteorologia_api.py:119-120`) | ✅ valores, não só status |
| Erros do roteador | `422`/`404` asseridos junto com `content-type` `application/problem+json` e `codigo` estável (`:99-101`, `:154-156`) | ✅ |
| `GET /eventos` | Conjunto exato de campos (`:185`) + valores `tipo == "chuva_intensa"`, `proveniencia == "real_inmet"` (`:186-187`) | ✅ |
| `GET /sincronizacoes` | Conjunto exato de chaves + `estado == "concluido"` nos dois marcos (`:214-221`) | ⚠️ `proxima_consulta` só `is not None` (`:222`) — valor não verificado |
| Idempotência | Igualdade de corpo **e** contagem de chamadas ao transporte (`:141-142`) | ✅ não é "a chamada aconteceu" |
| Repositórios | Round-trip de igualdade de entidade (`test_repositorio_meteorologia.py:80`), campos de estado/motivo/ordenação (`:129-131`, `:153`, `:183`) | ✅ estado real, não mocks |
| Lifespan/agendador | `test_agendador_meteorologico.py:242-259` — o único assert é `resposta.status_code == 200` de `/api/v1/saude` | ⚠️ não asserta que a task foi iniciada nem cancelada; o nome do teste promete mais do que a asserção entrega |

---

## Discrimination Sensor

Depth: lightweight (2 mutações), uma worktree descartável por mutação, árvore real nunca tocada.
Baseline `git status --porcelain` antes do sensor: vazio. Após ambas as mutações: vazio; `git worktree list` mostra só a árvore principal em `44fd7af`.

| # | File:line | Mutation | Test executado | Killed? |
| --- | --- | --- | --- | --- |
| M1 | `adaptadores/meteorologia/normalizador_inmet.py:17` | Limite de plausibilidade `INTENSIDADE_MAXIMA_PLAUSIVEL = 500.0` → `99999.0` (fronteira de faixa física) | `testes/test_normalizador_inmet.py` | ✅ **Killed** — `test_medida_fora_de_faixa_plausivel_e_rejeitada_sem_criar_evento` falhou (`assert resultado.evento is None` recebeu um `EventoMeteorologico`) |
| M2 | `aplicacao/portas_meteorologia.py:64` | Intervalo de coleta automática `INTERVALO_SEGUNDOS_COLETA = 900` → `60` (15 min → 1 min em produção) | `testes/test_agendador_meteorologico.py` + `testes/test_meteorologia_api.py`, depois a **suíte backend inteira** | ❌ **SURVIVED** — 14/14 e depois 235/235 testes passaram com o intervalo de produção alterado |

**Causa raiz do M2**: `test_agendador_meteorologico.py:139,180` injeta `intervalo_segundos=900` explicitamente em vez de exercitar o valor padrão, e o único outro consumidor da constante — `proxima_consulta` em `adaptadores/http/meteorologia.py:312` — só é verificado como `is not None` (`test_meteorologia_api.py:222`). Nenhuma asserção liga o comportamento observável ao `900` de produção.

**Result**: 1/2 killed — ❌ FAIL.

---

## Edge Cases (spec.md)

- [x] Resposta 200 com medida fora de faixa fisicamente plausível ⇒ inválida, sem evento — `testes/test_normalizador_inmet.py:72-79` (e confirmado pelo sensor M1)
- [ ] Duas coletas (automática e manual) aceitas quase simultaneamente ⇒ ambas persistidas como tentativas correlacionadas distintas — **NÃO coberto**: nenhum teste do escopo cria duas coletas concorrentes (`grep` por `gather(`/`simultan`/`concorren` nos testes desta feature: zero ocorrências)
- [x] Amostra congelada atualizada ⇒ testes determinísticos continuam sem rede — as fixtures são carregadas de disco por `carregar_fixture` (`test_normalizador_inmet.py:28-31`), sem nenhuma dependência de rede

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code (nada além do pedido) | ✅ |
| Sem abstrações para código de uso único | ✅ |
| Sem "flexibilidade" desnecessária | ✅ |
| Só arquivos exigidos pelas tasks tocados | ✅ |
| Não "melhorou" código não relacionado | ✅ (`test_inicializador.py`/`test_migracoes.py`/`test_saude.py` mudaram só pelo efeito real da migração `0002` e dos endpoints novos) |
| Segue os padrões existentes (fábrica de roteador, `Protocol` como porta, `problem+json`, fixture `autouse` de bloqueio de rede) | ✅ |
| Aprovaria em revisão sênior? | ⚠️ — sim, com as ressalvas de M2 e INMET-15 |
| Testes mapeiam ACs e não são rasos | ⚠️ — ver INMET-06/07/12 |
| Spec-anchored outcome check | ❌ — INMET-04 e a cláusula p95 de INMET-15 sem evidência |
| Coverage Expectation por camada (domínio 1:1; rotas feliz+borda+erro) | ✅ — rotas cobrem feliz, vazio, erro 422/404, idempotência e CORS |
| Todo teste do escopo mapeia a um AC/edge case/Done-when | ✅ — nenhum teste órfão |
| Diretrizes documentadas seguidas | ✅ — `AGENTS.md` (PT-BR, dados sintéticos, sem rede real); `README.md` (comandos de verificação) |

Observação de dívida: 3 marcadores `# SPEC_DEVIATION` em `aplicacao/portas_meteorologia.py:86,95,112` (métodos `buscar_por_id`, `listar_ativas`, `listar`) — todos justificados, usados e necessários; nenhum é código especulativo.

---

## Gate Check

- **Gate command (Build, backend)**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`
- **Gate command (Build, frontend)**: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**: confirmados verdes pelo orquestrador imediatamente antes do despacho deste Verifier (backend pytest, ruff, pyright; frontend vitest, lint, build). Este Verifier não os reexecutou para aprovação — a suíte backend completa foi executada apenas dentro da worktree descartável do sensor M2, onde passou 235/235 **com o mutante aplicado** (essa é a evidência do sobrevivente, não uma aprovação de gate).
- **Test integrity**: nenhum teste removido no intervalo `43e3e3b..44fd7af`; nenhuma asserção enfraquecida — as três mudanças em testes pré-existentes (`test_migracoes.py`, `test_inicializador.py`, `test_saude.py`) **fortalecem** as asserções (versões `[1] → [1, 2]`, tabelas e caminhos novos fixados).
- **Delta**: +7 arquivos de teste novos (5 backend, 2 frontend), +~1.400 linhas de teste.
- **Skipped**: nenhum.

---

## Fix Plans

### Fix 1: Fixar o intervalo de coleta automática de produção (mutante sobrevivente M2)

- **Root cause**: `testes/test_agendador_meteorologico.py:139,180` injeta o intervalo em vez de exercitar `INTERVALO_SEGUNDOS_COLETA`; `proxima_consulta` só é verificado como não-nulo.
- **Fix task**: adicionar (a) um teste que instancie `AgendadorMeteorologico` **sem** `intervalo_segundos` e asserte `relogio.chamadas == [900]`, e (b) em `test_meteorologia_api.py`, asserter `proxima_consulta == ultima_tentativa.iniciado_em + 900 s`.
- **Verify**: repetir a mutação `900 → 60` e confirmar falha.
- **Priority**: Major

### Fix 2: Cobrir INMET-04 (manual aceita com o agendamento em curso)

- **Root cause**: `test_meteorologia_api.py:71` cria o `TestClient` fora de context manager, então o `lifespan`/agendador nunca roda nos testes de rota.
- **Fix task**: um teste que use `with TestClient(...) as cliente:` (lifespan ativo, agendador rodando) e faça o `POST /coletas`, assertando `202` e que ambas as tentativas (automática e manual) aparecem como linhas distintas com `requisicao_id` diferentes em `GET /sincronizacoes` — o que cobre também o edge case das duas coletas quase simultâneas.
- **Priority**: Major

### Fix 3: Cobrir a cláusula de latência p95 de INMET-15

- **Root cause**: nenhum teste mede tempo de resposta; a cláusula "até 1 segundo no percentil 95" nunca é verificada.
- **Fix task**: teste de orçamento de latência sobre `GET /sincronizacoes` e `GET /eventos` com histórico semeado, medindo com `perf_counter` sobre N repetições e assertando o p95 < 1 s — ou, se o time decidir que isso não é testável de forma estável localmente, registrar a decisão no spec e rebaixar a cláusula a não-verificável.
- **Priority**: Major

### Fix 4: Ancorar INMET-07 nos campos temporais e INMET-06 no estado exibido

- **Root cause**: `periodo_inicio`/`periodo_fim`/`instante_observado` não têm asserção de valor; a UI só é testada com `concluido` e imprime o enum cru.
- **Fix task**: (a) assertar em `test_normalizador_inmet.py` que `instante_observado == datetime(2026,8,30,18,0)` e `periodo_inicio == instante_observado - 1h`; (b) adicionar caso de UI com `estado = "falha"` (e `motivoFalha`) e decidir se o spec exige rótulos acentuados (`Concluído`) — se sim, adicionar `ROTULOS_ESTADO`.
- **Priority**: Minor

### Fix 5 (não bloqueante): fechar a dívida da prova ao vivo do INMET (T4)

- **Root cause**: sem egresso de rede na sessão de implementação; fixtures são reconstrução, não captura (`adaptadores/meteorologia/README.md:17-34`).
- **Fix task**: quando houver rede, executar a prova pontual, confrontar os nomes de campo e atualizar as fixtures + o README.
- **Priority**: Minor (já declarado como dívida explícita)

---

## Requirement Traceability Update

| Requirement | Previous | New |
| --- | --- | --- |
| INMET-01 | Implementing | ⚠️ Verified com desvio documentado |
| INMET-02 | Implementing | ✅ Verified |
| INMET-03 | Implementing | ⚠️ Needs Fix (Fix 1) |
| INMET-04 | Implementing | ❌ Needs Fix (Fix 2) |
| INMET-05 | Implementing | ✅ Verified |
| INMET-06 | Implementing | ⚠️ Needs Fix (Fix 4) |
| INMET-07 | Implementing | ⚠️ Needs Fix (Fix 4) |
| INMET-08 | Implementing | ✅ Verified |
| INMET-09 | Implementing | ✅ Verified |
| INMET-10 | Implementing | ✅ Verified |
| INMET-11 | Implementing | ✅ Verified |
| INMET-12 | Implementing | ⚠️ Verified (evidência fraca) |
| INMET-13 | Implementing | ✅ Verified |
| INMET-14 | Implementing | ✅ Verified |
| INMET-15 | Implementing | ❌ Needs Fix (Fix 3) |
| INMET-16 | Implementing | ✅ Verified |
| INMET-17 | Implementing | ✅ Verified |

---

## Summary

**Overall**: ⚠️ Issues — implementação sólida e bem estruturada, com lacunas de *discriminação de teste*, não de comportamento.

**Spec-anchored check**: 10/17 ACs plenamente ancorados; 5 parciais/spec-precision; 2 GAPs.
**Sensor**: 1/2 mutantes mortos (M2 sobreviveu).
**Gate**: verde (confirmado pelo orquestrador antes do despacho).

**O que funciona**: normalização com rejeição tipada em todos os branches (M1 morto prova discriminação real); idempotência ponta a ponta com contagem de chamadas ao transporte (evidência forte); persistência de sincronização com início/término/estado/registros/correlação; restauração AD-014 orientada por catálogo com lista de exceções fixada por asserção; superfície acessível com seleção por teclado; contrato OpenAPI e tipos do frontend em sincronia.

**Problemas encontrados**: (1) o intervalo de produção de 15 min pode ser alterado sem quebrar nenhum teste; (2) INMET-04 nunca exercita coleta manual com o agendador ativo; (3) a cláusula de p95 ≤ 1 s de INMET-15 não é verificada em lugar nenhum; (4) campos temporais do evento e estados não-`concluido` da UI sem asserção de valor.

**Next steps**: rotear Fix 1–4 como fix tasks para um implementador e re-verificar (ciclo máximo de 3 iterações). Fix 5 pode seguir como dívida registrada.
