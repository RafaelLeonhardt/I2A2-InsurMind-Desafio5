# História 5.3: Consultar a apólice sintética e seu uso preventivo — Validation

**Date**: 2026-09-05
**Spec**: `.specs/features/5-3-consultar-a-apolice-sintetica-e-seu-uso-preventivo/spec.md`
**Diff range (ponta a ponta)**: `d7285ae..HEAD` (`083dc5b`, `c56a654`, `3d76e73`, `39491c8`, `4d1c522`, `352aee8`)
**Diff dos fixes desta rodada**: `39491c8..HEAD`
**Verifier**: sub-agente independente (autor ≠ verificador), somente leitura sobre a árvore real
**Rodada**: **2 de no máximo 3** — re-verificação dos 7 achados da rodada 1

**Veredito**: ✅ **PASS** — os dois gates de Build saem com código 0, os 6 ACs têm citação
`file:line` com valor asserido igual ao definido pela spec, os 3 edge cases estão cobertos e
**12 de 12 injeções de falha de comportamento foram mortas**, incluindo os **7 mutantes que
sobreviveram na rodada 1**. Uma observação menor não bloqueante fica registrada (nota A).

Este relatório é **auto-contido**: substitui integralmente o da rodada 1 e não exige lê-lo.

---

## O que mudou entre a rodada 1 e a rodada 2

O commit `4d1c522` **não alterou nenhuma linha de código de produção** — verificado em
`git diff 39491c8..HEAD --stat`: os únicos arquivos de `src/` tocados são
`testes/test_apolice_segurado.py`, `testes/test_apolice_segurado_api.py`,
`src/frontend/src/api/apoliceSegurado.test.ts` (novo) e
`src/frontend/src/funcionalidades/segurado/SuperficieApolice.test.tsx`. Os 7 achados eram
todos de **poder de discriminação dos testes**, não de comportamento incorreto, e foram
corrigidos exatamente onde deviam ser: nos testes.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 `RepositorioApolices` | ✅ Done | `083dc5b`; desempate `criado_em DESC` exercitado com timestamps distintos e invertidos em relação à ordem de inserção (`test_repositorio_apolices.py:93-106`) |
| T2 `ServicoApoliceSegurado` | ✅ Done | `c56a654` + `4d1c522`; fronteira `vigencia_fim == hoje` agora testada nos dois lados (`test_apolice_segurado.py:194-216`) |
| T3 Endpoints HTTP | ✅ Done | `3d76e73` + `4d1c522`; `participa_de_alertas`, `canal_preferido` e `atende` agora exercitados nos dois valores |
| T4 Superfície de Apólice | ✅ Done | `39491c8` + `4d1c522`; `api/apoliceSegurado.ts` deixou de ser 100 % mockado — `apoliceSegurado.test.ts` exercita a tradução real |

Nenhuma task bloqueada ou parcial. Todos os "Done when" de `tasks.md` verificados lendo o
código e os testes, não a mensagem de commit.

---

## Spec-Anchored Acceptance Criteria

### P1: Dados da apólice e explicação de critérios sem promessa de cobertura

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| **APOLICE-01** — abrir Apólice exibe número, situação, vigência, endereço sintético, coberturas, canal preferencial e participação em alertas, de dado real | Os 7 grupos de campos, vindos do registro persistido | Serviço: `src/backend/testes/test_apolice_segurado.py:148-157` — `numero == "RES-0001"`, `tipo == "residencial"`, `situacao == "ativa"`, `estado_objetivo == "ativa"`, `vigencia_inicio == date(2026,1,1)`, `vigencia_fim == date(2030,12,31)`, `endereco_risco_sintetico == "Rua Sintética, 123"`, `coberturas == ("alagamento",)`, `canal_preferido == "sms"`, `participa_de_alertas is True` | ✅ PASS |
| **APOLICE-01** — contrato HTTP não mistura campos entre si | Cada campo de `RespostaApolice` com o seu próprio valor | `src/backend/testes/test_apolice_segurado_api.py:126-135` (10 asserções campo a campo) **+** `:174-175` — `corpo["canal_preferido"] == "whatsapp"` e `corpo["participa_de_alertas"] is False` (segundo valor, novo nesta rodada) | ✅ PASS — M5/M6/M7 agora mortos |
| **APOLICE-01** — tradução HTTP→UI (`snake_case`→`camelCase`) sem troca de campos | Objeto traduzido campo a campo | `src/frontend/src/api/apoliceSegurado.test.ts:50-61` — `expect(apolice).toEqual({...})` com **todos** os 10 campos em valores mutuamente distintos (`situacao:'ativa'` × `estadoObjetivo:'expirada'`; `participaDeAlertas:false`) | ✅ PASS — MF6/MF7 agora mortos |
| **APOLICE-01** — mesmos campos visíveis na interface | Visíveis na superfície | `SuperficieApolice.test.tsx:84-91` — `findByText('RES-0001')`, `getByText('Residencial')`, `getByText('2026-01-01 a 2030-12-31')`, `getByText('Rua Sintética, 123')`, `getByText('alagamento')`, `getByText('vendaval')`, `getByText('SMS')`, `getByText('Participando')`; segundo valor em `:99-100` — `findByText('Não participando')` + `queryByText('Participando')` ausente | ✅ PASS |
| **APOLICE-02** — explicação mostra como a categoria foi comparada, sem afirmação de cobertura/indenização/sinistro | Critérios comparados; nenhuma promessa | **Filtro + conteúdo**: `test_apolice_segurado_api.py:253-266` — `operandos == {"área afetada","tipo da apólice","situação da apólice","cobertura exigida"}`, `criterio_area["valor_observado"] == AREA`, `["atende"] is True`, `["justificativa"] == "Área da apólice corresponde à área do evento."`; `:304` — `criterio_cobertura["atende"] is False` (ramo negativo, novo). **Ausência de promessa sobre texto de PRODUÇÃO**: `test_apolice_segurado.py:259-312` — constrói ≥20 justificativas chamando `avaliar()` de verdade nos 5 candidatos (ramo positivo + os 4 ramos negativos) e assere `palavra_proibida not in texto_completo` para `("indeniza","sinistro","confirma cobertura","garantimos")`. **Aviso na UI**: `SuperficieApolice.test.tsx:207-209` — `findByText(/não confirma cobertura, indenização nem decisão de sinistro/)` | ✅ PASS — o gap de precisão da rodada 1 foi fechado (N2 morto) |

### P1: Estados de apólice sem falha técnica e isolamento por segurado

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| **APOLICE-03** — apólice inativa/sem cobertura explicada objetivamente, sem virar falha técnica | Estado textual de domínio, sem indicador de erro | **Serviço (4/4 estados)**: `test_apolice_segurado.py:167-168` (`cancelada`), `:178` (`suspensa`), `:190-191` (`expirada` com `situacao == "ativa"`), `:151` (`ativa`). **HTTP (4/4)**: `test_apolice_segurado_api.py:148` (`cancelada`), `:159` (`suspensa`, novo), `:187-188` (`expirada`), `:129` (`ativa`). **UI sem `role="alert"` (3 estados)**: `SuperficieApolice.test.tsx:122-123` (`Cancelada`), `:133-134` (`Expirada`), `:144-145` (`Suspensa`, novo) | ✅ PASS |
| **APOLICE-04** — apólice inexistente ou de outro segurado: API impede, interface mostra `Não encontrada` sem expor outro registro | `None` no caso de uso; `404` **idêntico** nos dois casos; `Não encontrada` na UI | **Serviço**: `test_apolice_segurado.py:223` — `obter(SEGURADO_ID) is None` (a apólice existe, mas é de `OUTRO_SEGURADO_ID`); `:229` e `:236` — `obter_explicacao` devolve `None` nos dois casos. **HTTP, rota da apólice**: `test_apolice_segurado_api.py:218-222` — `resposta_outro.status_code == 404`, `resposta_inexistente.status_code == 404`, `corpo_outro["codigo"] == corpo_inexistente["codigo"] == "apolice_nao_encontrada"`, `impacto` e `proxima_acao` iguais. **HTTP, rota da explicação**: `:337-341` — mesmo quarteto com `"explicacao_nao_encontrada"`. **Cliente**: `apoliceSegurado.test.ts:72-74` e `:143-145` — `ErroApoliceSegurado` com `status === 404` e `codigo` correto nas duas rotas. **UI**: `SuperficieApolice.test.tsx:164-166` — `findByRole('heading',{name:'Não encontrada'})` + `getByText('Esta apólice não existe ou não pertence a você.')` | ✅ PASS — comparação agora campo a campo nas duas rotas (N6 morto) |

### P2: Snapshot histórico preservado apesar de mudança atual

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| **APOLICE-05** — explicação de comunicação histórica usa o snapshot da execução | Valor do snapshot, não o atual divergente | Serviço: `test_apolice_segurado.py:362-364` — após `UPDATE apolices SET situacao = 'cancelada'`, `situacao_no_snapshot_depois == situacao_no_snapshot_antes == "ativa"` **e** `apolice_atual.situacao == "cancelada"` (as duas metades, provando divergência real). HTTP: `test_apolice_segurado_api.py:363-367` — mesmo `UPDATE`, depois `criterio_situacao["valor_observado"] == "ativa"` com `status_code == 200`. Por construção: `obter_explicacao` (`aplicacao/apolice_segurado.py:155-172`) não referencia `self._portas.apolices` | ✅ PASS |
| **APOLICE-06** — a superfície atual indica que alterações afetam só decisões futuras | Aviso explícito na superfície | `SuperficieApolice.test.tsx:103-110` — `findByText(/afetam apenas decisões futuras/)`; produção em `SuperficieApolice.tsx:226-229` | ✅ PASS |

**Status**: ✅ **6/6 ACs** com citação `file:line` e valor asserido igual ao definido pela
spec. Nenhum spec-precision gap aberto; nenhum PASS parcial.

### Nota A (menor, não bloqueante) — a asserção backend do Edge Case 1 é presa à fixture

`test_apolice_segurado_api.py:264` assere `"vendaval" not in valores_observados` sobre a
constante `CRITERIOS` (`:26-32`), que o próprio teste escreve com
`Criterio("cobertura exigida", "alagamento", ...)`. Executei o avaliador **real** com uma
apólice de duas coberturas e o critério de produção é:

```
'cobertura exigida' | 'alagamento, vendaval' | 'Apólice possui a cobertura exigida (alagamento).'
```

(`dominio/avaliador_elegibilidade.py`: `valor_observado=", ".join(candidato.coberturas)`).
Ou seja: **com snapshot real, essa asserção falharia** — a fixture diverge da produção nesse
campo. Consequências:

- **Não é violação da spec.** O edge case pede que a explicação "destaque especificamente a
  cobertura avaliada, sem listar as demais como se também tivessem participado". A superfície
  renderiza apenas `operando` + `justificativa` (`SuperficieApolice.tsx:260-264`) — nunca
  `valor_observado` — e a justificativa **de produção** nomeia só a cobertura avaliada
  (`(alagamento)`). A metade visível ao segurado está correta e **protegida por teste**
  (MF5 morto, ver Sensor).
- **É uma asserção enganosa.** `valor_observado` é documentado como "o valor observado no
  momento da avaliação" (o que a apólice tem), não "o que participou" — a asserção pede dele
  uma propriedade que ele não tem contrato de cumprir, e quebrará se alguém construir a
  fixture a partir de `avaliar()`.
- **Severidade**: Minor. Registrada como lição, não como fix bloqueante.

---

## Discrimination Sensor

Scratch isolado: `git worktree add /tmp/verify-5-3-round2-scratch HEAD`; **nenhum `git stash`**.
`node_modules` entrou no scratch por symlink (não versionado); baseline do scratch verde
(374 testes) antes de qualquer mutação. Cada mutação foi aplicada por script com
`assert src.count(old) == 1` e revertida com `git checkout --` logo após a medição.

**Isolamento verificado**: `git status --porcelain` da árvore real **vazio antes e vazio
depois** (idêntico); `git worktree list` após `remove --force` + `prune` mostra **apenas** a
árvore principal em `352aee8 [main]`; `/tmp/verify-5-3-round2-scratch` não existe mais.

### Re-injeção dos 7 mutantes que sobreviveram na rodada 1

| # | File | Description | Rodada 1 | Rodada 2 |
| --- | --- | --- | --- | --- |
| M1 | `aplicacao/apolice_segurado.py:90` | `vigencia_fim < hoje` → `<= hoje` (apólice que vence **hoje** vira "expirada") | ❌ Survived | ✅ **Killed** — `test_apolice_segurado.py:205` (`test_obter_apolice_com_vigencia_fim_hoje_ainda_e_ativa`) |
| M5 | `http/apolice_segurado.py:158` | `participa_de_alertas=True` fixo | ❌ Survived | ✅ **Killed** — `test_apolice_segurado_api.py:175` |
| M6 | `http/apolice_segurado.py:168` | `atende=True` fixo | ❌ Survived | ✅ **Killed** — `test_apolice_segurado_api.py:304` |
| M7 | `http/apolice_segurado.py:157` | `canal_preferido="sms"` fixo | ❌ Survived | ✅ **Killed** — `test_apolice_segurado_api.py:174` |
| MF5 | `SuperficieApolice.tsx:259` | A seção de explicação passa a listar **também** todas as coberturas da apólice (viola o Edge Case 1) | ❌ Survived | ✅ **Killed** — `SuperficieApolice.test.tsx:233` (`within(região).queryByText(/vendaval/)`) |
| MF6 | `api/apoliceSegurado.ts:92-93` | `paraApolice`: `numero`/`tipo` trocados | ❌ Survived | ✅ **Killed** — `apoliceSegurado.test.ts:50` |
| MF7 | `api/apoliceSegurado.ts:113` | `paraCriterio`: `justificativa: corpo.operando` | ❌ Survived | ✅ **Killed** — `apoliceSegurado.test.ts:114` |

### Mutações novas desta rodada (código tocado nesta rodada, não estressado na rodada 1)

| # | File | Description | Killed? |
| --- | --- | --- | --- |
| N1 | `aplicacao/apolice_segurado.py:88-89` | `_estado_objetivo` colapsa qualquer situação não-`ativa` em `"cancelada"` (apaga a distinção `suspensa`) | ✅ **Killed** — `test_apolice_segurado.py::…suspensa…` **e** `test_apolice_segurado_api.py:159` (as duas camadas) |
| N2 | `dominio/avaliador_elegibilidade.py` | Justificativa de produção `"Apólice está ativa."` → `"Apólice está ativa e garantimos a indenização."` | ✅ **Killed** — `test_apolice_segurado.py:312` — prova que o guarda-corpo de APOLICE-02 agora alcança o texto de produção, não a fixture |
| N3 | `api/apoliceSegurado.ts:101` | `participaDeAlertas: true` fixo (L-061 na camada do cliente) | ✅ **Killed** — `apoliceSegurado.test.ts:50` |
| N4 | `api/apoliceSegurado.ts:94-95` | `situacao`/`estadoObjetivo` trocados | ✅ **Killed** — `apoliceSegurado.test.ts:50` |
| N5 | `SuperficieApolice.tsx:37` | Rótulo `suspensa: 'Suspensa'` removido (cai no fallback bruto) | ✅ **Killed** — `SuperficieApolice.test.tsx:144` |
| N6 | `http/apolice_segurado.py:126` | `codigo` do `404` da apólice → `"apolice_ausente"` | ✅ **Killed** — `test_apolice_segurado_api.py:220` **e** `:199` (a comparação de não-enumeração fixa o código, não só a igualdade) |

**Sensor depth**: expandido (12 injeções nesta rodada; piso do tier padrão: 1-3, do tier P0: 5).
Somado à rodada 1, a história acumula **26 injeções distintas**, todas hoje mortas.
**Result**: **12/12 killed, 0 survived** — ✅ **PASS**

### Observação de robustez

A suíte frontend rodou 8 vezes nesta rodada (1 baseline + 6 mutações + 1 confirmação) sem
nenhum falso negativo. O teste flaky suspeitado na rodada 1 (`1 failed | 365 passed` sem nome
de teste, em uma execução isolada) **não se reproduziu**. Mantida a nota para quem investigar
depois; não atribuído a esta história.

---

## Verificação das alegações do autor sobre os fixes

| Alegação (commit `4d1c522`) | Veredito | Evidência independente |
| --- | --- | --- |
| Fix 1 — fronteira testada com data **relativa**, não literal | ✅ **Verdadeira** | `test_apolice_segurado.py:196` usa `date.today().isoformat()` e `:210` usa `(date.today() - timedelta(days=1)).isoformat()` — nenhum literal de calendário; os testes não expiram com o tempo. M1 morre |
| Fix 2 — `apoliceSegurado.ts` deixou de ser 100 % mockado | ✅ **Verdadeira** | `apoliceSegurado.test.ts` (158 linhas, 6 testes) chama `getApolice`/`getExplicacaoApolice` **reais** com `fetch` stubado, cobrindo `200` (mapeamento completo), `404` (`problem+json` → `ErroApoliceSegurado`) e falha de rede. Os 10 campos têm valores mutuamente distintos e a asserção é `toEqual` do objeto inteiro — qualquer troca ou constante fixa morre (MF6, MF7, N3, N4) |
| Fix 3 — os 3 campos agora aparecem nos dois valores | ✅ **Verdadeira** | `criar_segurado` (`:62-73`) passou a ser chamado com `canal_preferido="whatsapp", participa_de_alertas=False` em `:169`, e há um snapshot com `atende=False` em `:280-283`. M5/M6/M7 morrem |
| Fix 4 — o teste frontend delimita a região, não varre a página | ✅ **Verdadeira** | `SuperficieApolice.test.tsx:229-233`: `findByRole('region',{name:'Como sua apólice participou desta decisão'})` + `within(...)`. Necessário porque `vendaval` **aparece legitimamente** na lista de Coberturas da apólice (`SuperficieApolice.tsx:205-212`) — uma busca de página inteira daria falso negativo. MF5 morre |
| Fix 4 (metade backend) | ⚠️ **Parcialmente verdadeira** | A asserção existe (`:264`) mas é presa à fixture — ver **nota A**. Não bloqueia: a metade visível ao segurado está protegida |
| Fix 5 — varredura sobre texto de produção, não constante do teste | ✅ **Verdadeira** | `test_apolice_segurado.py:259-312` chama `avaliar()` de verdade em 5 candidatos (base + 4 variantes via `dataclasses.replace`), cobrindo o ramo **negativo** de todos os 4 critérios relevantes à apólice, e assere `len(...) >= 20` para impedir que o teste esvazie silenciosamente. N2 (injeção de `"garantimos a indenização"` na produção) morre. Ressalva menor: o ramo negativo de `participação em alertas` não é varrido — mas esse critério é justamente o **filtrado para fora** da explicação da apólice, então não pertence a APOLICE-02 |
| Fix 6 — `suspensa` coberta em HTTP e frontend | ✅ **Verdadeira** | `test_apolice_segurado_api.py:151-159` e `SuperficieApolice.test.tsx:137-145`. N1 e N5 morrem |
| Fix 7 — `404` compara `codigo` e os dois status | ✅ **Verdadeira** | Rota da apólice: `:218-222` (era 2 asserções, agora 5). Rota da explicação: `:337-341`. `ocorrencia` fica de fora com razão (ecoa o `elegibilidade_id` que o solicitante já conhece) e `correlacao_id` é `uuid4()` por ocorrência, por construção. Confirmado por leitura que há **um único** construtor de `404` por rota (`http/apolice_segurado.py:121-142`) — não-enumeração garantida por construção, e agora também por asserção |
| "Nenhum código de produção foi alterado" | ✅ **Verdadeira** | `git diff 39491c8..HEAD --stat`: em `src/`, só arquivos de teste. Os 7 achados eram de discriminação de teste, não de comportamento — a correção certa era exatamente essa |

---

## Code Quality

| Principle | Status |
| --- | --- |
| No features beyond what was asked | ✅ `buscar_por_id` em `RepositorioApolices` não é usado em produção, mas está na interface do `design.md:61` e no Done-when de T1 |
| No abstractions for single-use code | ✅ `PortasApoliceSegurado` + 3 `Protocol` seguem o padrão de 5.1/5.2 |
| No unnecessary "flexibility" added | ✅ |
| Only touched files required for task | ✅ 17 arquivos na feature; nesta rodada, só 4 arquivos de teste |
| Didn't "improve" unrelated code | ✅ A extensão de `repositorio_segurados.py` é estritamente aditiva (`Segurado`, `buscar_por_id` e o `SELECT` original inalterados byte a byte; `inserir_segurado` ganhou 2 parâmetros com default idêntico ao valor antigo) |
| Matches existing patterns/style | ✅ Roteador com `problem+json`, `422` para UUID inválido, docstrings em pt-BR, `RespostaX` com `extra="forbid"`; `apoliceSegurado.test.ts` segue o padrão de `contexto.test.ts`/`elegibilidade.test.ts` |
| Would senior engineer approve? | ✅ Sim — a lacuna estrutural da rodada 1 (178 linhas de cliente HTTP sem nenhum teste) está fechada |
| Tests map to ACs and are non-shallow | ✅ Spot-check em APOLICE-02: o teste agora executa o avaliador de produção nos dois ramos de cada critério |
| Spec-anchored outcome check | ✅ 6/6 com citação e valor igual ao da spec |
| Per-layer Coverage Expectation | ✅ Domínio 1:1 com os ACs; rotas cobrem feliz + `cancelada`/`suspensa`/`expirada` + 404 (duas origens, duas rotas) + 422 + snapshot divergente + **caminhos `False`** (L-061 atendida nas 3 camadas) |
| Every test maps to a spec requirement | ✅ Os 35 testes backend e 20 frontend da feature rastreiam a um AC, edge case ou Done-when |
| Documented guidelines followed | ✅ `AGENTS.md`, `README.md`, Test Coverage Matrix de `tasks.md:20-26` — a linha "Superfície de Apólice" agora tem a coluna "ausência de promessa de cobertura" atendida em **duas** frentes (aviso da UI + texto de produção do avaliador) |

**Nota de escopo (pré-existente, não regressão)**: `SuperficieApolice` não está ligada a
`App.tsx` nem a `PerfilContexto.tsx` — a superfície é inalcançável no shell, condição já
registrada como item (9) do `STATE.md` e comum a 5.1/5.2.

**Nota de lint**: `npm run lint` sai com código 0; a superfície nova acrescenta **1 warning**
ao conjunto pré-existente (`react(set-state-in-effect)`), mesmo padrão das superfícies
anteriores. Não bloqueante.

---

## Edge Cases

- [x] **Múltiplas coberturas, só uma relevante → a explicação destaca a avaliada, sem listar
  as demais** — ✅ **Coberto**. Frontend (o que o segurado vê):
  `SuperficieApolice.test.tsx:214-234` — a asserção é **delimitada à região** da explicação
  (`within(findByRole('region',{name:'Como sua apólice participou desta decisão'}))`),
  necessário porque `vendaval` aparece legitimamente na lista de Coberturas da apólice; a
  mutação MF5 (a seção passar a listar as coberturas da apólice) **morre**. Backend:
  `test_apolice_segurado_api.py:264-266`, com a ressalva da **nota A** (asserção presa à
  fixture). A propriedade visível ao segurado é verdadeira **e** protegida.
- [x] **Sem nenhuma execução histórica → dados cadastrais normais, sem seção de "uso
  preventivo" vazia** — ✅ **Coberto**: `SuperficieApolice.test.tsx:236-245` — `findByText('RES-0001')`
  presente, `queryByRole('heading',{name:'Como sua apólice participou desta decisão'})` ausente
  **e** `expect(getExplicacaoApoliceMock).not.toHaveBeenCalled()` (não há nem chamada de rede).
- [x] **`vigencia_fim` passado → `expirada`, distinto de `cancelada`/`suspensa`** — ✅
  **Coberto nas três camadas** (`test_apolice_segurado.py:190-191`,
  `test_apolice_segurado_api.py:187-188`, `SuperficieApolice.test.tsx:133`) **e agora também
  na fronteira exata**: `vigencia_fim == date.today()` → `ativa` (`test_apolice_segurado.py:205`)
  e `vigencia_fim == date.today() - 1 dia` → `expirada` (`:216`), ambos com data relativa.
  A distinção de `suspensa` é verificada por N1.

---

## Gate Check

- **Gate command (backend)**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`
- **Result**: **1043 passed**, 0 failed, 0 skipped; ruff `All checks passed!`;
  pyright `0 errors, 0 warnings, 0 informations` — **exit 0**
- **Gate command (frontend)**: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**: **374 passed** (37 arquivos), 0 failed, 0 skipped; lint exit 0 (warnings
  pré-existentes + 1 novo); `vite build ✓ built in 229ms` — **exit 0**
- **Test count antes da feature**: 1008 (backend) / 354 (frontend)
- **Test count após a rodada 1**: 1037 / 366
- **Test count após a rodada 2**: **1043 / 374**
- **Delta da feature**: **+35 backend / +20 frontend**
- **Delta desta rodada**: **+6 backend** (2 de fronteira de vigência, `suspensa` HTTP,
  canal/participação não-padrão, `atende=False`, justificativas reais do avaliador) /
  **+8 frontend** (6 no novo `apoliceSegurado.test.ts`, `suspensa`, Edge Case 1)
- **Test Integrity**: nenhum teste removido. O antigo
  `test_obter_explicacao_nunca_contem_palavra_de_cobertura…` **não foi apagado** — foi
  dividido em dois (`test_justificativas_reais_do_avaliador_…` sobre texto de produção +
  `test_obter_explicacao_repassa_a_justificativa_de_producao_sem_reescreve_la` sobre
  pass-through), ambos **mais fortes** que o original. Nenhuma asserção existente foi
  enfraquecida (verificado no diff completo `39491c8..HEAD`).
- **Skipped tests**: nenhum
- **Failures**: nenhuma

Ambos os gates passam, e desta vez o sensor também.

---

## Fix Plans

Nenhum fix bloqueante. Um item registrado como dívida menor, sem task de correção:

### Observação 1 (Minor, sem fix task): asserção backend do Edge Case 1 presa à fixture

- **O quê**: `test_apolice_segurado_api.py:264` (`"vendaval" not in valores_observados`) vale
  para a fixture escrita à mão, mas não para o `valor_observado` produzido por
  `avaliar()` (`"alagamento, vendaval"`).
- **Por que não é fix agora**: a propriedade da spec (a explicação destacar só a cobertura
  avaliada) é verdadeira e **testada** na superfície visível ao segurado, que renderiza apenas
  `operando` + `justificativa`; a justificativa de produção nomeia só a cobertura exigida.
- **Se alguém tocar nisso**: ou construir a fixture a partir de `avaliar()` e ajustar a
  asserção ao contrato real de `valor_observado`, ou trocá-la por uma asserção sobre a
  `justificativa` (que é o campo com essa garantia). Registrado como lição.

---

## Requirement Traceability Update

| Requirement | Rodada 1 | Rodada 2 |
| --- | --- | --- |
| APOLICE-01 | ⚠️ Needs Fix (Fix 2, 3, 6) | ✅ **Verified** |
| APOLICE-02 | ⚠️ Needs Fix (Fix 4, 5) | ✅ **Verified** |
| APOLICE-03 | ⚠️ Needs Fix (Fix 1, 6) | ✅ **Verified** |
| APOLICE-04 | ✅ Verified | ✅ **Verified** (reforçado por Fix 7) |
| APOLICE-05 | ✅ Verified | ✅ **Verified** |
| APOLICE-06 | ✅ Verified | ✅ **Verified** |

---

## Summary

**Overall**: ✅ **Ready**

**Spec-anchored check**: **6/6 ACs** com `file:line` e valor asserido igual ao da spec;
0 spec-precision gaps; 0 PASS parciais
**Sensor**: **12/12 mutações mortas** nesta rodada (7 re-injeções da rodada 1 + 6 novas —
uma delas, N1, contada uma vez mas morta em duas camadas); 26 injeções distintas acumuladas
na história, todas hoje mortas
**Gate**: backend 1043 passed / ruff 0 / pyright 0 (exit 0); frontend 374 passed / lint 0 /
build ok (exit 0)

**O que funciona**:
- **A fronteira de vigência** (`vigencia_fim == hoje` ainda é `ativa`; ontem já é `expirada`)
  agora é testada com data **relativa**, nos dois lados do `<`. O off-by-one real da rodada 1
  está fechado (M1 morto).
- **O cliente HTTP frontend** (`api/apoliceSegurado.ts`, 178 linhas) deixou de ser inteiramente
  mockado: 6 testes exercitam a tradução real com 10 campos em valores mutuamente distintos.
  Quatro mutações independentes de mapeamento morrem (MF6, MF7, N3, N4).
- **APOLICE-02 passou de garantia por inspeção a garantia por teste**: a varredura de palavras
  proibidas roda sobre ≥20 justificativas produzidas pelo `avaliador_elegibilidade` real,
  cobrindo o ramo negativo dos 4 critérios relevantes. Injetar `"garantimos a indenização"` na
  produção agora quebra a suíte (N2 morto).
- **L-061 atendida nas três camadas**: `participa_de_alertas`, `canal_preferido` e `atende`
  aparecem nos dois valores no serviço, no HTTP e no cliente. Fixar qualquer um deles como
  constante mata a suíte.
- **O Edge Case 1** ganhou asserção negativa **delimitada por região** — a escolha certa, já
  que `vendaval` aparece legitimamente na lista de Coberturas da apólice e uma busca de página
  inteira daria falso negativo.
- **A não-enumeração do `404`** agora fixa `codigo` e os dois status nas **duas** rotas, além
  de ser garantida por construção (um único construtor de `404` por rota).
- **APOLICE-05, a propriedade mais delicada da história**, segue coberta nas duas camadas com
  os testes alterando a apólice no banco *depois* de criar o snapshot.
- **Nenhum código de produção precisou mudar** — confirmação independente de que os 7 achados
  eram lacunas de discriminação de teste, não defeitos de comportamento.

**Issues found**: nenhum bloqueante. Uma observação menor (nota A): a asserção backend do
Edge Case 1 é presa à fixture e divergiria de dado real; a metade que o segurado vê está
correta e protegida.

**Next steps**: história pronta para fechamento. Atualizar a Requirement Traceability de
`spec.md` para `Verified` nos 6 requisitos e fechar a 5.3 no `STATE.md`.
