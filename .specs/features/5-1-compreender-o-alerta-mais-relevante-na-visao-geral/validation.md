# História 5.1: Compreender o alerta mais relevante na visão geral — Validation

**Date**: 2026-09-05
**Spec**: `.specs/features/5-1-compreender-o-alerta-mais-relevante-na-visao-geral/spec.md`
**Diff range**: `7fd35ca..98af09d` (T1 `a01539c`, T2 `d9ff957`, T3 `3585dee`, T4 `98af09d`)
**Verifier**: independent sub-agent (author ≠ verifier), read-only sobre a árvore real

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 — `RepositorioElegibilidades.obter_mais_recente_por_segurado` | ✅ Done | 4 testes novos; ordenação e filtro `elegivel` discriminados pelo sensor |
| T2 — `ServicoAlertaSegurado` | ✅ Done | 7 testes novos; SPEC_DEVIATION declarada e verificada empiricamente (ver abaixo) |
| T3 — `GET /segurados/{id}/alerta-mais-relevante` | ✅ Done | 4 testes novos; `openapi.json` e `test_saude.py` sincronizados |
| T4 — Reescrita de `VisaoGeralSegurado.tsx` | ⚠️ Partial | 5 estados implementados, mas 3 comportamentos ficaram sem teste discriminante (M6, M7, M8) e a cópia do estado vazio afirma uma navegação que ainda não existe |

---

## Spec-Anchored Acceptance Criteria

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| **VISAO-01** — abrir a Visão geral com alerta ativo exibe *tipo* | `chuva_intensa` renderizado como tipo do evento | `src/backend/testes/test_alerta_segurado.py:143` — `assert alerta.evento_tipo is TipoEventoMeteorologico.CHUVA_INTENSA`; `src/frontend/src/funcionalidades/segurado/VisaoGeralSegurado.test.tsx:86` — `findByRole('heading', { level: 2, name: 'Chuva intensa' })` | ✅ PASS |
| **VISAO-01** — … *severidade* | critério de risco observado (valor + justificativa) | `test_alerta_segurado.py:149` — `assert "62.5" in alerta.severidade`; `VisaoGeralSegurado.test.tsx:87` — `getByText(/72.5 mm/)` | ✅ PASS |
| **VISAO-01** — … *período* | `periodo_inicio`/`periodo_fim` do evento visíveis na interface | `test_alerta_segurado.py:144-145` — `assert alerta.periodo_inicio == evento.periodo_inicio` (DTO). **Nenhuma asserção de interface**: remover o parágrafo `Previsto entre … e … em …` de `VisaoGeralSegurado.tsx:170-173` mantém os 335 testes verdes (mutante M8) | ❌ GAP (camada de interface) |
| **VISAO-01** — … *localização* | `evento.area` (`9990001`) | `test_alerta_segurado.py:146` — `assert alerta.localizacao == AREA`; `VisaoGeralSegurado.test.tsx:88` — `getAllByText(/9990001/).length > 0` | ✅ PASS |
| **VISAO-01** — … *impactos esperados* | `regra.cobertura_exigida` = `alagamento` | `test_alerta_segurado.py:147` — `assert alerta.impactos_esperados == ("alagamento",)`; `VisaoGeralSegurado.test.tsx:89` — `getByText('alagamento')` | ✅ PASS |
| **VISAO-01** — … *recomendações curtas, práticas e coerentes* | mesmas `ORIENTACOES_POR_EVENTO` do `ContextoAgente` (3.1) | `test_alerta_segurado.py:148` — `assert alerta.recomendacoes == ORIENTACOES_POR_EVENTO[TipoEventoMeteorologico.CHUVA_INTENSA]`; `VisaoGeralSegurado.test.tsx:91` — `getByText('Evite áreas alagadas e não atravesse ruas com água corrente.')` | ✅ PASS |
| **VISAO-02** — procedência visível | `real_inmet` rotulado "Observação real (INMET)", nunca sintético | `test_alerta_segurado.py:150` — `assert alerta.origem is ProvenienciaEvento.REAL_INMET`; `VisaoGeralSegurado.test.tsx:101-102` — `getAllByText(/Observação real \(INMET\)/).length > 0` **e** `queryByText(/sintétic/i)).not.toBeInTheDocument()` | ✅ PASS |
| **VISAO-02** — origem sintética nunca confundida com real | `sintetico` rotulado "Cenário demonstrativo (sintético)", nunca "Observação real" | `test_alerta_segurado.py:164` — `assert alerta.origem is ProvenienciaEvento.SINTETICO`; `VisaoGeralSegurado.test.tsx:111-112` — `getAllByText(/sintétic/i).length > 0` **e** `queryByText(/Observação real/)).not.toBeInTheDocument()` | ✅ PASS |
| **VISAO-02** — horário dos dados visível | `instante_observado` do evento exibido | `test_alerta_segurado.py:151` — `assert alerta.instante_observado == evento.instante_observado` (DTO). **Nenhuma asserção de interface**: remover `<dt>Horário do dado</dt><dd>{alerta.instanteObservado}</dd>` (`VisaoGeralSegurado.tsx:213-215`) mantém os 335 testes verdes (mutante M8) | ❌ GAP (camada de interface) |
| **VISAO-03** — linguagem esclarece que a comunicação é privada, não substitui autoridades e não confirma cobertura | as três ressalvas presentes no texto | `VisaoGeralSegurado.test.tsx:121` — `findByText(/não substitui as autoridades competentes/)`; `:123` — `getByText(/não confirma cobertura ou indenização/)` | ✅ PASS |
| **VISAO-03** — linguagem "objetiva, não alarmista e orientada à segurança" | não há valor/estado preciso definido na spec | — | ⚠️ Spec-precision gap |
| **VISAO-04** — sem alerta relevante → estado vazio explicativo | serviço devolve `None`; API devolve `200` com `{"alerta": null}`; interface mostra estado vazio | `test_alerta_segurado.py:129` — `assert contexto.servico.obter_mais_relevante(SEGURADO_ID) is None`; `test_alerta_segurado_api.py:109-110` — `assert resposta.status_code == 200` / `assert resposta.json() == {"alerta": None}`; `VisaoGeralSegurado.test.tsx:167` — `findByRole('heading', { name: 'Nenhum alerta relevante no momento' })` | ✅ PASS |
| **VISAO-04** — sem inventar risco ou recomendação | nenhum bloco de alerta renderizado no estado vazio | `VisaoGeralSegurado.test.tsx:169` — `queryByRole('heading', { level: 2, name: 'Chuva intensa' })).not.toBeInTheDocument()` | ✅ PASS |
| **VISAO-04** — Apólice, Comunicados e Meus Dados continuam acessíveis | as três superfícies alcançáveis pela navegação a partir do estado vazio | Nenhuma evidência. Pior: nenhuma das três existe na navegação do perfil Segurado — `src/frontend/src/App.test.tsx:129-131` prova que a navegação do Segurado tem **somente** "Visão geral". A cópia fixa em `VisaoGeralSegurado.tsx:133-136` ("Apólice, Comunicados e Meus Dados continuam disponíveis pela navegação") afirma algo hoje falso | ❌ GAP |
| **VISAO-05** — fonte degradada → snapshot com caráter apenas informativo | `fonte_degradada = true` quando a última sincronização da área falhou ou precisou de >1 tentativa; `false` caso contrário e sempre para evento sintético | `test_alerta_segurado.py:190` — `assert alerta.fonte_degradada is True` (estado `FALHA`); `:224` — `is True` (2 tentativas); `:255` — `is False` (1 tentativa); `:267` — `is False` (sem sincronização); `:165` — `is False` (sintético); `test_alerta_segurado_api.py:99` — `assert corpo["alerta"]["fonte_degradada"] is False` | ✅ PASS |
| **VISAO-05** — interface não sugere alerta novo a partir do snapshot | aviso com caráter "apenas informativo" | `VisaoGeralSegurado.test.tsx:146` — `findByText(/Fonte meteorológica degradada/)`; `:147` — `getByText(/apenas informativo/)`; `:156` — `queryByText(/Fonte meteorológica degradada/)).not.toBeInTheDocument()` quando operacional | ✅ PASS |
| **VISAO-05** — snapshot aparece "com sua idade" | idade do último dado visível | `VisaoGeralSegurado.tsx:152` renderiza `calcularIdade(alerta.instanteObservado)`, mas nenhum teste asserta a idade renderizada | ⚠️ Spec-precision gap (cláusula sem asserção) |
| **VISAO-06** — distinguir `Carregando`, `Alerta`, `Sem alerta`, `Contexto trocando`, `Erro` | cinco estados observáveis distintos | `VisaoGeralSegurado.test.tsx:73` — `findByText('Carregando alerta…')`; `:86` (Alerta); `:167` (Sem alerta); `:185` — `findByText('Contexto trocando…')`; `:233` — `findByRole('alert')` | ✅ PASS |
| **VISAO-06** — falha informa impacto e próxima ação | ocorrência + impacto + próxima ação no bloco de erro | `VisaoGeralSegurado.test.tsx:234-236` — `expect(alerta).toHaveTextContent('Falha ao consultar o alerta.')` / `('O alerta pode estar desatualizado.')` / `('Tente novamente.')` | ✅ PASS |
| **VISAO-06** — falha não apaga o último contexto válido (caso *Alerta*) | o alerta anterior continua visível sob o banner de erro | `VisaoGeralSegurado.test.tsx:237` — `expect((await screen.findAllByText(/AREA-VALIDA/)).length).toBeGreaterThan(0)` (mutante M5 morto) | ✅ PASS |
| **VISAO-06** — falha não apaga o último contexto válido (caso *Sem alerta*) | o estado vazio explicativo continua visível sob o banner de erro | Nenhuma evidência. `VisaoGeralSegurado.tsx:128-129` tem o ramo `(estado === 'erro' && resolvidoAoMenosUmaVez && !alerta)`, mas removê-lo mantém os 335 testes verdes (mutante M7) | ❌ GAP |
| **VISAO-07** — teclado preserva ordem, foco e nomes | botão de nova tentativa alcançável por `Tab` e ativável por `Enter` | `VisaoGeralSegurado.test.tsx:280` — `expect(screen.getByRole('button', { name: 'Tentar novamente' })).toHaveFocus()`; `:283` — heading recuperado após `{Enter}` | ✅ PASS |
| **VISAO-07** — zoom 200% preserva informação essencial | nenhuma informação essencial desaparece a 200% | `VisaoGeralSegurado.test.tsx:286-307` reduz `window.innerWidth` para 640; jsdom não faz layout nem zoom real, então a asserção prova presença no DOM, não legibilidade sob zoom | ⚠️ Spec-precision gap (ambiente não simula o critério; ver lição L-006) |
| **VISAO-07** — "alvos mínimos" preservados | tamanho mínimo de alvo não numerado na spec, nenhuma asserção | — | ⚠️ Spec-precision gap |
| **VISAO-08** — nenhuma informação essencial depende só de cor/ícone/mapa/hover | rótulo textual acompanha o ícone de proveniência (`aria-hidden`) | `VisaoGeralSegurado.test.tsx:316` — `getAllByText(/Cenário demonstrativo \(sintético\)/).length > 0`; ícones marcados `aria-hidden="true"` em `VisaoGeralSegurado.tsx:150,158,164,219` | ✅ PASS |

**Status**: ❌ Gaps presentes (4 ACs/cláusulas sem evidência) + ⚠️ 4 spec-precision gaps

---

## Edge Cases

- [x] **Elegível para mais de um evento → mostra o mais recente**: `src/backend/testes/test_repositorio_elegibilidade.py:576-577` — `assert resultado.id == id_novo` após forçar `criado_em` `2020-01-01` vs `2030-01-01`. Mutante M3 (`DESC`→`ASC`) morto.
- [ ] **Snapshot degradado sem elegibilidade associada → "sem alerta", não "alerta degradado"**: parcialmente coberto. `test_alerta_segurado.py:129` prova `None` sem elegibilidade, mas nenhum teste semeia uma sincronização em estado `falha` **junto com** a ausência de elegibilidade — o caminho exato do edge case. Estruturalmente garantido (`obter_mais_relevante` retorna antes de tocar em sincronizações), mas sem evidência dedicada.
- [ ] **Troca de contexto permanece em `Contexto trocando` sem misturar dado antigo e novo**: metade coberta. `VisaoGeralSegurado.test.tsx:185-186` prova que `AREA-ANTIGA` some durante a troca ✅. A outra metade — descartar uma resposta antiga que chega depois — é testada em `:192-210`, mas a asserção usa `await Promise.resolve()` (um único microtask), curto demais para o React aplicar a atualização obsoleta: o mutante M6 (remoção do guard de token de requisição) **sobrevive**.

---

## Discrimination Sensor

Scratch isolado: `git worktree add /tmp/verify-5-1-scratch HEAD` (e `/tmp/verify-5-1-scratch2` para M8), descartado com `git worktree remove --force`. Baseline `git status --porcelain` vazio antes e depois — isolamento confirmado.

| # | File:line | Description | Killed? |
| --- | --- | --- | --- |
| M1 | `aplicacao/alerta_segurado.py:220` | `return len(tentativas) > 1` → `>= 1` | ✅ Killed (`test_fonte_operacional_quando_ultima_sincronizacao_concluiu_de_primeira`) |
| M2 | `aplicacao/alerta_segurado.py:192-193` | Guard de proveniência invertido (`is not REAL_INMET → return False` vira `is REAL_INMET → return True`) | ✅ Killed (4 testes, incluindo `test_alerta_segurado_api.py:99`) |
| M3 | `persistencia/repositorio_elegibilidade.py:246` | `ORDER BY e.criado_em DESC` → `ASC` | ✅ Killed (`test_obter_mais_recente_por_segurado_devolve_a_mais_recente_entre_varias`) |
| M4 | `adaptadores/http/alerta_segurado.py:171-172` | Ausência de alerta devolve `404` em vez de `200 {"alerta": null}` | ✅ Killed (2 testes de API) |
| M5 | `VisaoGeralSegurado.tsx:140,198` | `(estado === 'alerta' \|\| (estado === 'erro' && resolvidoAoMenosUmaVez))` → `estado === 'alerta'` (apaga o alerta válido no erro) | ✅ Killed (`:237`) |
| M6 | `VisaoGeralSegurado.tsx:80` | Removido `if (requisicao !== requisicaoAtualRef.current) return` (guard de resposta obsoleta) | ❌ **Survived** — 17/17 verdes. Trocar `await Promise.resolve()` (`:207`) por `await new Promise((r) => setTimeout(r, 50))` mata o mutante, provando que a asserção só passa por timing curto demais |
| M7 | `VisaoGeralSegurado.tsx:128-129` | Removido o ramo `(estado === 'erro' && resolvidoAoMenosUmaVez && !alerta)` (apaga o estado vazio no erro) | ❌ **Survived** — 17/17 verdes |
| M8 | `VisaoGeralSegurado.tsx:170-173` e `:213-215` | Removidos o parágrafo `Previsto entre … e … em …` e o `<dd>{alerta.instanteObservado}</dd>` | ❌ **Survived** — suíte completa 335/335 verdes |

**Sensor depth**: P0-full (8 mutações, cobrindo repositório, caso de uso, rota HTTP e componente)
**Result**: 5/8 killed — ❌ FAIL

---

## Verificação independente da SPEC_DEVIATION (T2)

`aplicacao/alerta_segurado.py:14-17` declara que `RepositorioContextosAgente` e `RepositorioAvaliacoesRisco` (listados em `design.md:70`) não são usados porque a persona semeada da demonstração (`SEGURADO_PADRAO`) só tem uma linha de `elegibilidades_historicas` com `execucao_id IS NULL` e `criterios = '[]'`.

Verifiquei isso empiricamente (script descartável no worktree scratch, banco temporário migrado + `SemeadorDadosSinteticos.semear()`):

```
AlertaSegurado(evento_tipo=CHUVA_INTENSA,
  severidade='72.5 mm — Intensidade observada atinge o limiar de 50.0 mm (fronteira inclusiva).',
  periodo_inicio=2026-03-10 06:00, periodo_fim=2026-03-10 18:00, localizacao='9990001',
  impactos_esperados=('alagamento',), recomendacoes=(3 orientações de chuva intensa),
  origem=SINTETICO, instante_observado=2026-03-09 18:00, fonte_degradada=False)
```

A deviation é **materialmente justificada**: a persona semeada recebe um alerta completo e correto pela abordagem escolhida.

**Porém, essa justificativa não está protegida por nenhum teste.** Nenhum teste do repositório executa o `SemeadorDadosSinteticos` contra `ServicoAlertaSegurado`/`SEGURADO_PADRAO` — a evidência mais próxima é `test_repositorio_elegibilidade.py:580-607` (nível de repositório, linha semeada com `execucao_id` nulo). Se o semeador mudar, nada quebra.

---

## Code Quality

| Principle | Status |
| --- | --- |
| Minimum code | ✅ |
| Surgical changes | ✅ — apenas 1 método novo no repositório, 1 caso de uso, 1 roteador, 1 cliente HTTP, 1 componente reescrito |
| No scope creep | ✅ — `App.test.tsx`, `test_saude.py`, `openapi.json`, `tipos-gerados.ts` e `App.css` mudaram só pelo acoplamento inevitável da rota/componente novos; `openapi.json` e `tipos-gerados.ts` são puramente aditivos (0 linhas removidas no diff) |
| Matches patterns | ✅ — Protocols de porta, `problem+json`, `criar_roteador(configuracao)`, cliente HTTP tipado por `tipos-gerados`, todos idênticos a 4.1/4.2/4.4 |
| Spec-anchored outcome check | ❌ — 4 cláusulas de AC sem asserção que case com o resultado definido na spec (período/horário na interface, navegação do estado vazio, preservação do estado vazio no erro) |
| Per-layer Coverage Expectation | ⚠️ — repositório/aplicação/rota atendem a matriz (com/sem resultado, todos os branches, feliz + sem alerta + degradada + `422`); o componente cobre os 5 estados mas deixa 3 comportamentos sem discriminação |
| Every test maps to a spec requirement — no unclaimed tests | ✅ — os 30 testes novos mapeiam para VISAO-01..08, edge cases ou "Done when" de T1..T4 |
| Documented guidelines followed | ✅ — `AGENTS.md` (somente dados sintéticos: fixtures usam `9990001`, `A701`, UUIDs gerados); demais convenções por defaults fortes do repositório |

### Observação adicional de honestidade (AD-9)

`VisaoGeralSegurado.tsx:133-136` afirma no estado vazio que "Apólice, Comunicados e Meus Dados continuam disponíveis pela navegação". Essas três superfícies **não existem** — `App.test.tsx:129-131` prova que a navegação do perfil Segurado hoje tem somente "Visão geral". Uma história cujo propósito declarado é remover texto fixo enganoso introduziu um texto fixo que afirma algo falso sobre a própria navegação.

---

## Gate Check

- **Gate command (backend)**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`
- **Result**: 978 passed, 0 failed, 0 skipped · ruff `All checks passed!` (exit 0) · pyright `0 errors, 0 warnings, 0 informations` (exit 0)
- **Gate command (frontend)**: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**: 335 passed / 34 arquivos, 0 failed (exit 0) · lint exit 0 (apenas warnings `react(set-state-in-effect)` pré-existentes em arquivos fora deste diff) · build exit 0
- **Test count before feature**: backend 963 · frontend 320
- **Test count after feature**: backend 978 · frontend 335
- **Delta**: +15 backend (7 caso de uso, 4 API, 4 repositório) · +15 frontend (`VisaoGeralSegurado.test.tsx` passou de 2 para 17 testes)
- **Skipped tests**: nenhum
- **Failures**: nenhuma
- **Integridade**: nenhuma contagem caiu; nenhuma asserção existente foi enfraquecida. `App.test.tsx:133` trocou `getByRole` por `findByRole` e o título estático pelo título real — mudança exigida pela assincronia nova, não um enfraquecimento.

---

## Fix Plans

### Fix 1 — Endurecer a asserção do descarte de resposta obsoleta (Blocker)

- **Root cause**: `VisaoGeralSegurado.test.tsx:207` usa `await Promise.resolve()`, um único microtask — o React não chega a aplicar a atualização obsoleta, então a asserção de `:208` passa mesmo sem o guard de token.
- **Fix task**: substituir por `await waitFor(...)` ou `await new Promise((r) => setTimeout(r, 50))` antes de `expect(screen.queryAllByText(/AREA-ANTIGA/).length).toBe(0)`. Confirmado no scratch: com essa troca o mutante M6 morre.
- **Verify**: remover `if (requisicao !== requisicaoAtualRef.current) return` de `VisaoGeralSegurado.tsx:80` num scratch e confirmar que o teste falha.
- **Done when**: M6 morto.
- **Priority**: Blocker (a única proteção do edge case "nunca misturar dado do segurado anterior com o novo" é vazia hoje).

### Fix 2 — Testar a preservação do estado vazio sob erro (Major)

- **Root cause**: nenhum teste resolve `null` (Sem alerta) e depois falha uma nova consulta; o ramo `VisaoGeralSegurado.tsx:128-129` nunca é exercitado.
- **Fix task**: adicionar um teste em `describe('estado Erro (VISAO-06)')` que mocka `null` na primeira chamada, rerenderiza com outro `seguradoId` rejeitando, e asserta que o heading "Nenhum alerta relevante no momento" **continua presente** junto com o `role="alert"`.
- **Verify**: mutante M7 (remoção do ramo) passa a matar.
- **Priority**: Major.

### Fix 3 — Assertar período e horário renderizados (Major)

- **Root cause**: nenhum teste de interface cita `periodoInicio`/`periodoFim`/`instanteObservado`; `getAllByText(/9990001/)` continua encontrando a localização no painel lateral mesmo sem o parágrafo do período.
- **Fix task**: assertar o texto do período (`/Previsto entre/` + os dois instantes) e o valor do `<dd>` de "Horário do dado" nos testes de VISAO-01/02.
- **Verify**: mutante M8 passa a matar.
- **Priority**: Major (são dois substantivos explícitos do AC).

### Fix 4 — Corrigir a cópia do estado vazio sobre navegação (Major)

- **Root cause**: o texto afirma que Apólice, Comunicados e Meus Dados "continuam disponíveis pela navegação"; nenhuma das três existe na navegação do perfil Segurado (`App.test.tsx:129-131`).
- **Fix task**: ou reescrever a cópia para descrever apenas o que existe hoje, ou registrar em `spec.md`/`STATE.md` que a cláusula de VISAO-04 só é satisfazível depois de 5.2/5.3/5.5 e marcar VISAO-04 como parcialmente verificada.
- **Verify**: um teste que asserta que a cópia do estado vazio não promete superfícies inexistentes.
- **Priority**: Major (viola a própria premissa de honestidade da história e AD-9).

### Fix 5 — Ancorar a SPEC_DEVIATION num teste (Minor)

- **Root cause**: a justificativa da deviation (a persona semeada recebe alerta completo sem `avaliacoes_risco`/`contextos_agente`) foi confirmada empiricamente pelo Verificador, mas nenhum teste do repositório a protege.
- **Fix task**: adicionar em `test_alerta_segurado.py` um teste que roda `SemeadorDadosSinteticos.semear()` e asserta que `obter_mais_relevante(SEGURADO_PADRAO)` devolve severidade, período, localização, impactos, recomendações e `origem is SINTETICO`.
- **Priority**: Minor.

### Fix 6 — Cobrir o edge case do snapshot degradado sem elegibilidade (Minor)

- **Fix task**: teste que semeia uma sincronização em `FALHA` para a área **sem** nenhuma elegibilidade do segurado e asserta `obter_mais_relevante(...) is None`.
- **Priority**: Minor.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| VISAO-01 | Implementing | ❌ Needs Fix (período sem asserção de interface — Fix 3) |
| VISAO-02 | Implementing | ❌ Needs Fix (horário sem asserção de interface — Fix 3) |
| VISAO-03 | Implementing | ✅ Verified |
| VISAO-04 | Implementing | ❌ Needs Fix (navegação prometida inexistente — Fix 4) |
| VISAO-05 | Implementing | ✅ Verified |
| VISAO-06 | Pending | ❌ Needs Fix (estado vazio não preservado sob erro — Fix 2) |
| VISAO-07 | Implementing | ✅ Verified (zoom 200% marcado como spec-precision gap: jsdom não simula) |
| VISAO-08 | Implementing | ✅ Verified |

---

## Summary

**Overall**: ❌ Not Ready

**Spec-anchored check**: 18/22 cláusulas de AC casaram com o resultado definido na spec · 4 gaps · 4 spec-precision gaps
**Sensor**: 5/8 mutantes mortos (M6, M7, M8 sobreviveram)
**Gate**: backend 978 passed / ruff 0 / pyright 0 · frontend 335 passed / lint 0 / build 0

**What works**:
- A camada backend é sólida: ordenação, filtro `elegivel`, guard de proveniência, limiar de tentativas e o contrato `200 {"alerta": null}` (nunca `404`) foram todos discriminados pelo sensor.
- A SPEC_DEVIATION do T2 é materialmente correta: verifiquei de forma independente que a persona semeada recebe um alerta completo pela abordagem escolhida.
- A rotulagem de origem real vs. sintética — o núcleo de honestidade da história — é assertada nos dois sentidos, com asserções negativas (`not.toBeInTheDocument()`) em ambos.
- O mockup estático foi de fato eliminado (`AUTO-DEMO-001`, "Campinas (SP)", "Há chuva forte…" provados ausentes).

**Issues found**: os 6 Fix Plans acima, com Fix 1 (guard de resposta obsoleta sem teste real) como bloqueador e Fix 4 (cópia que promete navegação inexistente) como o achado mais próximo do espírito da história.

**Next steps**: rotear Fix 1-4 como fix tasks para um implementador e re-despachar o Verificador (iteração 1 de no máximo 3). Fix 5 e 6 podem entrar na mesma rodada.
