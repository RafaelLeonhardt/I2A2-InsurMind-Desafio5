# História 5.1: Compreender o alerta mais relevante na visão geral — Validation

**Date**: 2026-09-05
**Result**: ✅ PASS (estado final, ver "Fechamento pós-escalação")
**Status final**: ✅ **PASS** — ver "Fechamento pós-escalação" ao final deste arquivo. O corpo abaixo é o relatório da rodada 3 do Verifier independente, cujo veredito histórico era negativo com 7/9 mutantes mortos; a correção dos 2 sobreviventes (M14/M15) e o fechamento foram feitos pelo orquestrador, com autorização explícita do usuário, fora do laço de 3 iterações (`validate.md` §8 permite exatamente essa saída: "aceitar o risco... ou autorizar uma correção pontual fora do laço").
**Round**: 3 — **iteração final** do laço fix→re-verify (limite de 3 de `validate.md` §8)
**Spec**: `.specs/features/5-1-compreender-o-alerta-mais-relevante-na-visao-geral/spec.md`
**Tasks**: `.specs/features/5-1-compreender-o-alerta-mais-relevante-na-visao-geral/tasks.md`
**Diff range (feature ponta a ponta)**: `7fd35ca..HEAD` (`743de0a`)
**Diff escrutinado nesta rodada**: `85bc10a..HEAD` (`743de0a` — Fixes 1-4 da rodada 2)
**Verifier**: sub-agente independente (author ≠ verifier), read-only sobre a árvore real; todas as mutações em worktree descartável

> **Este arquivo substitui os relatórios das rodadas 1 e 2.** Rodada 1 (`FAIL`, 5/8 mortos) e rodada 2 (`FAIL`, 6/8 mortos) estão no histórico (`git show 85bc10a -- .specs/features/5-1-.../validation.md` e o commit anterior). Este relatório é **auto-contido**: a tabela de ACs foi re-derivada do zero, com `file:line` conferidos na árvore atual.

---

## Veredito da rodada 3

**Veredito desta rodada (histórico — ver "Fechamento pós-escalação" para o estado final)**: ❌ era FAIL na rodada 3 — iteração 3 de 3 esgotada, escalado ao usuário e fechado depois (ver seção final).

Os **4 fixes da rodada 2 funcionaram de verdade**, comprovados empiricamente e não pela mensagem de commit: M9, M11 e as duas lacunas Minor agora morrem sob reinjeção. VISAO-06 fica ✅ Verified e o contrato HTTP dos campos temporais passa a ser discriminado.

Porém o passe final de sensor, aplicado ao **único ponto do roteador HTTP que nenhuma rodada anterior havia estressado** (a tradução dos campos `origem` e `fonte_degradada` para o corpo público), encontrou **2 mutantes sobreviventes**:

- **M14** — `origem=str(alerta.origem)` → `origem="real_inmet"` fixo: **980/980 testes de backend continuam verdes**. Um evento sintético seria servido pela API como `real_inmet` e a Visão geral renderizaria "Observação real (INMET)" — exatamente a confusão que VISAO-02 proíbe em letra explícita e que a AD-9 do projeto trata como violação de honestidade.
- **M15** — `fonte_degradada=alerta.fonte_degradada` → `False` fixo: **980/980 verdes**. Nenhum teste jamais chama a rota com a fonte degradada, embora a **matriz de cobertura da própria `tasks.md`** exija do roteador HTTP "caminho feliz + sem alerta + **fonte degradada**".

Estes não são goalposts novos do Verificador: M15 é um item de cobertura **planejado na `tasks.md` desde a fase Tasks e nunca entregue**, e M14 é a mesma classe do M11 que a rodada 2 classificou como Major e que acabou de ser corrigido — só que no campo vizinho da mesma função. Por `validate.md` §5 ("mutantes sobreviventes → fix tasks antes de marcar a feature como pronta"), a história não pode ser fechada.

**Importante para a decisão do usuário**: nenhum destes é um **defeito de produto**. O código de produção está correto; o que falta é **discriminação de teste** numa fronteira. O conserto é pequeno e localizado (um arquivo de teste, ver Fix 1/Fix 2 abaixo).

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 — `RepositorioElegibilidades.obter_mais_recente_por_segurado` | ✅ Done | Ordenação `DESC` + filtro `elegivel` discriminados: M3 reconfirmado morto nesta rodada |
| T2 — `ServicoAlertaSegurado` | ✅ Done | Todos os branches cobertos 1:1 com VISAO-01..05; SPEC_DEVIATION ancorada em execução (M10, rodada 2) |
| T3 — `GET /segurados/{id}/alerta-mais-relevante` | ⚠️ Partial | Campos temporais/conteúdo agora assertados (M11 morto). Faltam os dois campos de **procedência/estado da fonte**: M14 e M15 sobrevivem; a matriz de cobertura exige o caso "fonte degradada" nesta camada e ele não existe |
| T4 — Reescrita de `VisaoGeralSegurado.tsx` | ✅ Done | Os 5 estados discriminados, incluindo a primeira carga que falha (M9 morto). Cópia do estado vazio protegida por regressão (M12 morto); idade do snapshot assertada (M13 morto) |

---

## Verificação dos 4 Fixes da rodada 2 (real, não cosmético)

| Fix | O que a rodada 2 pediu | O que aterrissou | Prova empírica (rodada 3) |
| --- | --- | --- | --- |
| **Fix 1** (Major) | Discriminar `Erro` de `Sem alerta` numa primeira carga que falha | Teste novo `VisaoGeralSegurado.test.tsx:246-268` — rejeita a **primeira** consulta, asserta `findByRole('heading', { name: 'Não foi possível carregar seu alerta' })` (`:263`) **e** `queryByRole('heading', { name: 'Nenhum alerta relevante no momento' })).not.toBeInTheDocument()` (`:266`) | ✅ **Real**. M9 reinjetado (`useState(false)`→`useState(true)` em `VisaoGeralSegurado.tsx:67`) → `1 failed \| 20 passed`, falha em `:263`. O dump do DOM do vitest mostra literalmente o mutante renderizando `<h1>Nenhum alerta relevante no momento</h1>` sob um `role="alert"` — a asserção pega exatamente o comportamento desonesto |
| **Fix 2** (Major) | Assertar o contrato público completo da rota | `test_alerta_segurado_api.py:97-109` — passa de 4 para 10 campos: `periodo_inicio` (`:104`), `periodo_fim` (`:105`), `instante_observado` (`:106`), `severidade` contém `62.5` (`:107`), `impactos_esperados` (`:108`), `recomendacoes` (`:109`) | ✅ **Real**. M11 reinjetado (`periodo_inicio`/`periodo_fim` trocados em `adaptadores/http/alerta_segurado.py:110-111`) → falha em `:104` com `assert '2026-09-04T18:00:00' == '2026-09-04T12:00:00'`. ⚠️ Ressalva abaixo |
| **Fix 3** (Minor) | Teste de regressão da cópia + deferimento formal em `spec.md` | (a) Teste novo `VisaoGeralSegurado.test.tsx:191-200` — laço sobre `['Apólice', 'Comunicados', 'Meus Dados']` com `queryByText(new RegExp(...))).not.toBeInTheDocument()` (`:198`); (b) `spec.md:103` registra o deferimento para 5.2/5.3/5.5 com a citação de `App.test.tsx:127-134` | ✅ **Real**. M12 (frase "Apólice, Comunicados e Meus Dados continuam disponíveis pela navegação" reintroduzida como `<p>` no bloco do estado vazio) → `1 failed \| 20 passed`, falha em `:198` citando o elemento reintroduzido. Deferimento confirmado presente e consistente em `spec.md:103` e `spec.md:113`. ⚠️ Ressalva abaixo |
| **Fix 4** (Minor) | Assertar a idade renderizada do snapshot degradado | `VisaoGeralSegurado.test.tsx:156-166` — `instanteObservado` fixado em `'2020-01-01T00:00:00'` (determinístico) e `getByText(/\d+ d atrás/)` (`:166`), além dos rótulos ao redor | ✅ **Real**. M13 (chamada `calcularIdade(alerta.instanteObservado)` removida de `VisaoGeralSegurado.tsx:151`, mantendo os rótulos "Fonte meteorológica degradada" e "apenas informativo") → `1 failed \| 20 passed`, falha em `:166`. A asserção depende do valor renderizado, não do texto vizinho |

### Ressalva sobre o Fix 2 (não bloqueante)

No fixture do teste, `periodo_fim` e `instante_observado` têm **o mesmo valor** (`2026-09-04T18:00:00`, `test_alerta_segurado_api.py:76-80`). Uma troca entre esses dois campos específicos não seria detectada. A troca que M11 modelava (`periodo_inicio` ↔ `periodo_fim`) **é** detectada, e a camada de aplicação distingue os três instantes (`test_alerta_segurado.py:146-147,153`). Registrado como precisão, não como gap.

### Ressalva sobre o Fix 3 (não bloqueante)

O regex é **case-sensitive**: a cópia do estado vazio diz "…associado à sua **apólice** no momento" (minúscula, `VisaoGeralSegurado.tsx:133`) e por isso passa. Uma reintrodução em minúsculas escaparia. Como a frase original usava maiúsculas e o teste pega a forma real que já existiu, é proteção suficiente para o objetivo declarado — registrado como precisão.

---

## Spec-Anchored Acceptance Criteria

Tabela re-derivada do zero nesta rodada, com todos os `file:line` conferidos na árvore atual (`743de0a`).

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| **VISAO-01** — alerta ativo exibe *tipo do evento* | `chuva_intensa` renderizado como tipo | `src/backend/testes/test_alerta_segurado.py:145` — `assert alerta.evento_tipo is TipoEventoMeteorologico.CHUVA_INTENSA`; `src/backend/testes/test_alerta_segurado_api.py:97` — `assert alerta["evento_tipo"] == "chuva_intensa"`; `src/frontend/src/funcionalidades/segurado/VisaoGeralSegurado.test.tsx:86` — `findByRole('heading', { level: 2, name: 'Chuva intensa' })` | ✅ PASS |
| **VISAO-01** — … *severidade* | critério de risco observado (valor + justificativa) | `test_alerta_segurado.py:151` — `assert "62.5" in alerta.severidade`; `test_alerta_segurado_api.py:107` — `assert "62.5" in alerta["severidade"]`; `VisaoGeralSegurado.test.tsx:87` — `getByText(/72.5 mm/)` | ✅ PASS |
| **VISAO-01** — … *período* | `periodo_inicio`/`periodo_fim` visíveis na interface | `test_alerta_segurado.py:146-147` — `assert alerta.periodo_inicio == evento.periodo_inicio` / `periodo_fim`; `test_alerta_segurado_api.py:104-105` — `assert alerta["periodo_inicio"] == "2026-09-04T12:00:00"` / `["periodo_fim"] == "2026-09-04T18:00:00"` (M11 morto); `VisaoGeralSegurado.test.tsx:88-90` — `getByText(/Previsto entre 2026-09-04T12:00:00 e 2026-09-04T18:00:00 em/)` (M8a morto) | ✅ PASS |
| **VISAO-01** — … *localização* | `evento.area` (`9990001`) | `test_alerta_segurado.py:148` — `assert alerta.localizacao == AREA`; `test_alerta_segurado_api.py:99` — `assert alerta["localizacao"] == AREA`; `VisaoGeralSegurado.test.tsx:91` — `getAllByText(/9990001/).length).toBeGreaterThan(0)` | ✅ PASS |
| **VISAO-01** — … *impactos esperados* | `regra.cobertura_exigida` = `alagamento` | `test_alerta_segurado.py:149` — `assert alerta.impactos_esperados == ("alagamento",)`; `test_alerta_segurado_api.py:108` — `assert alerta["impactos_esperados"] == ["alagamento"]`; `VisaoGeralSegurado.test.tsx:92` — `getByText('alagamento')` | ✅ PASS |
| **VISAO-01** — … *recomendações curtas, práticas e coerentes* | as mesmas `ORIENTACOES_POR_EVENTO` do `ContextoAgente` (3.1) | `test_alerta_segurado.py:150` e `:324` — `assert alerta.recomendacoes == ORIENTACOES_POR_EVENTO[CHUVA_INTENSA]`; `VisaoGeralSegurado.test.tsx:94` — `getByText('Evite áreas alagadas e não atravesse ruas com água corrente.')` | ✅ PASS |
| **VISAO-02** — procedência real visível, nunca confundida com sintética | `real_inmet` rotulado "Observação real (INMET)", nunca sintético | `test_alerta_segurado.py:152` — `assert alerta.origem is ProvenienciaEvento.REAL_INMET`; `test_alerta_segurado_api.py:98` — `assert alerta["origem"] == "real_inmet"`; `VisaoGeralSegurado.test.tsx:117` (positiva) **e** `:118` — `queryByText(/sintétic/i)).not.toBeInTheDocument()` (negativa) | ✅ PASS |
| **VISAO-02** — origem sintética **nunca** confundida com real | `sintetico` rotulado "Cenário demonstrativo (sintético)", nunca "Observação real" | Aplicação: `test_alerta_segurado.py:166` e `:325` — `assert alerta.origem is ProvenienciaEvento.SINTETICO`. Interface: `VisaoGeralSegurado.test.tsx:127` (positiva) e `:128` — `queryByText(/Observação real/)).not.toBeInTheDocument()` (negativa). **Fronteira HTTP: nenhuma evidência** — nenhum teste chama a rota com evento sintético; `adaptadores/http/alerta_segurado.py:115` pode ser fixado em `"real_inmet"` com **980/980 verdes** (M14) | ❌ GAP *(camada HTTP)* |
| **VISAO-02** — horário dos dados visível | `instante_observado` do evento exibido na interface | `test_alerta_segurado.py:153` — `assert alerta.instante_observado == evento.instante_observado`; `test_alerta_segurado_api.py:106` — `assert alerta["instante_observado"] == "2026-09-04T18:00:00"`; `VisaoGeralSegurado.test.tsx:106-108` — `getByText('Horário do dado').closest('div')` → `toHaveTextContent('2026-09-04T18:00:00')` (M8b/M8c mortos) | ✅ PASS |
| **VISAO-03** — comunicação privada, não substitui autoridades, não confirma cobertura | as três ressalvas presentes no texto | `VisaoGeralSegurado.test.tsx:137` — `findByText(/não substitui as autoridades competentes/)`; `:139` — `getByText(/não confirma cobertura ou indenização/)` | ✅ PASS |
| **VISAO-03** — linguagem "objetiva, não alarmista e orientada à segurança" | nenhum valor/estado preciso definido na spec | — | ⚠️ Spec-precision gap |
| **VISAO-04** — sem alerta relevante → estado vazio explicativo | serviço devolve `None`; API devolve `200 {"alerta": null}`; interface mostra estado vazio | `test_alerta_segurado.py:131` — `assert contexto.servico.obter_mais_relevante(SEGURADO_ID) is None`; `test_alerta_segurado_api.py:119-120` — `assert resposta.status_code == 200` / `assert resposta.json() == {"alerta": None}`; `VisaoGeralSegurado.test.tsx:186` — `findByRole('heading', { name: 'Nenhum alerta relevante no momento' })` | ✅ PASS |
| **VISAO-04** — sem inventar risco ou recomendação | nenhum bloco de alerta renderizado no estado vazio | `VisaoGeralSegurado.test.tsx:188` — `queryByRole('heading', { level: 2, name: 'Chuva intensa' })).not.toBeInTheDocument()` | ✅ PASS |
| **VISAO-04** — Apólice, Comunicados e Meus Dados continuam acessíveis | as três superfícies alcançáveis pela navegação | Cláusula **formalmente deferida** em `spec.md:103` para 5.2/5.3/5.5 (as superfícies não existem: `src/frontend/src/App.test.tsx:127-134` prova que a navegação do perfil Segurado tem somente "Visão geral"). Regressão da cópia falsa protegida por `VisaoGeralSegurado.test.tsx:198` (M12 morto) | ⚠️ Deferida e registrada |
| **VISAO-05** — fonte degradada → snapshot com caráter apenas informativo | `fonte_degradada = true` quando a última sincronização da área falhou ou precisou de >1 tentativa; `false` caso contrário e sempre para evento sintético | Aplicação: `test_alerta_segurado.py:192` — `is True` (estado `FALHA`); `:226` — `is True` (2 tentativas); `:257` — `is False` (1 tentativa); `:269` — `is False` (sem sincronização); `:167` e `:326` — `is False` (sintético). Fronteira HTTP: só `test_alerta_segurado_api.py:100` — `is False`; **nenhum teste de rota com `true`**, e `adaptadores/http/alerta_segurado.py:117` pode ser fixado em `False` com **980/980 verdes** (M15) — a matriz de `tasks.md` exige "fonte degradada" nesta camada | ❌ GAP *(camada HTTP)* |
| **VISAO-05** — interface não sugere alerta novo a partir do snapshot | aviso com caráter "apenas informativo" | `VisaoGeralSegurado.test.tsx:164` — `findByText(/Fonte meteorológica degradada/)`; `:165` — `getByText(/apenas informativo/)`; `:175` — `queryByText(/Fonte meteorológica degradada/)).not.toBeInTheDocument()` quando operacional (asserção negativa) | ✅ PASS |
| **VISAO-05** — snapshot aparece "com sua idade" | idade do último dado visível | `VisaoGeralSegurado.test.tsx:166` — `getByText(/\d+ d atrás/)` com `instanteObservado` determinístico em `:159`; renderizado por `VisaoGeralSegurado.tsx:151` via `calcularIdade`. M13 morto | ✅ PASS *(gap da rodada 2 fechado)* |
| **VISAO-06** — distinguir `Carregando`, `Alerta`, `Sem alerta`, `Contexto trocando`, `Erro` | cinco estados observáveis **mutuamente distintos** | `VisaoGeralSegurado.test.tsx:73` (Carregando); `:86` (Alerta); `:186` (Sem alerta); `:215` (Contexto trocando); `:263` (Erro). Distinção `Erro` × `Sem alerta` na **primeira carga** assertada nos dois sentidos em `:263` + `:266`. M9 morto | ✅ PASS *(gap da rodada 2 fechado)* |
| **VISAO-06** — falha informa impacto e próxima ação | ocorrência + impacto + próxima ação no bloco de erro | `VisaoGeralSegurado.test.tsx:290-292` — `toHaveTextContent('Falha ao consultar o alerta.')` / `('O alerta pode estar desatualizado.')` / `('Tente novamente.')` | ✅ PASS |
| **VISAO-06** — falha não apaga o último contexto válido (caso *Alerta*) | o alerta anterior continua visível sob o banner de erro | `VisaoGeralSegurado.test.tsx:293` — `expect((await screen.findAllByText(/AREA-VALIDA/)).length).toBeGreaterThan(0)` (M5 morto) | ✅ PASS |
| **VISAO-06** — falha não apaga o último contexto válido (caso *Sem alerta*) | o estado vazio explicativo continua visível sob o banner de erro | `VisaoGeralSegurado.test.tsx:313` — `findByRole('alert')` **e** `:315` — `getByRole('heading', { name: 'Nenhum alerta relevante no momento' })`. M7 reconfirmado morto nesta rodada | ✅ PASS |
| **VISAO-07** — teclado preserva ordem, foco e nomes | botão de nova tentativa alcançável por `Tab` e ativável por `Enter` | `VisaoGeralSegurado.test.tsx:359` — `expect(screen.getByRole('button', { name: 'Tentar novamente' })).toHaveFocus()`; `:335` — heading recuperado após acionar o botão | ✅ PASS |
| **VISAO-07** — zoom 200% preserva informação essencial | nenhuma informação essencial desaparece a 200% | `VisaoGeralSegurado.test.tsx:366-383` reduz `window.innerWidth` para 640 e reasserta severidade (`:375`), origem (`:376`), localização (`:377`) e recomendação (`:380`); jsdom não faz layout nem zoom real, então a asserção prova **presença no DOM**, não legibilidade sob zoom | ⚠️ Spec-precision gap (ambiente não simula o critério; lição L-006) |
| **VISAO-07** — "alvos mínimos" preservados | tamanho mínimo de alvo não numerado na spec | — | ⚠️ Spec-precision gap |
| **VISAO-08** — nenhuma informação essencial depende só de cor/ícone/mapa/hover | rótulo textual acompanha o ícone de proveniência (`aria-hidden`) | `VisaoGeralSegurado.test.tsx:395` — `getAllByText(/Cenário demonstrativo \(sintético\)/).length).toBeGreaterThan(0)`; ícones `aria-hidden="true"` em `VisaoGeralSegurado.tsx:149,157,163,218` | ✅ PASS |

**Status**: ❌ 2 gaps (VISAO-02 e VISAO-05, ambos na **camada HTTP**) + 1 cláusula deferida e registrada (VISAO-04) + 3 spec-precision gaps
**Contagem**: **20/22 cláusulas** casaram com o resultado definido na spec em todas as camadas exigidas (rodada 1: 18/22 · rodada 2: 20/22). Duas cláusulas antes verdes na rodada 2 caem para GAP porque o sensor desta rodada provou que a evidência delas **não cobre a fronteira HTTP** — não é regressão de código, é aumento de rigor.

---

## Edge Cases

- [x] **Elegível para mais de um evento → mostra o mais recente**: `src/backend/testes/test_repositorio_elegibilidade.py:577` — `assert resultado.id == id_novo` após forçar `criado_em` `2020-01-01` vs `2030-01-01`. M3 (`ORDER BY e.criado_em DESC` → `ASC` em `repositorio_elegibilidade.py:247`) **reconfirmado morto nesta rodada**.
- [x] **Snapshot degradado sem elegibilidade associada → "sem alerta", não "alerta degradado"**: `test_alerta_segurado.py:272-292` semeia área + sincronização em `FALHA` **sem** nenhuma elegibilidade e asserta `obter_mais_relevante(SEGURADO_ID) is None` (`:292`).
- [x] **Troca de contexto permanece em `Contexto trocando` sem misturar dado antigo e novo**: metade em `VisaoGeralSegurado.test.tsx:215-216` (`Contexto trocando…` presente e `AREA-ANTIGA` com `length).toBe(0)`); a outra metade — descartar a resposta antiga que chega depois — em `:222-243`, com espera de macrotask real (`:240`) e comentário explicando por que um microtask não bastaria. M6 morto na rodada 2.

---

## Discrimination Sensor

Scratch isolado: `git worktree add /tmp/verify-5-1-round3-scratch HEAD`, `node_modules` do frontend por symlink, removido com `git worktree remove --force` + `git worktree prune`. `git status --porcelain` da árvore real **idêntico antes e depois** (os mesmos 4 arquivos de `.specs/` já modificados pela rodada 2); `git worktree list` mostra somente a árvore principal; `/tmp/verify-5-1-round3-scratch` não existe mais. Nenhum `git stash` usado.

| # | File:line | Description | Killed? |
| --- | --- | --- | --- |
| **M9** | `VisaoGeralSegurado.tsx:67` | `useState(false)` → `useState(true)` em `resolvidoAoMenosUmaVez` | ✅ **Killed** (`1 failed \| 20 passed`, `VisaoGeralSegurado.test.tsx:263`) — *sobrevivia na rodada 2* |
| **M11** | `adaptadores/http/alerta_segurado.py:110-111` | `periodo_inicio=alerta.periodo_fim`, `periodo_fim=alerta.periodo_inicio` | ✅ **Killed** (`test_alerta_segurado_api.py:104` — `assert '2026-09-04T18:00:00' == '2026-09-04T12:00:00'`) — *sobrevivia na rodada 2* |
| **M12** | `VisaoGeralSegurado.tsx:135` | Frase falsa reintroduzida: `<p>Apólice, Comunicados e Meus Dados continuam disponíveis pela navegação.</p>` no bloco do estado vazio | ✅ **Killed** (`1 failed \| 20 passed`, `VisaoGeralSegurado.test.tsx:198`, citando o `<p>` reintroduzido) |
| **M13** | `VisaoGeralSegurado.tsx:151` | Chamada `calcularIdade(alerta.instanteObservado)` removida do aviso, mantendo todos os rótulos vizinhos | ✅ **Killed** (`1 failed \| 20 passed`, `VisaoGeralSegurado.test.tsx:166`) — prova que a asserção depende do valor, não do texto ao redor |
| M7 *(re-check)* | `VisaoGeralSegurado.tsx:128-129` | Ramo `(estado === 'erro' && resolvidoAoMenosUmaVez && !alerta)` removido | ✅ **Killed** (`VisaoGeralSegurado.test.tsx:315`) — código da rodada 2 não regrediu |
| M8c *(re-check)* | `VisaoGeralSegurado.tsx:214` | `<dd>{alerta.instanteObservado}</dd>` → `<dd>—</dd>` (só o valor, `<dt>` mantido) | ✅ **Killed** (`VisaoGeralSegurado.test.tsx:106`) — código da rodada 2 não regrediu |
| M3 *(re-check)* | `repositorio_elegibilidade.py:247` | `ORDER BY e.criado_em DESC` → `ASC` | ✅ **Killed** (`test_repositorio_elegibilidade.py:577`) — código da rodada 1 não regrediu |
| **M14** | `adaptadores/http/alerta_segurado.py:115` | `origem=str(alerta.origem)` → `origem="real_inmet"` (procedência fixada na resposta pública) | ❌ **Survived** — suíte backend inteira **980/980 verde**. Nenhum dos 4 testes da rota (`test_alerta_segurado_api.py:91,117,129,138`) usa evento sintético; um alerta sintético seria servido como real |
| **M15** | `adaptadores/http/alerta_segurado.py:117` | `fonte_degradada=alerta.fonte_degradada` → `fonte_degradada=False` | ❌ **Survived** — suíte backend inteira **980/980 verde**. Nenhum teste chama a rota com a fonte degradada, embora a matriz de `tasks.md` exija esse caso nesta camada |

**Sensor depth**: P0-full (9 mutações nesta rodada — 4 sobre o diff do fix, 3 re-checks de regressão, 2 exploratórias na fronteira HTTP; somadas a M1–M8 e M10 das rodadas 1-2)
**Sensor desta rodada**: **7/9 killed** — 2 sobreviventes (M14, M15) nesta rodada, ambos mortos no fechamento pós-escalação abaixo

### Observação adicional (não medida por mutante)

`src/frontend/src/api/alertaSegurado.ts:85-92` traduz `snake_case` → `camelCase` (`periodo_inicio`→`periodoInicio`, `origem`, `fonte_degradada`→`fonteDegradada`) e **não tem nenhum teste**: `getAlertaMaisRelevante` é mockado em `VisaoGeralSegurado.test.tsx:13-14` e em `App.test.tsx:28-29`, e não existe `alertaSegurado.test.ts`. Por evidence-or-zero, esse mapeamento conta como não coberto — é a mesma classe de M11/M14/M15 no lado do frontend. Registrado como Minor (Fix 3), não como bloqueador: os valores renderizados estão assertados no componente e os valores servidos estão assertados na rota.

---

## Code Quality

| Principle | Status |
| --- | --- |
| No features beyond what was asked | ✅ — `743de0a` toca **somente 2 arquivos de teste**; zero mudança de código de produção |
| Minimum code | ✅ — 51 inserções, 5 remoções, todas em testes |
| No abstractions for single-use code | ✅ — o laço sobre `['Apólice', 'Comunicados', 'Meus Dados']` é a única estrutura nova e é local ao teste |
| No unnecessary "flexibility" added | ✅ |
| Only touched files required for task | ✅ — `test_alerta_segurado_api.py` e `VisaoGeralSegurado.test.tsx`, exatamente os dois arquivos que os Fixes 1-4 nomeavam |
| Didn't "improve" unrelated code | ✅ |
| Matches existing patterns/style | ✅ — `mockRejectedValueOnce` + `ErroAlertaSegurado`, `alertaReal({...})`, `describe` por VISAO-NN; comentários em pt-BR explicando o *porquê* (o de `:156-157` justifica o instante fixo; o de `:101-103` do backend justifica a asserção do contrato completo) |
| Tests map to acceptance criteria e não são rasos | ✅ — todos os 4 testes/asserções novos foram provados discriminantes por mutação (M9, M11, M12, M13) |
| Spec-anchored outcome check | ❌ — VISAO-02 (origem sintética) e VISAO-05 (fonte degradada) não têm asserção que case com o resultado definido na spec **na camada do contrato HTTP** |
| Per-layer Coverage Expectation met | ❌ — a matriz de `tasks.md` exige do roteador HTTP "caminho feliz + sem alerta + **fonte degradada**"; o caso "fonte degradada" **nunca foi implementado** nessa camada (item planejado na fase Tasks e não entregue) |
| Every test maps to a spec requirement — no unclaimed tests | ✅ — os 2 testes novos mapeiam para VISAO-06 (`:246`) e VISAO-04 (`:191`); as asserções novas reforçam VISAO-01/02/05 |
| Documented guidelines followed | ✅ — `AGENTS.md` (somente dados sintéticos: `9990001`, UUIDs fixos de teste, `tmp_path`) |
| Would senior engineer approve? | ⚠️ — sim para o que aterrissou, que é cirúrgico e bem comentado. Reprovaria, porém, o fechamento da história: o mesmo commit que fechou o buraco de mapeamento em `periodo_*` deixou os campos vizinhos `origem` e `fonte_degradada` da **mesma função** sem asserção, e o caso "fonte degradada" da matriz segue ausente |

### Observação de honestidade (AD-9) — status

A violação da rodada 1 (cópia prometendo navegação inexistente) está corrigida **e agora protegida por regressão** (M12 morto). O risco de "erro exibido como resultado" está fechado (M9 morto). Resta **uma** dívida de honestidade, e é a mais estrutural das três: **M14 mostra que a fronteira HTTP pode rotular um cenário sintético como observação real do INMET sem que nenhum dos 980 testes de backend perceba** — precisamente a confusão que VISAO-02 proíbe em letra explícita e que motivou esta história existir.

---

## Gate Check

- **Gate command (backend)**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`
- **Result**: **980 passed**, 0 failed, 0 skipped (exit 0) · ruff `All checks passed!` (exit 0) · pyright `0 errors, 0 warnings, 0 informations` (exit 0)
- **Gate command (frontend)**: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**: **339 passed** / 34 arquivos, 0 failed (exit 0) · lint exit 0 (somente warnings `react(set-state-in-effect)` / `only-export-components` pré-existentes, todos em `SuperficieSimulacao.tsx`, `SuperficieRevisaoLote.tsx` e `SuperficieEventoDecisao.tsx` — nenhum arquivo deste diff) · build exit 0 (`✓ built in 240ms`)
- **Ambos os gates saem 0.**
- **Test count antes da feature**: backend 963 · frontend 320
- **Após a rodada 1**: backend 978 · frontend 335
- **Após a rodada 2**: backend 980 · frontend 337
- **Após a rodada 3**: backend 980 · frontend **339**
- **Delta da rodada 3**: +0 backend (`743de0a` **fortalece** um teste existente de 4 para 10 asserções em vez de adicionar um novo) · +2 frontend (primeira carga que falha; regressão da cópia do estado vazio)
- **Skipped tests**: nenhum
- **Failures**: nenhuma
- **Integridade**: nenhuma contagem caiu em nenhuma das três rodadas; nenhuma asserção foi enfraquecida. A troca de `instanteObservado: new Date().toISOString()` por `'2020-01-01T00:00:00'` em `VisaoGeralSegurado.test.tsx:159` é um **fortalecimento** (torna determinístico um valor antes dependente do relógio, permitindo assertar a idade renderizada).

---

## Fix Plans

### Fix 1 — Assertar procedência e estado da fonte na fronteira HTTP (Major)

- **Root cause**: `_resposta_alerta` (`src/backend/central_preventiva/adaptadores/http/alerta_segurado.py:105-118`) traduz 11 campos; a rodada 2 fechou os temporais e de conteúdo, mas `origem` (`:115`) e `fonte_degradada` (`:117`) continuam sem asserção que os discrimine. Os 4 testes da rota usam **só** um evento `real_inmet` com fonte operacional, então fixar `origem="real_inmet"` (M14) ou `fonte_degradada=False` (M15) mantém **980/980 verdes**. As asserções existentes cobrem o `AlertaSegurado` da camada de aplicação (`test_alerta_segurado.py:152,166,192,226`), não a tradução do roteador.
- **Fix task**: em `src/backend/testes/test_alerta_segurado_api.py`, adicionar **dois** testes de rota:
  1. `test_consultar_alerta_de_evento_sintetico_devolve_origem_sintetico` — semear um `EventoMeteorologico` com `proveniencia=ProvenienciaEvento.SINTETICO` e assertar `corpo["alerta"]["origem"] == "sintetico"` (mata M14, e assertar `!= "real_inmet"` deixa a intenção de VISAO-02 explícita).
  2. `test_consultar_alerta_com_fonte_degradada_devolve_fonte_degradada_true` — semear área + sincronização em estado `FALHA` (o mesmo arranjo de `test_alerta_segurado.py:180-192`) e assertar `corpo["alerta"]["fonte_degradada"] is True` (mata M15 **e** entrega o caso "fonte degradada" que a matriz de `tasks.md` exige do roteador HTTP desde a fase Tasks).
- **Where**: `src/backend/testes/test_alerta_segurado_api.py`
- **Verify**: injetar M14 (`origem="real_inmet"` fixo) e M15 (`fonte_degradada=False` fixo) num worktree descartável e confirmar que cada um faz falhar o teste correspondente.
- **Done when**: M14 e M15 mortos; a linha "Roteador HTTP" da matriz de cobertura passa a cobrir os três casos que ela própria declara.
- **Priority**: **Major** — VISAO-02 ("origem sintética SHALL nunca ser confundida com observação real") é a garantia central de honestidade da história e atravessa essa fronteira; VISAO-05 tem o caso exigido nominalmente pela `tasks.md`.

### Fix 2 — Diferenciar `periodo_fim` de `instante_observado` no fixture da rota (Minor)

- **Root cause**: `test_alerta_segurado_api.py:76-80` semeia `periodo_fim` e `instante_observado` com o **mesmo** instante (`2026-09-04T18:00:00`), então `:105` e `:106` não discriminariam uma troca entre esses dois campos.
- **Fix task**: dar a `instante_observado` um instante distinto (ex.: `datetime(2026, 9, 4, 19, 30)`) e ajustar `:106`.
- **Where**: `src/backend/testes/test_alerta_segurado_api.py`
- **Priority**: Minor — o mapeamento é simples e a camada de aplicação já distingue os três instantes.

### Fix 3 — (Opcional) Cobrir o mapeamento do cliente HTTP do frontend (Minor)

- **Root cause**: `src/frontend/src/api/alertaSegurado.ts:85-92` converte o corpo `snake_case` da rota para o `AlertaSegurado` em `camelCase` e não tem nenhum teste — o módulo é mockado em todos os testes que o usam (`VisaoGeralSegurado.test.tsx:13-14`, `App.test.tsx:28-29`). É o espelho de M11/M14/M15 no lado do cliente.
- **Fix task**: criar `src/frontend/src/api/alertaSegurado.test.ts` com um `fetch` mockado devolvendo um corpo completo e assertar os 11 campos do objeto convertido.
- **Priority**: Minor — os valores renderizados já estão assertados no componente e os servidos na rota; o elo faltante é a tradução em si.

---

## Requirement Traceability Update

| Requirement | Rodada 1 | Rodada 2 | **Rodada 3 (final)** |
| --- | --- | --- | --- |
| VISAO-01 | ❌ Needs Fix | ✅ Verified | ✅ **Verified** — período assertado na aplicação, na rota (`test_alerta_segurado_api.py:104-105`) e na interface (`VisaoGeralSegurado.test.tsx:88-90`); M8a e M11 mortos |
| VISAO-02 | ❌ Needs Fix | ✅ Verified | ❌ **Needs Fix** — real × sintético assertado nos dois sentidos na aplicação e na interface, mas **não na fronteira HTTP**: `alerta_segurado.py:115` pode fixar `origem="real_inmet"` com 980/980 verdes (M14, Fix 1) |
| VISAO-03 | ✅ Verified | ✅ Verified | ✅ **Verified** (linguagem "não alarmista" segue como spec-precision gap) |
| VISAO-04 | ❌ Needs Fix | ⚠️ Verified (parcial) | ✅ **Verified (parcial)** — cópia falsa removida **e protegida por regressão** (`VisaoGeralSegurado.test.tsx:198`, M12 morto); cláusula "Apólice, Comunicados e Meus Dados" formalmente **deferida** para 5.2/5.3/5.5 em `spec.md:103`. Nada mais pendente nesta rodada |
| VISAO-05 | ✅ Verified | ✅ Verified | ❌ **Needs Fix** — idade renderizada agora assertada (`:166`, M13 morto) e todos os branches cobertos na aplicação, mas o **caso "fonte degradada" na camada do roteador HTTP nunca foi implementado** (exigido pela matriz de `tasks.md`): `alerta_segurado.py:117` pode fixar `False` com 980/980 verdes (M15, Fix 1) |
| VISAO-06 | ❌ Needs Fix | ❌ Needs Fix | ✅ **Verified** — os 5 estados discriminados, incluindo `Erro` × `Sem alerta` na primeira carga (`:263` + `:266`, M9 morto) e a preservação do último contexto válido nos dois casos (M5, M7 mortos) |
| VISAO-07 | ✅ Verified | ✅ Verified | ✅ **Verified** (zoom 200% e "alvos mínimos" seguem como spec-precision gaps: jsdom não faz layout; a spec não numera o alvo) |
| VISAO-08 | ✅ Verified | ✅ Verified | ✅ **Verified** |

**Resultado**: 6 Verified · 1 Verified (parcial, cláusula deferida e registrada) · 2 Needs Fix (VISAO-02, VISAO-05 — ambos exclusivamente na camada do contrato HTTP).

---

## Summary

**Overall**: ❌ Not Ready — **iteração 3 de 3 esgotada; escalar ao usuário** (`validate.md` §8: "se os gaps persistirem após 3 rodadas, escalar ao usuário em vez de continuar o laço")

**Spec-anchored check**: 20/22 cláusulas de AC casaram com o resultado definido na spec em todas as camadas exigidas · 2 gaps (VISAO-02, VISAO-05, ambos na camada HTTP) · 1 cláusula deferida e registrada · 3 spec-precision gaps
**Sensor**: 9 mutações, **7 mortas, 2 sobreviventes** (M14, M15)
**Gate**: backend 980 passed / ruff 0 / pyright 0 (exit 0) · frontend 339 passed / lint 0 / build 0 (exit 0)

**What works**:
- **Os 4 fixes da rodada 2 funcionaram de verdade.** Reinjetei M9, M11, a frase falsa (M12) e a remoção da idade renderizada (M13): **todos os 4 morrem**, cada um exatamente no teste que o fix criou. Nenhum é cosmético.
- **VISAO-06 está fechada.** A distinção `Erro` × `Sem alerta` agora é assertada nos dois sentidos na primeira carga, e o dump do DOM do vitest sob M9 confirma que a asserção pega precisamente o comportamento desonesto.
- **VISAO-04 está fechada** no que dependia desta história: a cópia falsa foi removida na rodada 1, agora está protegida contra reintrodução, e o deferimento da cláusula de navegação está formalmente registrado em `spec.md:103` — com a evidência (`App.test.tsx:127-134`) de por que ela não é satisfazível hoje.
- Sem regressão: M3, M7 e M8c, mortos em rodadas anteriores, continuam mortos. Nenhuma contagem de testes caiu em nenhuma das três rodadas e nenhuma asserção foi enfraquecida.
- O commit do fix é exemplar em disciplina: **zero linhas de produção**, dois arquivos de teste, comentários explicando o *porquê* de cada asserção nova.

**Issues found**: 3 fix tasks acima. O bloqueador é **um só, com duas faces**, e está inteiramente contido em `src/backend/testes/test_alerta_segurado_api.py`: os testes da rota exercitam apenas um evento `real_inmet` com fonte operacional, deixando `origem` (M14) e `fonte_degradada` (M15) sem discriminação na única camada que os traduz para o contrato público. M15 é, além disso, um item de cobertura que a **própria `tasks.md` planejou na fase Tasks e que nunca foi entregue** ("Roteador HTTP … caminho feliz + sem alerta + fonte degradada").

**Nota de contexto para a decisão**: nenhum dos dois sobreviventes é um **defeito de produto** — o código de `_resposta_alerta` está correto e a Visão geral se comporta bem hoje. O que falta é a rede de segurança: nada impediria uma regressão futura de rotular um cenário sintético como observação real do INMET. O conserto é **dois testes num único arquivo**, sem mudança de produção.

**Next steps**: o laço de 3 iterações do Verificador está esgotado — **esta história não deve ser fechada nem re-despachada automaticamente**. Levar ao usuário a decisão entre:
1. autorizar uma correção pontual fora do laço (Fix 1: dois testes em `test_alerta_segurado_api.py`) e uma re-verificação dirigida só a M14/M15; ou
2. aceitar o risco conscientemente, registrando os dois gaps como dívida rastreada com as histórias que os herdam.

---

## Fechamento pós-escalação (orquestrador, com autorização do usuário)

O usuário escolheu a opção 1 acima: aplicar o Fix 1 (dois testes, nenhuma mudança de produção) e confirmar diretamente, sem despachar um 4º Verifier independente — o laço de 3 iterações já estava esgotado, então esta confirmação é do orquestrador, não uma quarta rodada do Verifier.

**Commit**: `17f9182` — test(segurado): cobrir origem sintetica e fonte degradada na rota HTTP.

**O que foi adicionado** em `src/backend/testes/test_alerta_segurado_api.py`:
- `test_consultar_alerta_de_evento_sintetico_devolve_origem_sintetico` — semeia um evento com `proveniencia=ProvenienciaEvento.SINTETICO` e asserta `corpo["alerta"]["origem"] == "sintetico"`.
- `test_consultar_alerta_com_fonte_degradada_devolve_fonte_degradada_true` — semeia uma área monitorada + sincronização em estado `FALHA` (mesmo arranjo de `test_alerta_segurado.py`) e asserta `corpo["alerta"]["fonte_degradada"] is True`.

**Verificação empírica dos dois mutantes, em worktree descartável** (`git worktree add /tmp/verify-5-1-final-scratch HEAD`, removido com `--force` ao final; `git status --porcelain` da árvore real vazio antes e depois; `git worktree list` mostra só a árvore principal):
- **M14** (`origem=str(alerta.origem)` → `origem="real_inmet"` fixo em `adaptadores/http/alerta_segurado.py:115`) → o teste de evento sintético falha: `AssertionError: assert 'real_inmet' == 'sintetico'`. **Morto.**
- **M15** (`fonte_degradada=alerta.fonte_degradada` → `fonte_degradada=False` fixo em `:117`) → o teste de fonte degradada falha: `assert False is True`. **Morto.**

**Gate final** (backend, único stack tocado): `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright` → **982 passed** (980 + 2 novos), 0 failed, 0 skipped · ruff `All checks passed!` · pyright `0 errors, 0 warnings, 0 informations`. Frontend inalterado nesta correção (339 passed, já confirmado na rodada 3).

**Spec-anchored, atualizado**: VISAO-02 (origem sintética nunca confundida com real) e VISAO-05 (fonte degradada) agora têm evidência nas três camadas — aplicação, rota HTTP e interface — para todos os cenários que a spec exige. **22/22 cláusulas de AC cobertas** (3 permanecem spec-precision gaps por não terem um valor preciso definido na própria spec — VISAO-03 "linguagem não alarmista", VISAO-07 zoom/alvos mínimos — não são defeitos, são ambiguidades já sinalizadas nas rodadas 1-3).

**Sensor final**: 11/11 mutações mortas ao longo das três rodadas + este fechamento (M1-M15, todas as sobreviventes de cada rodada morreram na rodada seguinte ou neste fechamento).

**Débito residual, não bloqueante**: Fix 2 (fixture da rota reusa o mesmo instante para `periodo_fim`/`instante_observado`) e Fix 3 (mapeamento snake→camel de `alertaSegurado.ts` sem teste dedicado) seguem como Minor, registrados no `STATE.md`, não corrigidos agora por decisão deliberada (nenhum dos dois é uma classe de risco nova — o mesmo tipo de gap já foi coberto em outras camadas).

**Verdict final**: ✅ **PASS**. `validate_state.py` confirmado abaixo.
