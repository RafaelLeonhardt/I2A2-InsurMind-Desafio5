# História 5.8: Executar e comprovar os cenários ponta a ponta — Validation

**Date**: 2026-09-07
**Spec**: `.specs/features/5-8-executar-e-comprovar-os-cenarios-ponta-a-ponta/spec.md`
**Diff range**: `589d1ba..bd3bbc6`
**Verifier**: independent sub-agent (author ≠ verifier)
**Verdict**: **PASS ✅**

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 | ✅ Done | `testes-e2e/playwright.config.ts`, `workers: 1` justificado (DuckDB escritor único, portas fixas); README documenta a instalação dos navegadores |
| T2 | ✅ Done | `cenarios/chuva-intensa.spec.ts` |
| T3 | ✅ Done | `cenarios/granizo.spec.ts` |
| T4 | ✅ Done | `cenarios/sem-risco.spec.ts` |
| T5 | ✅ Done | `cenarios/sem-elegivel.spec.ts` |
| T6 | ✅ Done | `cenarios/regeneracao.spec.ts` |
| T7 | ✅ Done | `cenarios/contingencia-inmet.spec.ts` — SPEC_DEVIATION declarado (tentativas/snapshot pela API REST) |
| T8 | ✅ Done | `cenarios/indisponibilidade-openai.spec.ts` — SPEC_DEVIATION declarado (variante `OPENAI_API_KEY` ausente) |
| T9 | ✅ Done | `cenarios/retentativa.spec.ts` |
| T10 | ✅ Done | `cenarios/evidencias-localizaveis.spec.ts` — SPEC_DEVIATION declarado (4 de 7 evidências pela API REST) |
| T11 | ✅ Done | `responsividade/*.spec.ts`. Ressalva de rastreabilidade: introduzido no commit `c3a3c21`, cuja mensagem é apenas "mudanca de porta de 5173 para 5151" (ver Achado 4) |
| T12 | ✅ Done | `acessibilidade/*.spec.ts`. Mesma ressalva de commit |
| T13 | ✅ Done | `scripts/gerar_evidencias.py` + `docs/evidencias/` + README. Reexecutado ponta a ponta por este Verifier (ver Gate Check) |

Nenhuma task bloqueada ou parcial. Todos os 13 checkboxes de "Done when" foram reconferidos contra o código, não aceitos por confiança.

---

## Spec-Anchored Acceptance Criteria

### P1: Cenários completos e encerramentos determinísticos comprovados

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| **E2E-01** WHEN chuva intensa residencial em ambiente restaurado THEN avança da entrada meteorológica até o comunicado de um segurado elegível, com ≥1 não elegível com explicação consultável | fluxo completo verde; 1 incluído, ≥1 excluído com motivo consultável; comunicado visível na interface | `cenarios/chuva-intensa.spec.ts:55` - `expect(comPublico.publico_elegivel_total).toBe(1)`; `:62` - `expect(elegibilidade.excluidos).toBe(1)`; `:71-72` - `expect(criterioReprovado?.valor_observado).toBe('cancelada')` / `expect(...justificativa).toBe('Apólice não está ativa (situação: cancelada).')`; `:101` - `expect(simulada.entregas[0]?.corpo).toBe(CONTEUDO_PADRAO_DUBLE.whatsapp)`; `:110` - `expect(detalhe.getByText(CONTEUDO_PADRAO_DUBLE.whatsapp)).toBeVisible()` | ✅ PASS |
| **E2E-02** WHEN granizo automóvel THEN avança até o comunicado preservando regras, apólices, canais e recomendações, com entrada do cenário sintético rotulado (AD-013) | `proveniencia = sintetico` do evento ao fim; regra de granizo (limiar 20, apólice automóvel, cobertura granizo, canal SMS); recomendações específicas | `cenarios/granizo.spec.ts:72` - `expect(granizoAtivado?.proveniencia).toBe('sintetico')`; `:83-87` - `expect(regra.limiar_meteorologico).toBe(20)` / `.apolice_tipo).toBe('automovel')` / `.cobertura_exigida).toBe('granizo')` / `.canal).toBe('sms')`; `:112` - `expect(item.destinatario.apolice_id).toBe(APOLICE_GRANIZO_ELEGIVEL_ID)`; `:132` - `expect(alerta.alerta?.recomendacoes).toEqual(RECOMENDACOES_GRANIZO)`; `:145` - `expect(apolice.getByText('Automóvel', { exact: true })).toBeVisible()` | ✅ PASS |
| **E2E-03** WHEN evento sem risco e evento sem público elegível THEN ambos terminam com motivo e evidência determinísticos, sem nenhuma chamada à OpenAI, mensagem ou simulação | estados `sem_risco` / `sem_elegiveis`; justificativa tipada; zero chamadas OpenAI, zero mensagens, zero entregas | `cenarios/sem-risco.spec.ts:36` - `expect(terminal.estado).toBe('sem_risco')`; `:46-48` - `expect(criterioIntensidade?.justificativa).toBe('Intensidade observada fica abaixo do limiar de 50.0 mm.')`; `:60-61` - `expect(chamadas.openaiChat).toEqual([])` / `expect(chamadas.openaiModelos).toEqual([])`. `cenarios/sem-elegivel.spec.ts:56` - `expect(terminal.estado).toBe('sem_elegiveis')`; `:76-78` - `expect(criterioAlertas?.justificativa).toBe('Segurado optou por não participar de alertas preventivos.')`; `:98-99` - `expect(chamadas.openaiChat).toEqual([])` | ✅ PASS |

### P1: Resiliência agêntica e de integração comprovada

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| **E2E-04** WHEN regeneração a partir de reprovação do crítico THEN demonstra retorno ao redator, motivos, histórico e limite de 3 tentativas; esgotamento produz exceção e impede a mensagem de entrar na simulação | 3 versões registradas; `falhou_conteudo` + `Exceção`; mensagem fora do lote simulável | `cenarios/regeneracao.spec.ts:90-92` - `expect(item.limite_tentativas).toBe(3)` / `expect(item.versoes.map(v => v.numero_tentativa)).toEqual([1, 2, 3])`; `:102-105` - `expect(item.estado).toBe('falhou_conteudo')` / `expect(item.em_excecao).toBe(true)` / `expect(item.pode_regenerar).toBe(false)`; `:120-121` - `expect(detalhe.excecao?.impacto).toBe(IMPACTO_ITEM_FORA_DO_LOTE)` / `expect(detalhe.excecao?.tentativas).toBe(3)`; `:126-133` - `expect(chamadas.openaiChat.map(c => c.esquema)).toEqual([redator, crítico, redator, crítico, redator, crítico])` (prova o retorno ao redator); `:152` - `expect(simulacao.entregas).toEqual([])` | ✅ PASS |
| **E2E-05** WHEN indisponibilidade controlada do INMET THEN demonstra timeout, tentativas, snapshot informativo e ativação explícita do cenário sintético, com origem sintética visível até o fim | Prontidão `Indisponível` + causa + impacto; 3 tentativas `timeout`; snapshot anterior preservado; `proveniencia = sintetico` até a tela do segurado | `cenarios/contingencia-inmet.spec.ts:88-90` - `expect(linhaInmet.getByText(CAUSA_TIMEOUT_INMET)).toBeVisible()` / `...IMPACTO_INMET_INDISPONIVEL`; `:100-107` - `expect(falhada?.motivo_falha).toBe('retentativas_esgotadas')` / `expect(falhada?.tentativas.map(t => t.codigo_resultado)).toEqual(['timeout','timeout','timeout'])`; `:111-113` - `expect(aposQueda.ultima_valida?.id).toBe(snapshotValido?.id)` / `expect(terminal.marcos.map(m => m.marco)).toEqual(['falhou_coleta'])`; `:151` - `expect(alerta.alerta?.origem).toBe('sintetico')`; `:156` - `expect(visaoGeral.getByText('Cenário demonstrativo (sintético)').first()).toBeVisible()` | ✅ PASS |
| **E2E-06** WHEN produção agêntica alcançada sob indisponibilidade ou configuração ausente da OpenAI THEN o preflight termina o agregado em `falhou_preparacao_ia`, sem resposta fixa ou modelo alternativo, com o trabalho determinístico anterior consultável | `falhou_preparacao_ia`; 3 tentativas de preflight; zero chamadas de geração; coleta/evento/risco/elegibilidade ainda legíveis | `cenarios/indisponibilidade-openai.spec.ts:80-81` - `expect(preflight.estado).toBe('falhou_preparacao_ia')` / `expect(preflight.causa).toBe(CAUSA_CONEXAO)`; `:92-93` - `expect(chamadas.openaiModelos).toHaveLength(3)` / `expect(chamadas.openaiChat).toEqual([])` (sem modelo alternativo, sem resposta fixa); `:124-131` - `expect(terminal.marcos.map(m => m.marco)).toEqual([...])` sequência exata; `:160` - segunda causa `expect(preflight.causa).toBe(CAUSA_MODELO_AUSENTE)` | ✅ PASS (com SPEC_DEVIATION declarado — ver Desvios) |
| **E2E-07** WHEN retentativa a partir de falha terminal THEN nova execução correlacionada, inicializada só com snapshots imutáveis válidos, sem reabrir a original; repetir o comando não duplica | `execucao_origem_id`; cópias com ids novos; origem permanece terminal; repetição devolve a mesma execução | `cenarios/retentativa.spec.ts:59-60` - `expect(criada.execucao_origem_id).toBe(origemId)` / `expect(criada.execucao_id).not.toBe(origemId)`; `:68-69` - `expect(origemDepois.estado).toBe('falhou_preparacao_ia')` / `expect(origemDepois.retentativas).toEqual([criada.execucao_id])`; `:86-90` - conteúdo idêntico mas `expect(elegibilidadeNova.registros.some(r => idsOrigem.has(r.id))).toBe(false)`; `:95` - `expect(repetida.execucao_id).toBe(criada.execucao_id)`; `:103-105` - `expect(aguardando.resultados.map(...)).toEqual([criada.execucao_id])` (uma só execução) | ✅ PASS |

### P1: Evidências localizáveis, contrato de API fiel e suíte completa

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| **E2E-08** WHEN a pessoa navegar pelas evidências THEN localiza prontidão, evento e decisão, supervisão, resultados, comunicado, explicação e linha do tempo sem editar arquivos ou banco; OpenAPI/Swagger correspondem à API realmente utilizada | as 7 evidências alcançáveis; documento ao vivo == instantâneo versionado; toda rota exercitada publicada | `cenarios/evidencias-localizaveis.spec.ts:143-146` (prontidão, UI real); `:150-157` (evento e decisão); `:160-171` (supervisão); `:174-181` - `expect(resultados.totais_por_estado).toEqual([{ chave: 'simulada_entregue', total: 1 }])`; `:196-210` (comunicado + linha do tempo do alerta, UI real); `:215-224` - `expect(explicacao.evento_e_regra.origem).toBe('deterministica')` / `expect(explicacao.agente.origem).toBe('agente')`; `:184-192` (linha do tempo, 7 tipos de marco). Contrato: `:239` - `expect(operacoes(aoVivo)).toEqual(operacoes(versionado))`; `:245` - `expect(ausentes).toEqual([])` sobre 37 rotas exercitadas; `:256` - Swagger UI real | ✅ PASS (com SPEC_DEVIATION declarado — ver Desvios) |
| **E2E-09** WHEN a suíte completa for executada sem integrações externas reais THEN cobre sucesso, encerramentos antecipados, reprovação e esgotamento, falha do INMET, falha da OpenAI, idempotência, contratos da API e jornadas críticas da interface, reproduzível a partir de um conjunto restaurado | um comando roda as 3 suítes; sai não-zero se qualquer uma falhar; um relatório por cenário citando `file:line`; determinismo por restauração | `scripts/gerar_evidencias.py:245-247` (as 3 suítes na ordem); `:257-261` - `codigo_final = max(backend, frontend, e2e)` devolvido como `SystemExit` (`:270`); `:187` - `f"| {caso.titulo} | \`testes-e2e/{caso.arquivo}:{caso.linha}\` | {resultado} |"` (citação `file:line` real, vinda do reporter JSON do Playwright, não escrita à mão); `suporte/cenario.ts:16` - `await restaurarDadosSinteticos()` antes de cada cenário (AD-014); `suporte/processos.ts:35-38` - `CENTRAL_PREVENTIVA_URL_BASE_INMET` / `OPENAI_BASE_URL` apontados ao dublê local (nenhuma rede externa). Reexecutado por este Verifier: exit 0, 13 relatórios reproduzidos byte a byte | ✅ PASS |

### P2: Fidelidade visual, componentes contratados e acessibilidade WCAG 2.2 AA

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| **E2E-10** WHEN os fluxos forem verificados em 1440×1024 e ≥1024px THEN nenhuma função essencial desaparece, o sistema visual permanece consistente, e abaixo de 1024px o aviso de resolução é exibido | referência + 1024/1280/1920px sem perda de função; aviso exato abaixo de 1024px | `responsividade/viewports.spec.ts:107` - `expect(grade.startsWith('252px ')).toBe(true)` (grade real via `getComputedStyle`); `:83` - `expect(caixa!.x).toBeGreaterThanOrEqual(252)` para toda `.conteudo` (nenhuma superfície sob a navegação); `:128`/`:142` parametrizados nas 3 larguras, com `toBeEnabled()` nas ações essenciais; `:158-159` - `await expect(aviso).toBeVisible()` / `await expect(aviso).toHaveText(AVISO_RESOLUCAO)` (texto integral, não presença); `:177` - `expect(page.getByRole('note')).toHaveCount(0)` ao voltar | ✅ PASS |
| **E2E-11** WHEN os estilos e componentes forem inspecionados THEN usam os tokens de cores, tipografia Inter/Roboto Condensed, escala de espaçamento, raios e dimensões canônicas de `DESIGN.md` | valores canônicos de `DESIGN.md` | `responsividade/sistema-visual.spec.ts:108-110` - `expect(await estiloDe(navegacao, 'background-color')).toBe('rgb(6, 29, 69)')` (= `#061D45`, `DESIGN.md:12`) / `width` = `252px` (`DESIGN.md:44`); `:117-119` - fundo secundário `#082B67` (`DESIGN.md:13`), `min-height` `44px` (`DESIGN.md:49-50`); `:126` - borda `#D5E0E5` (`DESIGN.md:19`); `:132` - `border-radius` `5px` (`{rounded.sm}`); `:140-144` - `font-family` `"Roboto Condensed", sans-serif` / `Inter, Arial, sans-serif` (`DESIGN.md:28-29,93`); `:152` - `outline-width` `3px` (`DESIGN.md:68`). Valores conferidos contra `DESIGN.md` por este Verifier: **não circulares** | ⚠️ **Desvio documentado** — 9 tokens medidos divergem de `DESIGN.md` e estão registrados em `responsividade/sistema-visual.spec.ts:22-32`; o teste deliberadamente **não** afirma o valor divergente (não transforma o desvio em contrato). O AC não é integralmente atendido pela implementação; a correção é "Out of Scope" desta história por `spec.md:30` |
| **E2E-12** WHEN cada superfície for verificada contra `DESIGN.md`/`EXPERIENCE.md` THEN os estados estão implementados conforme contrato, sem nenhuma função aprovada como botão inerte ou dado fixo | todo controle produz efeito real e reversível | `responsividade/sistema-visual.spec.ts:170-178` - a mesma ação produz `Indisponível` e depois `Disponível` conforme a sonda (não estado fixo); `:186-195` - modal confirma, executa a restauração real e informa; `:204-207` - `toHaveAttribute('href', 'http://127.0.0.1:8000/docs')`; `:212-220` - `expect(apoliceExibida(page).getByText('DEMO-AUT-0003')).toBeVisible()` + `expect(...'DEMO-RES-0001').toHaveCount(0)` (dado troca de verdade); `:237-241` - `expect.poll(...participa_de_alertas).toBe(false)` e `expect(depois.versao).toBe(antes.versao + 1)` (gravou na fonte da verdade, não só na tela) | ✅ PASS para as superfícies montadas; escopo limitado declarado em `sistema-visual.spec.ts:11-13` |
| **E2E-13** WHEN a auditoria de acessibilidade for realizada (teclado, foco, contraste, zoom 200%, nomes acessíveis, movimento reduzido) THEN os critérios WCAG 2.2 AA são atendidos | zero violação crítica/séria; os 6 eixos cobertos | `acessibilidade/axe.spec.ts:43` - `withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa'])`; `:83-86` - `expect(proibidas).toEqual([])` (contagem real de violações críticas/sérias, com o quadro completo na mensagem) em 9 estados (`:114`, `:123`, `:132`, `:136`, `:143`, `:151`, `:162`, `:173`, `:179`). `acessibilidade/checklist-manual.spec.ts:100` - `expect(await elementoFocado(page)).toEqual({ id: 'conteudo-principal', tagName: 'MAIN' })`; `:113` - `toBeFocused()` por item de navegação; `:137/:141` - foco entra no modal e volta à origem após `Esc`; `:156` - foco devolvido ao item de origem; `:180` - `expect(rolagem.conteudo).toBeLessThanOrEqual(rolagem.visivel)` medido no estado de maior densidade textual; `:215` - `expect(emMovimento).toEqual([])` varrendo `getComputedStyle` de todos os elementos sob `prefers-reduced-motion: reduce` | ✅ PASS; lacuna de escopo declarada em `axe.spec.ts:14-18` |

**Status**: ✅ 12/13 ACs atendidos com asserção que casa com o desfecho definido no spec. 1 (E2E-11) atendido parcialmente, com os 9 desvios medidos, registrados e não silenciados — conforme exige o Edge Case de `spec.md:116`.

**Evidence-or-zero**: nenhum critério ficou sem citação `file:line`. Nenhum critério passou por "existe uma asserção" — todos afirmam o valor exato (estado, causa, justificativa, contagem, token, cor computada).

---

## Discrimination Sensor

Escopo escolhido: como esta história **é** a camada de verificação, a pergunta certa não é "o teste do teste falha?", mas "esta suíte E2E nova detecta uma regressão real de produção?". As três mutações atacam código de produção coberto pelos testes novos.

| Mutation | File:line | Description | Killed? |
| --- | --- | --- | --- |
| 1 | `src/backend/central_preventiva/composicao/api.py:140` | CORS deixa de liberar `PUT`: `allow_methods=["GET","POST","PUT"]` → `["GET","POST"]` | ✅ Killed — `responsividade/sistema-visual.spec.ts:223` falhou (`1 failed, 10 passed`). É exatamente o defeito que a suíte encontrou em `36523bf` |
| 2 | `src/backend/central_preventiva/aplicacao/grafos/geracao_mensagem.py:77` | Limite de tentativas de conteúdo: `MAXIMO_TENTATIVAS_MENSAGEM = 3` → `4` | ✅ Killed — `cenarios/regeneracao.spec.ts:58` falhou com diagnóstico explícito: "não alcançou aguardando_revisao... Estado observado: processando_mensagens. Marcos: ..." |
| 3 | `src/frontend/src/App.tsx:46,49` | Limiar do aviso de resolução: `window.innerWidth < 1024` → `< 900` | ✅ Killed — `responsividade/viewports.spec.ts:153` e `:171` falharam (`2 failed, 8 passed`) |

**Sensor depth**: lightweight (3 mutações, risco padrão — não é P0)
**Result**: 3/3 killed — **PASS ✅**

**Isolamento**: git worktree temporário em scratch (`git worktree add`), nunca `git stash`. Baseline `git status --porcelain` do worktree real **vazio** antes; **vazio** depois; `HEAD` inalterado em `bd3bbc6`; `git worktree list` de volta a uma única entrada. Sensor válido.

---

## Interactive UAT Results

Não executada. Esta história é a própria camada de verificação automatizada; os critérios que exigiriam julgamento humano (contraste, refluxo, foco, movimento reduzido) foram convertidos em asserção de navegador real medida em tempo de execução, que é mais forte que a inspeção assistida prevista no `spec.md:38`.

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ `suporte/api.ts:13-29` é `fetch` cru com `Idempotency-Key`; nenhuma camada de abstração além do necessário |
| Surgical changes | ✅ Correções de produção limitadas ao defeito e acompanhadas de regressão `vitest` (`SuperficieAlertas.test.tsx`, `SuperficieApolice.test.tsx`, `SuperficieComunicados.test.tsx`, +92 linhas) |
| No scope creep | ✅ Nenhuma capacidade de produto nova; as 4 correções inline referenciam o AC violado, como `spec.md:30` autoriza |
| Matches patterns | ✅ PT-BR em nomes, comentários e mensagens; mesma disciplina de dublês dos testes de integração backend |
| Spec-anchored outcome check | ✅ Asserções afirmam o valor exato definido no spec, não a mera existência do campo |
| Per-layer Coverage Expectation met | ✅ Matriz de `tasks.md:22-28` cumprida: 1:1 com os 8 cenários; acessibilidade e responsividade em diretório próprio; `Tests: none` só em T1/T13 |
| Every test maps to a spec requirement | ✅ Todo `*.spec.ts` declara `E2E-NN` no cabeçalho; nenhum teste órfão. Ressalva: `docs/evidencias/cenarios-retentativa.md` atribui "E2E-06, E2E-07" (Achado 3) |
| Documented guidelines followed | ✅ `AGENTS.md`, `README.md`; voz e PT-BR conforme `coding-principles.md:70` |

Ponto forte digno de registro: os testes **não afirmam valores divergentes**. Em `sistema-visual.spec.ts:147-153` o foco é verificado por `outline-style` e `outline-width` (canônicos), mas **não** por `outline-color`, porque a cor medida diverge de `DESIGN.md`. Afirmar o valor implementado teria transformado o defeito em contrato. Essa é a decisão correta e é rara.

---

## Edge Cases

- [x] **Dado sintético alterado por execução anterior → falha clara, nunca resultado parcial**: `suporte/cenario.ts:16` restaura antes de cada cenário; `suporte/api.ts:114-118` lança erro nomeando estado observado e marcos. Comprovado empiricamente pela Mutação 2, cuja falha veio como diagnóstico legível, não como timeout obscuro.
- [x] **Suíte duas vezes seguidas → resultados idênticos**: `suporte/cenario.ts:11-13` (wipe catalog-driven, AD-014); `cenarios/retentativa.spec.ts:126-138` encerra a execução aberta para não bloquear o cenário seguinte (DW-002). Verificado empiricamente: a execução do autor e a reexecução independente deste Verifier deram os mesmos 43 verdes.
- [x] **Critério WCAG não atendido por limitação documentada → registrado, não silenciado**: `acessibilidade/checklist-manual.spec.ts:21-39`, `acessibilidade/axe.spec.ts:14-18`, `responsividade/sistema-visual.spec.ts:15-35`. Registrado — com a ressalva de propagação do Achado 2.

---

## Gate Check

- **Gate command**: `uv run --directory src/backend pytest && npm test --prefix src/frontend -- --run && npx playwright test` (Playwright invocado de dentro de `testes-e2e/` via `npm test`, conforme `tasks.md:39-42`)
- **Result**: **1582 passed, 0 failed, 0 skipped**
  - Backend `pytest`: **1095 passed** (16 linhas de progresso, zero `F`/`E`/`s`)
  - Frontend `vitest`: **444 passed** (46 arquivos)
  - Playwright: **43 passed** em 2.1m, exit 0
- **Test count before feature**: 1095 backend + 441 frontend = 1536 (Handoff de 5.7 em `.specs/STATE.md:128`)
- **Test count after feature**: 1095 + 444 + 43 = 1582
- **Delta**: **+46** (+3 `vitest` de regressão das correções inline, +43 E2E). Nenhum teste removido, nenhuma asserção enfraquecida.
- **Skipped tests**: nenhum
- **Failures**: nenhuma

**T13 reexecutado ponta a ponta por este Verifier**, em worktree descartável, com `docs/evidencias/` apagado antes: `python3 scripts/gerar_evidencias.py` → **exit 0**, 14 arquivos produzidos, e os **13 relatórios por cenário reproduziram byte a byte os arquivos commitados** (só `README.md` difere, no carimbo de tempo). As evidências commitadas não estão obsoletas nem fabricadas; todo `file:line` citado confere com o arquivo atual.

---

## Desvios (SPEC_DEVIATION) — pré-existentes e corretamente documentados

Confirmados como ainda exatos, não recontados como lacunas novas:

1. **Superfícies de Administrador dos Épicos 2–4 não montadas em `App.tsx`** — 4 das 7 evidências de E2E-08, e as tentativas/snapshot de E2E-05, são alcançadas pela API REST pública em vez da interface. Declarado em `tasks.md:220-223` (T7), `tasks.md:289-294` (T10), nos cabeçalhos de `evidencias-localizaveis.spec.ts:11-17`, `contingencia-inmet.spec.ts:13-16`, `retentativa.spec.ts:13-14`, `axe.spec.ts:14-18`, e em `.specs/STATE.md:131`. O AC diz "sem editar arquivos ou banco", e a API REST pública satisfaz isso literalmente.
2. **Variante literal `OPENAI_API_KEY` ausente** — coberta por integração backend (`src/backend/testes/test_preflight_ia_api.py`), não pelo E2E. Justificada em `indisponibilidade-openai.spec.ts:15-23`: o AC é disjuntivo e as duas causas cobertas atravessam o mesmo caminho de código.
3. **`PainelSegurado` como componente de composição** (5.7) — pré-existente, fora do escopo desta validação.

---

## Achados (nenhum bloqueante)

### Achado 1 — Comentário obsoleto descreve como aberto um defeito já corrigido (Minor)

- **Onde**: `testes-e2e/acessibilidade/checklist-manual.spec.ts:30-39`
- **O quê**: o cabeçalho diz "Refluxo da tabela de Prontidão (**defeito aberto, o teste de zoom abaixo o reprova**)" e detalha `scrollWidth` 1060 contra `clientWidth` 1024. O defeito foi corrigido em `36523bf` (`.tabela-prontidao-rolagem` com `overflow-x: auto`, rolagem nomeada conforme `EXPERIENCE.md`), e o teste de zoom (`:159`) **passa** — verificado nesta rodada.
- **Impacto**: documentação ativamente enganosa no artefato que a História 5.9 vai consumir; um leitor conclui que existe um defeito WCAG aberto que não existe.
- **Correção**: reescrever o item como desvio **resolvido**, citando `36523bf`.

### Achado 2 — A tabela de desvios não chega a `docs/evidencias/` (Minor)

- **Onde**: `scripts/gerar_evidencias.py:124` (`titulo = linhas[0]`) vs. `tasks.md:319` e `tasks.md:340`
- **O quê**: T11 diz "checklist por superfície documentado no relatório — **ver `docs/evidencias/responsividade-sistema-visual.md`**" e T12 diz "checklist manual ... com todo desvio explicitamente registrado — **ver `docs/evidencias/acessibilidade-checklist-manual.md`**". Esses dois arquivos contêm apenas título, requisitos, status e a tabela de casos. A tabela dos 9 desvios de token e a checklist manual por fluxo vivem só nos cabeçalhos dos `.spec.ts`, porque o extrator aproveita apenas a primeira linha do comentário.
- **Impacto**: o Edge Case de `spec.md:116` continua satisfeito por encadeamento (o relatório cita o arquivo de teste, que carrega os desvios), mas o artefato nomeado nos "Done when" não carrega o conteúdo prometido.
- **Correção**: propagar o corpo do cabeçalho (ou ao menos as seções `##`) para o relatório gerado.

### Achado 3 — Atribuição de requisito por varredura de texto (Minor)

- **Onde**: `scripts/gerar_evidencias.py:125` (`PADRAO_CABECALHO_REQUISITO.findall(corpo)`)
- **O quê**: `docs/evidencias/cenarios-retentativa.md` atribui "E2E-06, E2E-07" porque o cabeçalho de `retentativa.spec.ts:5` menciona E2E-06 em prosa ("mesmo caminho de E2E-06"). O cenário comprova E2E-07.
- **Impacto**: rastreabilidade levemente inflada no índice de evidências.
- **Correção**: declarar os requisitos numa linha própria (ex.: `Requisitos: E2E-07`) em vez de varrer o comentário inteiro.

### Achado 4 — Commit não atômico com mensagem que não descreve o trabalho (Minor, processo)

- **Onde**: `c3a3c21` "mudanca de porta de 5173 para 5151"
- **O quê**: esse commit introduz os quatro arquivos de T11/T12 (`responsividade/viewports.spec.ts`, `responsividade/sistema-visual.spec.ts`, `acessibilidade/axe.spec.ts`, `acessibilidade/checklist-manual.spec.ts`, ~820 linhas), sem mencioná-los. `tasks.md` exige um commit atômico por task.
- **Impacto**: `git log` não permite localizar quando T11/T12 entraram; a sincronização retroativa dos checkboxes em `bd3bbc6` é consequência disso.
- **Correção**: nada a desfazer no histórico. Vale a lição para as próximas histórias.

---

## Outcome dos Achados (pós-PASS, mesma sessão)

Verdito já era **PASS** — nenhum destes era bloqueante. Corrigidos por serem baratos e porque o artefato `docs/evidencias/` é justamente o que a História 5.9 vai consumir; não foi necessária uma nova rodada de Verifier (o PASS original se mantém, este é um refinamento pós-veredito, não um fix→re-verify sobre um FAIL).

- **Achado 1 — fixed.** `testes-e2e/acessibilidade/checklist-manual.spec.ts:29-33` reescrito: o refluxo da tabela de Prontidão agora é descrito como corrigido em `36523bf`, não como defeito aberto.
- **Achado 2 — fixed.** `scripts/gerar_evidencias.py` agora captura o corpo inteiro do cabeçalho (não só a primeira linha) em `RelatorioCenario.contexto` e o `escrever_relatorio_cenario` grava uma seção "## Contexto do cenário" com ele. `docs/evidencias/responsividade-sistema-visual.md` e `docs/evidencias/acessibilidade-checklist-manual.md` agora carregam as tabelas de desvio e a checklist manual, não só título/status.
- **Achado 3 — fixed.** `extrair_cabecalho` agora extrai `requisitos` só da linha de título (`PADRAO_CABECALHO_REQUISITO.findall(titulo)`), não do corpo inteiro. `docs/evidencias/cenarios-retentativa.md` agora atribui só `E2E-07`.
- **Achado 4 — no_change_needed.** Nada a desfazer no histórico; é uma lição de processo para as próximas histórias, já registrada em `.specs/LESSONS.md`.

**Reverificação**: `python3 scripts/gerar_evidencias.py` reexecutado do zero após as três correções — **exit 0**, 1582/1582 testes verdes (1095 backend + 444 frontend + 43 Playwright), os 13 relatórios regenerados com o conteúdo corrigido. `validate_spec.py`/`validate_tasks.py` sobre a feature: 0 erros.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| E2E-01 | Implementing | ✅ Verified |
| E2E-02 | Implementing | ✅ Verified |
| E2E-03 | Implementing | ✅ Verified |
| E2E-04 | Implementing | ✅ Verified |
| E2E-05 | Implementing | ✅ Verified |
| E2E-06 | Implementing | ✅ Verified |
| E2E-07 | Implementing | ✅ Verified |
| E2E-08 | Implementing | ✅ Verified |
| E2E-09 | Implementing | ✅ Verified |
| E2E-10 | Implementing | ✅ Verified |
| E2E-11 | Implementing | ⚠️ Verified com desvio documentado (9 tokens divergentes registrados; correção pertence às histórias de interface) |
| E2E-12 | Implementing | ✅ Verified (superfícies montadas) |
| E2E-13 | Implementing | ✅ Verified |

---

## Summary

**Overall**: ✅ Ready

**Spec-anchored check**: 13/13 ACs com evidência `file:line`; 12 casam integralmente com o desfecho do spec, 1 (E2E-11) parcial com desvio medido e registrado
**Sensor**: 3/3 mutantes mortos
**Gate**: 1582 passed, 0 failed, 0 skipped

**O que funciona**:

- Os 8 cenários de negócio rodam ponta a ponta contra backend e frontend reais, em Chromium, sem nenhuma chamada de rede externa (INMET e OpenAI redirecionados ao dublê local em `suporte/processos.ts:35-38`).
- As asserções são de desfecho, não de presença: justificativas literais, sequências exatas de marcos, contagens de chamadas ao dublê, cores computadas pelo navegador.
- O contrato OpenAPI é comparado **no processo em execução**, não só no instantâneo versionado, e as 37 rotas exercitadas são confirmadas como publicadas.
- A suíte provou seu valor durante a própria implementação: descobriu 4 defeitos reais de produção invisíveis a `vitest`/jsdom (CORS sem `PUT`, landmarks/ids duplicados, corrida na troca de segurado, transbordo da tabela de Prontidão), cada um corrigido com regressão própria.
- `gerar_evidencias.py` é reproduzível: reexecutado do zero, regenerou os 13 relatórios idênticos aos commitados.

**Problemas encontrados**: 4 achados Minor, nenhum bloqueante — comentário obsoleto sobre defeito já corrigido (Achado 1), desvios não propagados ao relatório gerado (Achado 2), atribuição de requisito inflada (Achado 3), commit não atômico (Achado 4).

**Next steps**: marcar E2E-01..E2E-13 como Verified em `spec.md`; atualizar o Handoff de `.specs/STATE.md` fechando 5.8; seguir para a História 5.9, que consome `docs/evidencias/`. Os Achados 1–3 são pequenos e ficam bem endereçados junto de 5.9, que é quem lê esses arquivos.
