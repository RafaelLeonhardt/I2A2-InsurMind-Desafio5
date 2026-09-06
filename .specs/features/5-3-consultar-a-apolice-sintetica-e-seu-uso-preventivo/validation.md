# História 5.3: Consultar a apólice sintética e seu uso preventivo — Validation

**Date**: 2026-09-05
**Spec**: `.specs/features/5-3-consultar-a-apolice-sintetica-e-seu-uso-preventivo/spec.md`
**Diff range**: `d7285ae..HEAD` (`083dc5b`, `c56a654`, `3d76e73`, `39491c8`)
**Verifier**: sub-agente independente (autor ≠ verificador), somente leitura sobre a árvore real
**Rodada**: 1 de no máximo 3

**Veredito**: ❌ **FAIL** — os dois gates de Build saem com código 0 e todos os ACs têm
citação `file:line`, mas **7 de 20 injeções de falha de comportamento sobreviveram**. Quatro
delas são recorrências diretas de lições já confirmadas (L-061 ×3, L-059 ×2) e uma é um
off-by-one real na fronteira de vigência (`_estado_objetivo`) que nenhum teste detecta.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 `RepositorioApolices` | ✅ Done | `083dc5b`; desempate `criado_em DESC` exercitado com timestamps distintos (M4b morto) |
| T2 `ServicoApoliceSegurado` | ⚠️ Partial | `c56a654`; fronteira `vigencia_fim == hoje` nunca testada (M1 sobrevive) |
| T3 Endpoints HTTP | ⚠️ Partial | `3d76e73`; `_resposta_apolice`/`_resposta_criterio` com 3 campos sem valor discriminante (M5/M6/M7 sobrevivem) |
| T4 Superfície de Apólice | ⚠️ Partial | `39491c8`; `apoliceSegurado.ts` (178 linhas novas) é 100 % mockado — nenhum teste exercita o mapeamento (MF6/MF7 sobrevivem) |

Nenhuma task está bloqueada; os quatro commits landaram o que prometem (verificado lendo o
código, não a mensagem do commit).

---

## Spec-Anchored Acceptance Criteria

### P1: Dados da apólice e explicação de critérios sem promessa de cobertura

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| **APOLICE-01** — abrir Apólice exibe número, situação, vigência, endereço sintético, coberturas, canal preferencial e participação em alertas | Os 7 grupos de campos, vindos de dado real | Serviço: `src/backend/testes/test_apolice_segurado.py:138-147` — `assert apolice.numero == "RES-0001"`, `... tipo == "residencial"`, `... situacao == "ativa"`, `... estado_objetivo == "ativa"`, `... vigencia_inicio == date(2026,1,1)`, `... vigencia_fim == date(2030,12,31)`, `... endereco_risco_sintetico == "Rua Sintética, 123"`, `... coberturas == ("alagamento",)`, `... canal_preferido == "sms"`, `... participa_de_alertas is True` | ✅ PASS |
| **APOLICE-01** — contrato HTTP não mistura campos | Cada campo de `RespostaApolice` com o seu próprio valor | `src/backend/testes/test_apolice_segurado_api.py:126-135` — 10 asserções campo a campo (`corpo["coberturas"] == ["alagamento","vendaval"]`, `corpo["vigencia_inicio"] == "2026-01-01"`, `corpo["vigencia_fim"] == "2030-12-31"`, …) | ⚠️ **PASS parcial** — M13/M10 mortos, mas M5/M6/M7 sobrevivem (ver Sensor) |
| **APOLICE-01** — mesmos campos na interface | Visíveis na superfície | `src/frontend/src/funcionalidades/segurado/SuperficieApolice.test.tsx:84-91` — `findByText('RES-0001')`, `getByText('Residencial')`, `getByText('2026-01-01 a 2030-12-31')`, `getByText('Rua Sintética, 123')`, `getByText('alagamento')`, `getByText('vendaval')`, `getByText('SMS')`, `getByText('Participando')` | ✅ PASS |
| **APOLICE-01** — participação em alertas nos dois valores | `Participando` / `Não participando` | `SuperficieApolice.test.tsx:99-100` — `findByText('Não participando')`, `queryByText('Participando')).not.toBeInTheDocument()` | ✅ PASS (frontend); ❌ **sem par no backend** (M5) |
| **APOLICE-02** — explicação mostra como a categoria foi comparada, sem afirmação de cobertura/indenização/sinistro | Critérios comparados; nenhuma promessa | Filtro + conteúdo: `test_apolice_segurado_api.py:215-221` — `operandos == {"área afetada","tipo da apólice","situação da apólice","cobertura exigida"}`, `criterio_area["valor_observado"] == AREA`, `... ["atende"] is True`, `... ["justificativa"] == "Área da apólice corresponde à área do evento."`; aviso na UI: `SuperficieApolice.test.tsx:196-198` — `findByText(/não confirma cobertura, indenização nem decisão de sinistro/)` | ⚠️ **Spec-precision gap** — ver nota A |

### P1: Estados de apólice sem falha técnica e isolamento por segurado

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| **APOLICE-03** — apólice inativa/sem cobertura explicada objetivamente, sem virar falha técnica | Estado textual de domínio, sem indicador de erro | Serviço: `test_apolice_segurado.py:157-158` — `assert apolice.situacao == "cancelada"`, `... estado_objetivo == "cancelada"`; `:168` — `... estado_objetivo == "suspensa"`. HTTP: `test_apolice_segurado_api.py:148` — `resposta.json()["estado_objetivo"] == "cancelada"`. UI sem `role="alert"`: `SuperficieApolice.test.tsx:122-123` e `:133-134` — `findByText('Cancelada')` / `findByText('Expirada')` + `queryByRole('alert')).not.toBeInTheDocument()` | ✅ PASS (MF1 morto) — `suspensa` só coberta na camada de serviço |
| **APOLICE-04** — apólice inexistente ou de outro segurado: API impede, interface mostra `Não encontrada` sem expor outro registro | `None` no caso de uso; `404` idêntico nos dois casos; `Não encontrada` na UI | Serviço: `test_apolice_segurado.py:188` — `assert contexto.servico.obter(SEGURADO_ID) is None` (apólice existe, mas é de `OUTRO_SEGURADO_ID`); `:194` e `:201` — `obter_explicacao` devolve `None` nos dois casos. HTTP: `test_apolice_segurado_api.py:186-187` — `status_code == 404` e `codigo == "apolice_nao_encontrada"` para a apólice de outro segurado, idêntico ao `:170-172` do caso inexistente; `:254-256` — `corpo_outro["impacto"] == corpo_inexistente["impacto"]` e `... ["proxima_acao"] == ...`. UI: `SuperficieApolice.test.tsx:153-156` — `findByRole('heading',{name:'Não encontrada'})` + `getByText('Esta apólice não existe ou não pertence a você.')` | ✅ PASS (M15 morto) — ver nota B sobre a comparação campo a campo |

### P2: Snapshot histórico preservado apesar de mudança atual

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| **APOLICE-05** — explicação de comunicação histórica usa o snapshot da execução | Valor do snapshot, não o atual divergente | Serviço: `test_apolice_segurado.py:265-267` — após `UPDATE apolices SET situacao = 'cancelada'`, `assert situacao_no_snapshot_depois == situacao_no_snapshot_antes == "ativa"` **e** `assert apolice_atual.situacao == "cancelada"` (as duas metades, provando divergência real). HTTP: `test_apolice_segurado_api.py:278-282` — mesmo `UPDATE`, depois `criterio_situacao["valor_observado"] == "ativa"` com `status_code == 200` | ✅ PASS (M8 morto nas duas camadas) |
| **APOLICE-06** — a superfície atual indica que alterações afetam só decisões futuras | Aviso explícito na superfície | `SuperficieApolice.test.tsx:108-110` — `findByText(/afetam apenas decisões futuras/)`; produção em `SuperficieApolice.tsx:226-229` | ✅ PASS (MF4 morto) |

**Status**: ⚠️ 6/6 ACs com citação `file:line` e valor asserido igual ao definido pela spec;
**1 spec-precision gap** (APOLICE-02, nota A) e **1 PASS parcial** (APOLICE-01 HTTP, campos
não discriminados).

### Nota A — APOLICE-02: o teste backend de "sem promessa de cobertura" é vacuous

`test_apolice_segurado.py:229-231` monta `texto_completo` a partir de
`criterio.justificativa` e assere a ausência de `"indeniza"`, `"sinistro"`,
`"confirma cobertura"`, `"garantimos"`. Mas os `Criterio` vêm de `CRITERIOS_COMPLETOS`
(`:37-43`), **constantes escritas pelo próprio teste** — o teste prova que o autor do teste
não escreveu essas palavras, não que a produção não as escreve. `obter_explicacao` só repassa
`registro.criterios`; o texto real é produzido por `dominio/avaliador_elegibilidade.py`.

Verifiquei por inspeção as 10 strings de produção (`avaliador_elegibilidade.py:59-130`,
ramos positivo **e** negativo dos 5 critérios): nenhuma contém cobertura confirmada,
indenização ou decisão de sinistro. **A propriedade é verdadeira de fato**, mas não é
protegida por nenhum teste — qualquer futura redação de justificativa pode violá-la sem que
a suíte reaja. O único guarda-corpo real é o aviso da UI
(`SuperficieApolice.test.tsx:196-198`, MF3 morto), que cobre a metade "disclaimer" do AC,
não a metade "o texto do critério não promete".

### Nota B — APOLICE-04: a comparação de `404` não é campo a campo

`test_apolice_segurado_api.py:254-256` compara `impacto` e `proxima_acao` entre "não existe" e
"é de outro segurado", mas **não** compara `codigo` nem assere
`resposta_inexistente.status_code == 404`. `ocorrencia` difere legitimamente (ecoa o
`elegibilidade_id` pedido, que o solicitante já conhece) e `correlacao_id` é `uuid4()` por
ocorrência, por construção. Confirmei por leitura de `http/apolice_segurado.py:133-142` que
existe **um único** construtor de `404` para a explicação — não-enumeração garantida por
construção. Item menor, não bloqueante.

---

## Discrimination Sensor

Scratch isolado: `git worktree add /tmp/verify-5-3-scratch HEAD`; nenhum `git stash` usado.
`git status --porcelain` da árvore real: **vazio antes e vazio depois** (idêntico).
`git worktree list` após a limpeza mostra **apenas** a árvore principal em `39491c8 [main]`;
`/tmp/verify-5-3-scratch` não existe mais. Cada mutação foi verificada com
`assert src.count(old) == 1` antes de aplicar (uma primeira tentativa de mutar
`ORDER BY ... DESC` atingiu apenas a **docstring** por `count=1` e produziu um falso
"sobreviveu" — refeita como M4b, sobre o literal SQL, e morre).

| # | File:line | Description | Killed? |
| --- | --- | --- | --- |
| M1 | `aplicacao/apolice_segurado.py:90` | `vigencia_fim < hoje` → `<= hoje` (apólice que vence **hoje** passa a "expirada") | ❌ **Survived** |
| M2 | `aplicacao/apolice_segurado.py:90-91` | Ramo `expirada` desativado (`if False`) | ✅ Killed — `test_apolice_segurado_api.py:161` |
| M3 | `aplicacao/apolice_segurado.py:40-47` | `"participação em alertas"` acrescentado a `_OPERANDOS_RELEVANTES_A_APOLICE` | ✅ Killed — `test_apolice_segurado_api.py:215` |
| M4b | `persistencia/repositorio_apolices.py:68` | SQL `ORDER BY criado_em DESC` → `ASC` | ✅ Killed — `test_repositorio_apolices.py:106` |
| M5 | `http/apolice_segurado.py:157` | `participa_de_alertas=True` fixo | ❌ **Survived** |
| M6 | `http/apolice_segurado.py:168` | `atende=True` fixo | ❌ **Survived** |
| M7 | `http/apolice_segurado.py:157` | `canal_preferido="sms"` fixo | ❌ **Survived** |
| M8 | `aplicacao/apolice_segurado.py:167-172` | `obter_explicacao` sobrescreve `valor_observado` do critério "situação da apólice" com a situação **atual** da apólice | ✅ Killed — `test_apolice_segurado.py:265` **e** `test_apolice_segurado_api.py:282` (as duas camadas) |
| M9 | `http/apolice_segurado.py:151` | `situacao=apolice.estado_objetivo` | ✅ Killed — `test_apolice_segurado_api.py:160` |
| M10 | `http/apolice_segurado.py:153-154` | `vigencia_inicio`/`vigencia_fim` trocados | ✅ Killed — `test_apolice_segurado_api.py:130` |
| M13 | `http/apolice_segurado.py:149-150` | `numero`/`tipo` trocados | ✅ Killed — `test_apolice_segurado_api.py:126` |
| M14 | `http/apolice_segurado.py:169` | `justificativa=criterio.operando` | ✅ Killed — `test_apolice_segurado_api.py:221` |
| M15 | `aplicacao/apolice_segurado.py:164` | `obter_explicacao` deixa de checar `registro.segurado_id != segurado_id` | ✅ Killed — `test_apolice_segurado.py:201` **e** `test_apolice_segurado_api.py:254` |
| MF1 | `SuperficieApolice.tsx:180-182` | `role="alert"` no parágrafo do estado objetivo | ✅ Killed — `SuperficieApolice.test.tsx:123` e `:134` (2 testes) |
| MF2 | `SuperficieApolice.tsx:38` | Rótulo `expirada: 'Expirada'` removido (cai no fallback bruto) | ✅ Killed — `SuperficieApolice.test.tsx:133` |
| MF3 | `SuperficieApolice.tsx:255-258` | Aviso "não confirma cobertura, indenização nem decisão de sinistro" removido | ✅ Killed — `SuperficieApolice.test.tsx:197` |
| MF4 | `SuperficieApolice.tsx:226-229` | Aviso "afetam apenas decisões futuras" removido | ✅ Killed — `SuperficieApolice.test.tsx:109` |
| MF5 | `SuperficieApolice.tsx:259` | A lista da explicação passa a listar **todas** as coberturas da apólice, não só as avaliadas (viola o Edge Case 1) | ❌ **Survived** |
| MF6 | `api/apoliceSegurado.ts:92-93` | `paraApolice`: `numero`/`tipo` trocados | ❌ **Survived** (reconfirmado em 3 execuções) |
| MF7 | `api/apoliceSegurado.ts:113` | `paraCriterio`: `justificativa: corpo.operando` | ❌ **Survived** |

**Sensor depth**: expandido (20 injeções; piso do tier padrão: 1-3, do tier P0: 5)
**Result**: **13/20 killed, 7 survived** — ❌ **FAIL**

### Observação de robustez (fora do placar)

Durante a primeira execução de MF6 a suíte frontend acusou `1 failed | 365 passed` sem
apontar nome de teste; três reexecuções da mesma mutação deram `366 passed` (rc=0). O
resultado registrado é **SURVIVED** (o valor reprodutível). O falso negativo isolado indica
um teste **flaky** em algum ponto da suíte frontend — não identificado, não atribuído a esta
história, registrado aqui para quem investigar depois.

---

## Verificação das alegações específicas do autor

| Alegação | Veredito | Evidência independente |
| --- | --- | --- |
| "Fixtures com valores distintos **desde o início**, não como correção posterior" | ✅ **Verdadeira, e funcionou — parcialmente** | `git show c56a654` / `3d76e73`: `CRITERIOS_COMPLETOS` já nasce com 5 operandos e justificativas distintas; `criar_apolice` já nasce parametrizada por `situacao`/`vigencia_fim`; `criar_apolice` do teste HTTP já nasce com `coberturas=("alagamento","vendaval")` (duas, distintas) e `vigencia_inicio`/`vigencia_fim` distintas. Resultado empírico: **M9, M10, M13, M14 morrem** — exatamente a classe de mutante que sobreviveu em 5.1/5.2 (L-059). O caso `expirada` (`situacao="ativa"` + `estado_objetivo="expirada"`) é o que torna esses dois campos irmãos discrimináveis, e foi escrito na primeira passada. **Mas a disciplina parou nos campos `str`**: os três campos que só existem num valor (`participa_de_alertas`, `atende`, `canal_preferido`) continuam indiscriminados — L-061, não L-059 |
| `_estado_objetivo` testado nos 4 valores nas duas camadas | ❌ **Parcialmente falsa** | Serviço: 4/4 (`ativa` `:141`, `cancelada` `:158`, `suspensa` `:168`, `expirada` `:181`). HTTP: **3/4** — `suspensa` não tem teste HTTP. Frontend: 2/4 (`cancelada`, `expirada`); `suspensa` tem rótulo em `SuperficieApolice.tsx:37` sem nenhum teste. Fronteira `vigencia_fim == hoje`: **não testada em nenhuma camada** — M1 sobrevive |
| `obter_explicacao` nunca toca dado atual, testado nas duas camadas | ✅ **Verdadeira** | Os dois testes existem e **ambos** alteram a apólice no banco *depois* de criar o snapshot (`test_apolice_segurado.py:250-254`, `test_apolice_segurado_api.py:269-272`). M8 (vazamento deliberado do dado atual) morre nas duas. Além disso, por construção: `obter_explicacao` (`:155-172`) não referencia `self._portas.apolices` |
| Filtro exclui "participação em alertas" com prova positiva | ✅ **Verdadeira** | `test_apolice_segurado.py:213-217`: o critério **está** no snapshot bruto (`CRITERIOS_COMPLETOS:42`) e o teste assere igualdade de conjunto exata **mais** `"participação em alertas" not in operandos`. M3 morre |
| `404` idêntico entre "não existe" e "de outro segurado" | ⚠️ **Verdadeira na prática, testada em parte** | Ver nota B |
| Desempate "apólice mais recente" com `criado_em` distinguíveis | ✅ **Verdadeira** | `test_repositorio_apolices.py:93-99`: `criado_em` forçado a `2020-01-01` e `2030-01-01` (distintos, e invertidos em relação à ordem de inserção — o teste não passa por acidente de ordem física). M4b morre |
| Extensão de `RepositorioSegurados` é aditiva e não afeta 5.1 | ✅ **Verdadeira** | `git diff` de `repositorio_segurados.py`: `Segurado`, `buscar_por_id` e o `SELECT` original **inalterados byte a byte**; só há adição de `PreferenciasSegurado` e `buscar_preferencias_por_id`. Em `test_repositorio_segurados.py` a única mudança nos testes existentes é o `inserir_segurado` ganhar dois parâmetros **com default idêntico ao valor antigo** (`"whatsapp"`, `True`). `consultar_segurado_padrao` e `/segurados/padrao` não foram tocados; os 3 testes de 5.1 seguem verdes |
| Ausência de promessa de cobertura verificada sistematicamente | ❌ **Falsa** | Ver nota A — é spot-check sobre a fixture do próprio teste |
| Estado objetivo nunca renderizado como erro | ✅ **Verdadeira** | Verificado no DOM renderizado, não no comentário: `queryByRole('alert')` ausente em `cancelada` e `expirada`; MF1 (injeção de `role="alert"`) mata 2 testes |

---

## Code Quality

| Principle | Status |
| --- | --- |
| No features beyond what was asked | ✅ `buscar_por_id` em `RepositorioApolices` não é usado em produção, mas está explicitamente na interface do `design.md:61` e no Done-when de T1 |
| No abstractions for single-use code | ✅ `PortasApoliceSegurado` + 3 `Protocol` seguem o padrão de 5.1/5.2 |
| No unnecessary "flexibility" added | ✅ |
| Only touched files required for task | ✅ 17 arquivos, todos no escopo declarado |
| Didn't "improve" unrelated code | ✅ A extensão de `repositorio_segurados.py` é estritamente aditiva (verificado no diff) |
| Matches existing patterns/style | ✅ Roteador com `problem+json`, `422` para UUID inválido, docstrings em pt-BR, `RespostaX` com `extra="forbid"` |
| Would senior engineer approve? | ⚠️ Sim quanto à estrutura; não quanto à cobertura do cliente HTTP frontend (178 linhas novas, 0 exercitadas) |
| Tests map to ACs and are non-shallow | ⚠️ Spot-check em APOLICE-02: o teste backend é raso (nota A) |
| Spec-anchored outcome check | ⚠️ 6/6 com citação, 1 spec-precision gap |
| Per-layer Coverage Expectation | ⚠️ Domínio 1:1 com os ACs (10 testes); rotas cobrem feliz + `cancelada` + `expirada` + 404 (duas origens) + 422 + snapshot divergente — mas **falta o caminho `False`/`suspensa`** exigido por L-061 |
| Every test maps to a spec requirement | ✅ Os 29 testes backend e 12 frontend novos rastreiam a um AC ou edge case |
| Documented guidelines followed | ✅ `AGENTS.md`, `README.md`, Test Coverage Matrix de `tasks.md:20-26` — exceto a linha "Superfície de Apólice" da matriz, cujo item "ausência de promessa de cobertura" é atendido só pelo aviso da UI |

**Nota de escopo (pré-existente, não regressão)**: `SuperficieApolice` não está ligada a
`App.tsx` nem a `PerfilContexto.tsx` — a superfície é inalcançável no shell, condição já
registrada como item (9) do `STATE.md` e comum a 5.1/5.2.

**Nota de lint**: `npm run lint` sai com código 0, mas a superfície nova acrescenta **1
warning** ao conjunto pré-existente (`SuperficieApolice.tsx:133`,
`react(set-state-in-effect)`) — mesmo padrão das superfícies anteriores, não bloqueante.

---

## Edge Cases

- [ ] **Múltiplas coberturas, só uma relevante → a explicação destaca a avaliada, sem listar
  as demais** — ❌ **NÃO coberto por asserção**. A fixture HTTP tem duas coberturas
  (`test_apolice_segurado_api.py:83`) e o snapshot só cita `alagamento`, mas **nenhum teste
  assere a ausência de `vendaval` na explicação**. MF5 (fazer a explicação listar todas as
  coberturas da apólice) **sobrevive**. A propriedade vale hoje por construção, não por teste.
- [x] **Sem nenhuma execução histórica → dados cadastrais normais, sem seção de "uso
  preventivo" vazia** — coberto: `SuperficieApolice.test.tsx:208-212` — `findByText('RES-0001')`
  presente, `queryByRole('heading',{name:'Como sua apólice participou desta decisão'})` ausente
  **e** `expect(getExplicacaoApoliceMock).not.toHaveBeenCalled()` (não há nem chamada de rede).
- [x] **`vigencia_fim` passado → `expirada`, distinto de `cancelada`/`suspensa`** — coberto nas
  três camadas: `test_apolice_segurado.py:180-181`, `test_apolice_segurado_api.py:160-161`,
  `SuperficieApolice.test.tsx:133`. ⚠️ **Mas a fronteira do "passado" não é**: nenhum teste usa
  `vigencia_fim == date.today()`, e M1 (`<` → `<=`) sobrevive.

---

## Gate Check

- **Gate command (backend)**: `uv run --directory src/backend pytest && uv run --directory src/backend ruff check . && uv run --directory src/backend pyright`
- **Result**: **1037 passed**, 0 failed, 0 skipped; ruff `All checks passed!`;
  pyright `0 errors, 0 warnings, 0 informations` — **exit 0**
- **Gate command (frontend)**: `npm test --prefix src/frontend -- --run && npm run lint --prefix src/frontend && npm run build --prefix src/frontend`
- **Result**: **366 passed** (36 arquivos), 0 failed, 0 skipped; lint exit 0 (warnings
  pré-existentes + 1 novo, ver acima); `vite build` ✓ — **exit 0**
- **Test count before feature**: 1008 (backend) / 354 (frontend)
- **Test count after feature**: 1037 (backend) / 366 (frontend)
- **Delta**: **+29 backend** (5 repositório de apólices, 10 caso de uso, 12 rotas, 2
  preferências de segurado) / **+12 frontend** — nenhum teste removido, nenhuma asserção
  existente enfraquecida (verificado no diff de `test_repositorio_segurados.py`: só defaults
  aditivos)
- **Skipped tests**: nenhum
- **Failures**: nenhuma

Ambos os gates passam. O FAIL vem do sensor, não do gate.

---

## Fix Plans

### Fix 1 (Blocker): fronteira de vigência não discriminada — M1

- **Root cause**: `_estado_objetivo` (`aplicacao/apolice_segurado.py:90`) usa
  `vigencia_fim < hoje`, e os testes só usam datas muito no passado (`2020-01-01`) ou muito no
  futuro (`2030-12-31`). Trocar `<` por `<=` — que passaria a marcar como `expirada` uma
  apólice que **vence hoje**, ainda dentro da vigência pela definição da spec ("fora do período
  de vigência atual") — não quebra nenhum teste.
- **Fix task**: em `test_apolice_segurado.py`, acrescentar dois casos com data relativa:
  `vigencia_fim = date.today()` → `estado_objetivo == "ativa"`; e
  `vigencia_fim = date.today() - timedelta(days=1)` → `estado_objetivo == ESTADO_EXPIRADA`.
  Usar `date.today()` calculado no teste (não literal), para não expirar com o calendário.
- **Verify**: reaplicar M1 (`<` → `<=`) e confirmar que a suíte falha.
- **Priority**: Blocker (é a única regra de negócio nova com aritmética de data).

### Fix 2 (Blocker): mapeamento de campos do cliente HTTP frontend sem nenhuma cobertura — MF6/MF7

- **Root cause**: `src/frontend/src/api/apoliceSegurado.ts` (178 linhas novas:
  `paraApolice`, `paraCriterio`, `paraExplicacao`, `erroDeResultado`, `FALHA_DE_REDE`) é
  importado por um único teste, que o **mocka inteiro** (`SuperficieApolice.test.tsx:18-22`).
  Nenhum caminho de teste executa a tradução `snake_case → camelCase`. Trocar `numero` por
  `tipo` ou `justificativa` por `operando` no mapeamento não quebra nada.
- **Fix task**: criar `src/frontend/src/api/apoliceSegurado.test.ts` no padrão já existente de
  `contexto.test.ts` / `elegibilidade.test.ts` (9 dos módulos de `api/` têm esse teste; os de
  5.1/5.2 são a exceção): resposta `200` com **todos** os campos em valores mutuamente
  distintos, asserindo cada campo do objeto traduzido; `404` com corpo `problem+json`
  produzindo `ErroApoliceSegurado` com `status === 404` e `codigo` correto; e falha de rede
  (`fetch` lançando) produzindo `FALHA_DE_REDE`.
- **Verify**: reaplicar MF6 e MF7 e confirmar que a suíte falha.
- **Priority**: Blocker (L-059 recorrendo numa terceira camada).

### Fix 3 (Major): campos de valor único no contrato HTTP — M5/M6/M7

- **Root cause**: `participa_de_alertas`, `atende` e `canal_preferido` só aparecem com **um**
  valor em toda a suíte backend (`True`, `True`, `"sms"`). Fixá-los como constante em
  `_resposta_apolice`/`_resposta_criterio` não quebra nada. Exatamente L-061.
- **Fix task**: em `test_apolice_segurado_api.py`, acrescentar um caso com
  `criar_segurado(..., canal_preferido="whatsapp", participa_de_alertas=False)` (o helper
  `:62-73` **já aceita** os dois parâmetros — nenhum teste os usa) asserindo
  `corpo["participa_de_alertas"] is False` e `corpo["canal_preferido"] == "whatsapp"`; e um
  caso de explicação com um `Criterio(..., atende=False, ...)` no snapshot, asserindo
  `criterio["atende"] is False`. Espelhar o caso `atende=False` também em
  `test_apolice_segurado.py`.
- **Verify**: reaplicar M5, M6 e M7 e confirmar que a suíte falha nos três.
- **Priority**: Major.

### Fix 4 (Major): Edge Case 1 sem asserção negativa — MF5

- **Root cause**: nenhum teste assere que a explicação **não** lista as coberturas que não
  participaram da regra. A fixture já tem o material (`apoliceBase` com
  `['alagamento','vendaval']` e `explicacaoBase` citando só `alagamento`), mas falta a asserção.
- **Fix task**: em `SuperficieApolice.test.tsx`, no teste da explicação, delimitar a seção
  (`within(screen.getByRole('region',{name:'Como sua apólice participou desta decisão'}))`) e
  asserir `queryByText('vendaval')` **ausente** dentro dela, com `getByText('alagamento')`
  presente. Espelhar no backend: `test_apolice_segurado_api.py` já cria a apólice com duas
  coberturas — asserir que os `criterios` da explicação não mencionam `vendaval`.
- **Verify**: reaplicar MF5 e confirmar que a suíte falha.
- **Priority**: Major (é um edge case explicitamente listado na spec).

### Fix 5 (Minor): teste de "sem promessa de cobertura" é vacuous — nota A

- **Root cause**: `test_apolice_segurado.py:220-231` varre justificativas escritas pelo próprio
  teste; não toca no texto de produção.
- **Fix task**: mover a varredura de palavras proibidas para um teste sobre as justificativas
  **reais** — construir os `Criterio` via `avaliador_elegibilidade`, cobrindo os ramos
  atende/não-atende dos 4 operandos relevantes, e asserir a ausência das palavras no texto
  produzido. Manter a lista de palavras proibidas num único lugar.
- **Verify**: mutar uma justificativa de `avaliador_elegibilidade.py` para conter
  `"garantimos a indenização"` e confirmar que a suíte falha.
- **Priority**: Minor (a propriedade é verdadeira hoje; falta o guarda-corpo).

### Fix 6 (Minor): `suspensa` sem cobertura HTTP e frontend

- **Root cause**: `situacao='suspensa'` só é exercitada no caso de uso
  (`test_apolice_segurado.py:168`); o rótulo `suspensa: 'Suspensa'`
  (`SuperficieApolice.tsx:37`) não tem teste.
- **Fix task**: um caso HTTP com `situacao="suspensa"` asserindo
  `estado_objetivo == "suspensa"`, e um caso frontend asserindo `findByText('Suspensa')` +
  `queryByRole('alert')` ausente.
- **Verify**: remover a entrada `suspensa` do mapa de rótulos e confirmar falha.
- **Priority**: Minor.

### Fix 7 (Minor): comparação de `404` incompleta — nota B

- **Root cause**: `test_apolice_segurado_api.py:254-256` não compara `codigo` nem assere o
  status da segunda resposta.
- **Fix task**: acrescentar `assert resposta_inexistente.status_code == 404` e
  `assert corpo_outro["codigo"] == corpo_inexistente["codigo"] == "explicacao_nao_encontrada"`;
  fazer o mesmo par explícito para a rota da apólice.
- **Priority**: Minor.

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| APOLICE-01 | Implementing | ⚠️ Needs Fix (Fix 2, Fix 3, Fix 6) |
| APOLICE-02 | Implementing | ⚠️ Needs Fix (Fix 4, Fix 5) |
| APOLICE-03 | Implementing | ⚠️ Needs Fix (Fix 1, Fix 6) |
| APOLICE-04 | Implementing | ✅ Verified (Fix 7 opcional, menor) |
| APOLICE-05 | Implementing | ✅ Verified |
| APOLICE-06 | Implementing | ✅ Verified |

---

## Summary

**Overall**: ❌ Not Ready

**Spec-anchored check**: 6/6 ACs com `file:line` e valor asserido igual ao da spec;
1 spec-precision gap (APOLICE-02), 1 PASS parcial (APOLICE-01 no contrato HTTP)
**Sensor**: **13/20 mutations killed, 7 survived**
**Gate**: backend 1037 passed / ruff 0 / pyright 0 (exit 0); frontend 366 passed / lint 0 /
build ok (exit 0)

**What works**:
- A propriedade mais delicada da história — **APOLICE-05, o isolamento snapshot × dado atual**
  — está genuinamente coberta nas **duas** camadas, com os testes alterando a apólice no banco
  *depois* de criar o snapshot; a injeção de vazamento (M8) morre nos dois lugares.
- O filtro de critérios prova a **exclusão** de "participação em alertas", não só a presença
  dos quatro incluídos (M3 morto).
- A alegação do autor sobre valores de fixture distintos **desde o início** é verdadeira e
  matou a classe de mutante que sobreviveu em 5.1 e 5.2 (M9/M10/M13/M14) — L-059 não recorreu
  nos campos `str` do backend.
- A extensão de `RepositorioSegurados` é comprovadamente aditiva; nada de 5.1 mudou.
- O desempate de "apólice mais recente" é exercitado com `criado_em` distintos e invertidos em
  relação à ordem de inserção (M4b morto).
- `role="alert"` ausente para `cancelada`/`expirada` verificado no DOM renderizado (MF1 morto).

**Issues found** (ranqueadas): Fix 1 (fronteira `vigencia_fim == hoje`, Blocker) · Fix 2
(cliente HTTP frontend sem nenhuma cobertura, Blocker) · Fix 3 (3 campos de valor único no
contrato HTTP, Major) · Fix 4 (Edge Case 1 sem asserção negativa, Major) · Fix 5 (teste de
"sem promessa de cobertura" vacuous, Minor) · Fix 6 (`suspensa` sem cobertura HTTP/frontend,
Minor) · Fix 7 (comparação de `404` incompleta, Minor).

**Next steps**: rotear os 7 fixes a um implementador (Fix 1 e Fix 2 são bloqueantes) e
re-verificar — esta é a rodada 1 de no máximo 3.
