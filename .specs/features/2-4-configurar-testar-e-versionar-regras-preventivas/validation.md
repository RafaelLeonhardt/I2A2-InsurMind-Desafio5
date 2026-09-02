# História 2.4: Configurar, testar e versionar regras preventivas — Validation

**Date**: 2026-09-02
**Rodada**: **ROUND 1**
**Spec**: `.specs/features/2-4-configurar-testar-e-versionar-regras-preventivas/spec.md`
**Diff range**: `7121003..e0876e2` (5 commits — T1 `73d2409`, T2 `d11ddab`, T3 `8f13e99`, T4 `ea3efa0`, T5 `e0876e2`)
**Verifier**: sub-agente independente (author ≠ verifier) — read-only sobre a árvore real; mutações apenas em worktree descartável

**Verdict**: ❌ **FAIL**

O caminho de segurança central da história está **correto e comprovadamente discriminado**: concorrência otimista, mapeamento AD-013 e comparação de hash de idempotência foram mutados e os três mutantes morreram. Os gates estão todos verdes (334 backend / 186 frontend, `ruff`/`pyright`/`lint`/`build` limpos). O FAIL vem de **três mutantes sobreviventes** e de **uma AC sem nenhuma citação `file:line`** (REGRA-14, operação por teclado) — o protocolo é explícito: mutante sobrevivente vira fix task e não se marca a feature como concluída.

Nenhum defeito de comportamento em produção foi encontrado. Todos os achados são **lacunas de asserção** (os testes não detectam regressões que deveriam detectar) mais duas imprecisões de documentação/contrato.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 — `ValidadorRegra` | ✅ Done | Quatro classes de invalidez implementadas e agregadas sem parar na primeira falha (`validador_regra.py:160-166`). Faixa de `antecedencia_horas` sem exemplos limítrofes imediatos (ver M5 / REGRA-02) |
| T2 — `RepositorioRegras` escrita versionada | ✅ Done | `criar_nova_versao` faz `UPDATE`+`INSERT` numa transação com `BEGIN`/`COMMIT`/`ROLLBACK` (`repositorio_regras.py:129-160`); `ConflitoVersao` provado discriminante (M1) |
| T3 — `ServicoGestaoRegras` | ⚠️ Partial | Comportamento correto, mas a docstring (`gestao_regras.py:246-247`) e a `description` do OpenAPI (`http/regras.py:372`) afirmam que `ativar` "reexecuta o teste determinístico" — sonda do verificador mediu **0 chamadas a `avaliar` durante `ativar`**. O gate real é validação + existência de cenário, não a reexecução (ver Fix 6) |
| T4 — Roteador HTTP `regras` | ✅ Done | 4 rotas registradas em `composicao/api.py:96-99`, guardadas por `test_saude.py:42-45` e pela igualdade exata do snapshot OpenAPI (`test_openapi_sincronizado.py:35`) |
| T5 — Superfície "Regras" | ⚠️ Partial | Componente correto por construção, mas duas ACs suas ficaram sem asserção discriminante: REGRA-04 (ícone, M6 sobreviveu) e REGRA-14 (teclado, zero evidência) |

**Lacuna de integração declarada (não é defeito)**: `SuperficieRegras` não está montada em rota no `App.tsx` — `grep -rn "SuperficieRegras" src/frontend/src/App.tsx` → zero ocorrências. É o mesmo padrão já aceito para `SuperficieFonteMeteorologica` (2.1/2.2) e `SuperficieEventoDecisao` (2.3), declarado pelo autor em `tasks.md`/mensagens de commit. Registrado, não contado como lacuna.

---

## Spec-Anchored Acceptance Criteria

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + asserção | Result |
| --- | --- | --- | --- |
| **REGRA-01** — limiares e janelas SHALL originar de configuração versionada e legível, com padrões e justificativa documentados | Limiar e janela lidos de linha versionada de `regras`, com justificativa escrita | Config versionada: `repositorio_regras.py:93-115` (`listar`/`obter_por_id` com `versao`/`estado`); justificativa das faixas em `dominio/validador_regra.py:7,10,16` (docstrings de `LIMIAR_ANTECEDENCIA_*`, `CANAIS_VALIDOS`, `PRODUTO_ESPERADO_POR_EVENTO_TIPO`). Teste: `testes/test_repositorio_regras.py:107-119` — `nova.versao == 2`, `nova.estado == "ativa"`, `nova.limiar_meteorologico == 60.0`, `nova.canal == "email"`; `:152-155` — versão substituída conserva `limiar_meteorologico == 10.0` | ✅ PASS (nota D — justificativa só em docstring de código, não no README versionado do schema) |
| **REGRA-02** — os testes da regra SHALL incluir exemplos imediatamente **abaixo**, **sobre** e **acima** de cada fronteira relevante | Para cada fronteira nova (limiar `> 0`; antecedência `1..168`): um exemplo de cada lado imediato | Fronteira de antecedência: `test_validador_regra.py:109-116` — `validar(antecedencia_horas=1).valida is True` e `=168 → True` (**sobre**); `:98-106` — `antecedencia_horas=200` → erro (**acima, mas não imediato**). **Ausentes**: `0` (imediatamente abaixo de 1) e `169` (imediatamente acima de 168). Fronteira de limiar: `:84-95` — `0.0` → "maior que zero" (**sobre**); **ausente** `0.1` (imediatamente acima). Mutante **M5 sobreviveu** provando a lacuna | ❌ **GAP** |
| **REGRA-03** — a superfície SHALL exibir tipo de evento, severidade, limiar, área, tipo e situação da apólice, coberturas, antecedência, canal, versão e estado | As 10 informações visíveis por regra | Código: `SuperficieRegras.tsx:233-243` (11 `<th scope="col">`) e `:249-270` (células, com severidade derivada em `:37-45`). **Asserção**: `SuperficieRegras.test.tsx:64-77` só verifica os textos `Ativa`/`Substituída` e a presença de um `<svg>`; `:98-99` cobre 2 campos no formulário (`limiar`, `área`). Nenhum teste assere o conjunto de colunas, nem `severidade`, `cobertura`, `antecedência`, `canal` ou `versão` na tabela | ❌ **GAP** (código presente, evidência ausente — evidence-or-zero) |
| **REGRA-04** — a interface SHALL identificar a regra ativa por **texto, ícone e indicador visual** | Os três sinais presentes **e distintos** entre ativa e substituída | Código: `SuperficieRegras.tsx:263-268` (`CheckCircleIcon` vs `ClockCounterClockwiseIcon`), `:260-261` (`regra-estado-badge--{estado}` + `data-indicador`), CSS `SuperficieRegras.css:24-30`. **Asserção**: `SuperficieRegras.test.tsx:76` — `...closest('span')?.querySelector('svg')).toBeTruthy()` — prova apenas que **existe um** `<svg>`, não que os ícones **diferem**; `data-indicador` e a classe nunca são asseridos. Mutante **M6 sobreviveu** (dois ícones idênticos, 9/9 testes verdes) | ❌ **GAP** (reincidência literal da lição **L-024**) |
| **REGRA-05** — o formulário SHALL validar tipos, faixas, combinações obrigatórias e coerência evento↔produto | As 4 classes de invalidez, cada uma com campo identificado | `test_validador_regra.py:40-59` (tipo: `evento_tipo`, `apolice_tipo`), `:62-81` (tipo Python de `limiar`/`antecedencia`), `:84-106` (faixa), `:119-149` (combinação obrigatória: `area_aplicavel`, `cobertura_exigida`, `canal`), `:152-164` — coerência: `erro_coerencia.motivo` contém `"residencial"` **e** `"automovel"`; `:178-201` — `campos_com_erro == {7 campos}` (agregação, não para na primeira falha). Mutante **M1/M2**: M2 (troca do mapa AD-013) **morto** | ✅ PASS |
| **REGRA-06** — erro de validação SHALL aparecer junto ao campo **sem descartar os valores já informados** | Mensagem junto ao campo + demais valores preservados | `SuperficieRegras.test.tsx:164-169` — `findByText('Limiar meteorológico deve ser maior que zero.')`, `expect(campoLimiar).toHaveAttribute('aria-invalid','true')`, **`expect(getByLabelText('Cobertura exigida')).toHaveValue('cobertura-customizada')`** (valor digitado em outro campo sobrevive ao erro) e `Ativar` volta a `toBeDisabled()`. Backend: `test_regras_api.py:154-157` — `codigo == "configuracao_invalida"` + `erros[].campo == "limiar_meteorologico"` | ✅ PASS |
| **REGRA-07** — testar/ativar configuração inválida SHALL ser bloqueado com motivos específicos em PT-BR, **sem criar nenhuma nova versão ativa** | Bloqueio + motivo PT-BR + zero escrita | `test_gestao_regras.py:130-133` — `raises(ConfiguracaoInvalida)` com `erro.campo == "limiar_meteorologico"`; `:175-178` — `raises(...)` **e `regras.chamadas == []`** (prova de zero escrita); `:184-187` — idem para `NenhumCenarioAplicavel`. HTTP: `test_regras_api.py:154-157` (422 + código + erro por campo) e `:306-307` — `codigo == "nenhum_cenario_aplicavel"`. Motivos em PT-BR: `validador_regra.py:59,66,74,81,97,111,123,125,129,145` | ✅ PASS |
| **REGRA-08** — teste de configuração válida SHALL aplicar a regra deterministicamente aos cenários sintéticos, e a interface SHALL apresentar **operando, valor observado, resultado e justificativa** por caso | 4 colunas por critério, por cenário | Frontend (onde a AC exige a apresentação): `SuperficieRegras.test.tsx:127-132` — `getByText('área aplicável')`, `getByText('9990001')`, `getByText('Atende')`, `getByText('Área do evento corresponde à área aplicável da regra.')` — os quatro valores reais, dentro de `findByRole('region', {name:/Resultado do teste/})`. Tabela: `SuperficieRegras.tsx:454-457,461-467`. Backend: `test_regras_api.py:136-140` — `len(casos)==1`, `casos[0].relevante is True`, `len(criterios)==2` (contagem, sem os valores dos campos — ver nota A). Determinismo herdado de `AvaliadorRisco` (2.3, função pura) | ✅ PASS (nota A) |
| **REGRA-09** — ativar uma alteração testada SHALL criar nova versão imutável e torná-la ativa, **mantendo a anterior consultável e inalterada** | Nova linha `ativa` com `versao+1`; anterior `substituida`, consultável, com campos preservados | `test_repositorio_regras.py:107-119` — `nova.versao == 2`, `nova.estado == "ativa"`, `anterior.estado == "substituida"`, `ativa.id == nova.id`; `:140-155` — `listar` devolve as duas versões e a substituída conserva `limiar_meteorologico == 10.0`. HTTP: `test_regras_api.py:203-210` — `corpo["versao"] == 2`, `estado == "ativa"`, `limiar_meteorologico == 60.0`, e um `GET` subsequente devolve `estado == "substituida"` (nota B: nesse teste só o `estado` da anterior é asserido). Imutabilidade: `repositorio_regras.py:132-156` — o único `UPDATE` toca exclusivamente a coluna `estado` | ✅ PASS (nota B) |
| **REGRA-10** — execução iniciada antes da alteração SHALL conservar o snapshot da versão originalmente aplicada, sem recálculo silencioso | Avaliação anterior segue reportando `regra_id`/`regra_versao` antigos | Nenhuma asserção **nesta feature**. Evidência estrutural + herdada de 2.3: `avaliacoes_risco` guarda `regra_versao` como **valor**, não referência (`test_repositorio_avaliacoes_risco.py:57-58` — `avaliacao.regra_id == regra_id`, `avaliacao.regra_versao == 7`); `repositorio_avaliacoes_risco.py` só `INSERT`/`SELECT` (zero `UPDATE`/`DELETE`); `criar_nova_versao` insere linha **nova** com `id` novo (`repositorio_regras.py:127,141-156`) e nunca reescreve os campos da anterior. Nenhum teste de 2.4 exercita a sequência "avaliar → criar nova versão → reler a avaliação" | ⚠️ **Partial** — verificado por construção e por evidência herdada, não por teste desta história |
| **REGRA-11** — duas tentativas concorrentes com a mesma `versao_esperada` → só a primeira confirma, a segunda recebe `409` sem sobrescrever nem aplicar parcialmente | 1ª `200`, 2ª `409`, exatamente 2 linhas ao final | Caminho coberto: `test_regras_api.py:224-225` — `status_code == 409` e `codigo == "conflito_versao"` (versão obsoleta `99`); `test_repositorio_regras.py:128-137` — `raises(ConflitoVersao)` **e** `anterior.estado == "ativa"`, `anterior.versao == 1`, `len(listar()) == 1` (prova de não-mutação). **Sonda do verificador** (worktree, descartada): duas ativações `versao_esperada=1` com `Idempotency-Key` distintas → `200` depois `409 conflito_versao`, `listar` = `[(2,'ativa'),(1,'substituida')]`. Mutante **M1 morto**. O cenário literal de duas tentativas não existe como teste na suíte | ✅ PASS (nota C) |
| **REGRA-12** — ativação repetida com a mesma `Idempotency-Key` e conteúdo idêntico SHALL devolver a resposta registrada, sem criar outra versão | Corpo idêntico ao da 1ª resposta + zero versão extra | `test_regras_api.py:248-253` — `primeira.status_code == 200`, `segunda.status_code == 200`, **`primeira.json() == segunda.json()`** e `len(regras) == 2` (nenhuma versão extra). Serviço: `test_gestao_regras.py:211-212` — `segunda == primeira` e `len(regras.chamadas) == 1` | ✅ PASS |
| **REGRA-13** — mesma `Idempotency-Key` reusada com conteúdo diferente SHALL retornar `409` | `409` + nenhuma mutação | `test_regras_api.py:273-274` — `status_code == 409`, `codigo == "conflito_idempotencia"`; `test_gestao_regras.py:221-224` — `raises(ConflitoIdempotencia)` **e `len(regras.chamadas) == 1`**. Hash = SHA-256 do corpo bruto (`http/regras.py:429`). Mutante **M3 morto** | ✅ PASS |
| **REGRA-14** — navegar, editar e confirmar **só pelo teclado**: nomes acessíveis, foco visível, ordem lógica, sem depender de hover ou cor isolada | Interação por teclado exercitada; foco visível; distinção não dependente de cor | **Nenhuma citação `file:line`.** `SuperficieRegras.test.tsx` não usa `.tab()`, `keyboard()` nem `toHaveFocus()` — só `userEvent.click`. O projeto **já tem o precedente** em `SuperficieFonteMeteorologica.test.tsx:160-173` (`botao.focus()` → `toHaveFocus()` → `keyboard('{Enter}')` → asserção de efeito). Estruturalmente há base (`App.css:17` `button:focus-visible`, `SuperficieRegras.css:52-56`, `<label htmlFor>` em todos os campos, `aria-describedby`/`aria-invalid`), mas nada disso é asserido, e o sinal "não só cor" é justamente o que M6 mostrou não estar guardado | ❌ **GAP** (evidence-or-zero) |
| **REGRA-15** — o MVP SHALL oferecer consulta das versões necessárias à explicação e à auditoria, sem duplicação de regras nem gestão avançada de histórico | Listagem + detalhe por versão; nenhuma rota de duplicação/reversão | `test_regras_api.py:88-90` — `status_code == 200` e `len(corpo["regras"]) == 2` (ativa **e** substituída visíveis); `:99-103` — detalhe com `corpo["id"] == id_regra`, `limiar_meteorologico == 50.0`, `estado == "ativa"`; `:111-113` — `404` + `codigo == "regra_inexistente"`; `:123-124` — `422` + `codigo == "regra_id_invalido"`. Ausência de duplicação/reversão guardada por `test_saude.py:42-45` (conjunto **exato** de caminhos sob `/api/v1`) | ✅ PASS |

**Status**: ❌ **Gaps presentes** — 11/15 ACs casam com o resultado definido pela spec; **3 GAPs** (REGRA-02, REGRA-03, REGRA-04, REGRA-14 → 4 GAPs) e 1 Partial (REGRA-10). Nenhum **spec-precision gap**: a spec 2.4 define resultado preciso para todas as 15 ACs; as lacunas são de asserção, não de imprecisão da spec.

Contagem final: **10 PASS**, **4 GAP** (REGRA-02, REGRA-03, REGRA-04, REGRA-14), **1 Partial** (REGRA-10).

### Notas de julgamento

**A — REGRA-08 no backend.** `test_regras_api.py:140` assere `len(criterios) == 2` mas nenhum valor de `operando`/`valor_observado`/`justificativa` do corpo HTTP. A AC exige a apresentação na **interface**, e o teste de frontend (`:127-132`) assere os quatro valores — por isso PASS. Ainda assim, o contrato HTTP dessas quatro chaves não tem asserção de valor própria (o precedente de 2.3 tinha: `test_avaliacao_risco_api.py:75-78`). Registrado como Fix 8 (Minor).

**B — REGRA-09 "inalterada".** O teste HTTP de ativação (`test_regras_api.py:209-210`) assere só `estado == "substituida"` na versão anterior; não assere que `limiar_meteorologico` continua `50.0`. A imutabilidade dos demais campos é coberta indiretamente por `test_repositorio_regras.py:155` (numa linha inserida já como `substituida`, não numa linha efetivamente substituída pelo `UPDATE`). Estruturalmente seguro — o `UPDATE` só toca `estado` — mas a asserção não é a mais forte possível.

**C — REGRA-11 cenário literal.** A AC descreve duas tentativas concorrentes com a **mesma** `versao_esperada`. A suíte cobre o caminho equivalente (`versao_esperada=99` obsoleta), que exercita exatamente o mesmo ramo de código. A sonda do verificador confirmou o comportamento literal (`200` → `409`, 2 linhas). Não é lacuna de comportamento, e sim de fidelidade do cenário de teste ao texto da AC.

**D — REGRA-01 documentação.** A justificativa das faixas novas (antecedência 1..168h, canais válidos, mapa AD-013) vive em docstrings de `dominio/validador_regra.py`, não no `adaptadores/persistencia/README.md` — o "documento versionado do schema operacional" que a lição **L-022** manda usar. É a mesma família de risco do Fix 6 ainda aberto de 2.3. Não bloqueia: a AC pede "documentados", e docstrings são documentação legível e versionada.

**E — `antecedencia_horas` sem asserção de valor.** Nenhum teste de 2.4 assere o valor de `antecedencia_horas` atravessando a escrita e a leitura (`inserir_regra` fixa `24`; a ativação envia `48` e ninguém o lê de volta). Uma troca de coluna no `INSERT`/desserialização seria parcialmente detectada por tipos, não por valor.

---

## Discrimination Sensor

Worktree isolada única (`git worktree add --detach <scratch> e0876e2`), revertida com `git checkout --` entre mutações e removida com `git worktree remove --force` ao final. O `node_modules` do frontend foi apenas **symlinkado** para dentro da worktree e removido antes da remoção — nada foi escrito na árvore real.

| # | Mutação | File:line | Descrição | Testes executados | Killed? |
| --- | --- | --- | --- | --- | --- |
| **M1** | Concorrência otimista desarmada | `adaptadores/persistencia/repositorio_regras.py:133-135` | Removida a cláusula `AND versao = ?` (e o parâmetro) do `UPDATE`: qualquer `versao_esperada` passa a substituir a regra ativa | `test_repositorio_regras.py`, `test_regras_api.py`, `test_gestao_regras.py` | ✅ **Killed** — 2 falhas: `test_criar_nova_versao_com_versao_esperada_incorreta_levanta_conflito_sem_mutar` e `test_post_ativar_versao_esperada_desatualizada_retorna_409` (`assert 200 == 409`) |
| **M2** | Mapa de coerência AD-013 trocado | `dominio/validador_regra.py:13-14` | `chuva_intensa → automovel`, `granizo → residencial` (inversão do par exigido) | `test_validador_regra.py`, `test_gestao_regras.py`, `test_regras_api.py` | ✅ **Killed** — falhas em cascata, incluindo `test_granizo_associado_a_apolice_residencial_produz_erro_de_coerencia`, `test_chuva_intensa_associada_a_apolice_automovel_produz_erro_de_coerencia` e 7 testes de rota |
| **M3** | Comparação de hash de idempotência quebrada | `aplicacao/gestao_regras.py:255` | `if registrada.hash_requisicao != hash_requisicao:` → `if False:` — qualquer corpo passa a receber a resposta registrada | `test_gestao_regras.py`, `test_regras_api.py` | ✅ **Killed** — `test_ativar_mesma_chave_com_hash_diferente_levanta_conflito_idempotencia` e `test_post_ativar_mesma_chave_com_corpo_diferente_retorna_409` (`assert 200 == 409`) |
| **M4** | Filtro de proveniência removido | `adaptadores/persistencia/repositorio_meteorologia.py:176` | Removido `AND proveniencia = 'sintetico'` — eventos **reais** passam a entrar no teste determinístico da regra | **Suíte backend completa** (334 testes) | ❌ **Survived** — 334 passed. Nenhum teste insere um evento não sintético e verifica que ele fica de fora |
| **M5** | Off-by-one nas duas fronteiras de antecedência | `dominio/validador_regra.py:104-106` | `range(MIN, MAX + 1)` → `range(MIN - 1, MAX + 2)`: `0h` e `169h` passam a ser aceitos | **Suíte backend completa** (334 testes) | ❌ **Survived** — 334 passed. Os testes usam `1`, `168` (sobre) e `200` (bem acima), nunca `0` nem `169` |
| **M6** | Distinção de ícone colapsada | `funcionalidades/regras/SuperficieRegras.tsx:266` | `<ClockCounterClockwiseIcon>` → `<CheckCircleIcon>`: ativa e substituída passam a mostrar **o mesmo ícone** | `SuperficieRegras.test.tsx` | ❌ **Survived** — 9/9 passed. `:76` só verifica que existe **um** `<svg>` na badge ativa |

### Sonda adicional (não é mutação — verificação de comportamento, worktree descartada)

| Sonda | Pergunta | Resultado medido |
| --- | --- | --- |
| **P1** | Duas ativações da mesma regra com a **mesma** `versao_esperada=1` e `Idempotency-Key` distintas (cenário literal de REGRA-11) | `200` depois `409 conflito_versao`; `listar` = `[(2,'ativa'),(1,'substituida')]` — **comportamento correto**, apenas não coberto por teste |
| **P2** | `ativar` chama de fato `avaliar` (a docstring afirma "reexecuta o teste determinístico")? | **0 chamadas.** `ativar` revalida e checa que existe ao menos um cenário aplicável, mas nunca executa o motor de avaliação — docstring e `description` do OpenAPI overclaimam (Fix 6) |

**Sensor depth**: lightweight-plus (6 mutações — 3 no caminho de segurança de maior risco, 3 nos caminhos de menor confiança) + 2 sondas de comportamento

**Result**: **3/6 killed, 3 survived** — ❌ **FAIL**

**Verificação de isolamento**: `git status --porcelain` vazio **antes** (`BASELINE:[]`) e **depois** (`POST-SENSOR STATUS:[]`) de todo o ciclo; `git worktree list` mostra apenas a árvore real em `e0876e2`. Nenhum resíduo, nenhum `git stash` usado.

---

## Payload / Conjunction Rule

Regra aplicada: a asserção precisa olhar **valor devolvido e/ou estado persistido**, não "a chamada aconteceu" nem um status isolado.

| Alvo | Asserção verifica valor real? | Evidência |
| --- | --- | --- |
| `GET /api/v1/regras` | ⚠️ Parcial | `test_regras_api.py:88-90` — status **+** `len(regras) == 2`. Nenhum campo de nenhuma regra é asserido; ordenação (`ORDER BY evento_tipo, versao DESC`) não é asserida |
| `GET /api/v1/regras/{id}` 200 | ✅ Sim | `:99-103` — status **+** `id`, `limiar_meteorologico == 50.0`, `estado == "ativa"` |
| `GET /api/v1/regras/{id}` 404 / 422 | ✅ Sim | `:111-113` — status + `content-type: application/problem+json` + `codigo == "regra_inexistente"`; `:123-124` — `codigo == "regra_id_invalido"` |
| `POST .../testar` 200 | ⚠️ Parcial | `:136-140` — status **+** `len(casos)==1`, `relevante is True`, `len(criterios)==2`. Os valores de `operando`/`valor_observado`/`justificativa` não são asseridos no corpo HTTP (nota A) |
| `POST .../testar` 200 vazio | ✅ Sim | `:173-174` — status **+** `casos == []` (lista vazia explícita, não um erro técnico) |
| `POST .../testar` 422 | ✅ Sim | `:154-157` — status + `codigo` + `erros[].campo == "limiar_meteorologico"` |
| `POST .../ativar` 200 | ✅ Sim | `:203-210` — status **+** `versao == 2`, `estado == "ativa"`, `limiar_meteorologico == 60.0` **+ estado persistido relido**: `GET` da anterior devolve `estado == "substituida"` (nota B) |
| `POST .../ativar` idempotente | ✅ Sim | `:248-253` — **`primeira.json() == segunda.json()`** (corpo inteiro) **e** `len(regras) == 2` (ausência de efeito colateral asserida) |
| `POST .../ativar` 409 (versão / idempotência) | ✅ Sim | `:224-225` e `:273-274` — status **+** `codigo` discriminando as duas causas |
| `POST .../ativar` 404 / 422 | ✅ Sim | `:286-287`, `:186-187`, `:306-307` — status + `codigo` específico em cada caso |
| `ServicoGestaoRegras.ativar` — efeito de escrita | ✅ Sim | `test_gestao_regras.py:199` — `regras.chamadas[0] == (regra_anterior_id, 1, DADOS_CHUVA_VALIDOS)` (tupla de argumentos reais); `:178,187,224` — `chamadas == []` / `len == 1` para provar **ausência** de escrita |
| `RepositorioRegras.criar_nova_versao` | ✅ Sim | `test_repositorio_regras.py:107-119` — objeto devolvido **e** três releituras do banco (`obter_por_id`, `obter_ativa`, `listar`) |
| Superfície — ativação | ✅ Sim | `SuperficieRegras.test.tsx:191-196` — mensagem de sucesso **e** `ativarRegra` chamado com `(id, versao, objectContaining({limiarMeteorologico: 50}))` |

Duas asserções ficam em "só contagem" (`GET /regras`, `criterios` do teste) — registradas como Fix 8 (Minor). Nenhuma asserção do tipo "status isolado" foi encontrada.

---

## Code Quality

| Princípio | Status |
| --- | --- |
| Minimum code | ✅ — nenhuma migração nova (o schema do Épico 1 já versiona); `AvaliadorRisco` de 2.3 reusado sem alteração como motor do teste, sem segunda implementação de avaliação |
| Surgical changes | ✅ — apenas os arquivos das 5 tasks + `composicao/api.py` (registro de rota), `test_saude.py` (conjunto exato de caminhos) e `repositorio_meteorologia.py` (+1 método necessário ao caso de uso) |
| No scope creep | ✅ — nenhuma rota de duplicação/reversão de regra; `listar`/`obter_por_id` são exatamente o que REGRA-15 delimita |
| Matches patterns | ✅ — `ConflitoVersao` espelha o padrão de `RepositorioExecucaoPreventiva` (2.2); `problema()`/`problem+json` e `Idempotency-Key` seguem os roteadores existentes; `Protocol`s de porta seguem `aplicacao/avaliacao_risco.py` |
| Spec-anchored outcome check | ❌ — 10/15 ACs com asserção casando o resultado da spec; 4 GAPs e 1 Partial |
| Per-layer Coverage Expectation | ⚠️ — domínio 1:1 com as classes de invalidez ✅; rota cobre feliz + vazio + 404 + 422 (×4 causas) + 409 (×2 causas) ✅; **componente não cobre teclado (REGRA-14) nem o conjunto de colunas (REGRA-03)** |
| Every test maps to a spec requirement | ✅ — todos os arquivos de teste novos citam os IDs `REGRA-NN` no docstring de módulo; nenhum teste órfão |
| Documented guidelines followed | ⚠️ — `AGENTS.md` e o padrão de 2.2/2.3 seguidos; a justificativa das faixas novas não chegou ao README versionado do schema (nota D, mesma família da lição **L-022** e do Fix 6 aberto de 2.3) |
| Docstring/contrato correspondem ao comportamento | ❌ — `gestao_regras.py:246-247` e `http/regras.py:372` afirmam reexecução do teste determinístico em `ativar`; sonda P2 mediu 0 chamadas a `avaliar` (Fix 6) |

---

## Edge Cases

- [x] **Ativar combinação evento↔produto inconsistente → bloqueio com motivo específico antes do teste** — `test_validador_regra.py:152-164` (granizo + residencial; motivo cita ambos os produtos), `test_regras_api.py:154-157` (bloqueio na rota com `erros[].campo`). Mutante M2 morto confirma discriminação
- [x] **Teste sem nenhum cenário sintético aplicável → resultado vazio válido, não erro técnico, e ativação segue bloqueada** — `test_gestao_regras.py:145-150` (`resultados == ()`), `:153-168` (filtragem por tipo), `test_regras_api.py:173-174` (`200` + `casos == []`), e o bloqueio da ativação em `:306-307` (`422 nenhum_cenario_aplicavel`) + `test_gestao_regras.py:184-187` (`regras.chamadas == []`). Frontend: `SuperficieRegras.tsx:443-444` ("Nenhum cenário sintético é aplicável…") — **não coberto por teste de frontend**
- [x] **Ativação idêntica reenviada depois de a resposta ter sumido da UI (chave ainda válida) → resposta originalmente registrada** — `test_regras_api.py:250` (`primeira.json() == segunda.json()`) + `:252-253` (`len(regras) == 2`); serviço em `test_gestao_regras.py:211-212`
- [ ] **Cenário sintético vs. evento real** — não é edge case listado na spec, mas M4 revelou que a fronteira "só sintético" não tem guarda de teste; um evento real do mesmo tipo entraria silenciosamente no teste determinístico da regra

---

## Gate Check

- **Gate command (Build)**: `uv run pytest -q && uv run ruff check . && uv run pyright` (em `src/backend`) + `npx vitest run && npm run lint && npm run build` (em `src/frontend`)
- **Executado nesta rodada pelo próprio Verificador** (não herdado do orquestrador):
  - `pytest`: **334 passed**, 0 failed, 0 skipped (exit 0)
  - `ruff check .`: **All checks passed!**
  - `pyright`: **0 errors, 0 warnings, 0 informations**
  - `vitest run`: **186 passed** em 22 arquivos, 0 failed (exit 0)
  - `npm run lint`: exit 0 — 10 warnings, **todas pré-existentes de `react-hooks`/fast-refresh**; a única em arquivo desta história é `SuperficieRegras.tsx:89` (`set-state-in-effect`), o mesmo padrão já aceito em `SuperficieEventoDecisao.tsx:79`, `SuperficieProntidao.tsx:84` e `SuperficieFonteMeteorologica.tsx:149`
  - `npm run build`: **✓ built in 224ms** (exit 0)
- **Test count antes da feature** (fim de 2.3, `7121003`): 292 backend / 164 frontend
- **Test count após a feature** (`e0876e2`): **334 backend / 186 frontend**
- **Delta**: **+42 backend** (`test_validador_regra` +15, `test_gestao_regras` +10, `test_regras_api` +13, `test_repositorio_regras` +4) / **+22 frontend** (`regras.test.ts` +13, `SuperficieRegras.test.tsx` +9)
- **Test Integrity**: a contagem **só cresceu**; nenhum teste removido; nenhuma asserção enfraquecida no diff `7121003..e0876e2` (`test_saude.py` foi **fortalecido** — o conjunto exato de caminhos ganhou as 4 rotas novas)
- **Skipped**: nenhum
- **Failures**: nenhuma

---

## Fix Plans

Ordenados por severidade. Fix 1–3 são os bloqueadores do FAIL (mutantes sobreviventes + AC sem evidência).

### Fix 1: Asserir a operação por teclado da superfície Regras (REGRA-14) — **Major**

- **Root cause**: `SuperficieRegras.test.tsx` exercita a superfície inteira por `userEvent.click`. Nenhuma asserção de foco, ordem de tabulação ou ativação por `{Enter}`/`{Space}` — apesar de o projeto já ter o padrão pronto em `SuperficieFonteMeteorologica.test.tsx:160-173`. REGRA-14 fica sem qualquer citação `file:line`, e por evidence-or-zero conta como não coberta.
- **Fix task**: em `SuperficieRegras.test.tsx`, um caso que (a) foca o botão `Editar` da regra ativa e assere `toHaveFocus()`, (b) abre o formulário com `keyboard('{Enter}')`, (c) tabula pelos campos asserindo a ordem lógica (limiar → área → apólice → cobertura → antecedência → canal → Testar → Ativar → Cancelar), (d) dispara `Testar` por teclado e assere o painel de resultado. Verificar: o teste falha se `tabIndex`/ordem do DOM for alterada.
- **Priority**: Major

### Fix 2: Asserir que o ícone **distingue** ativa de substituída (REGRA-04) — **Major**

- **Root cause**: `SuperficieRegras.test.tsx:76` prova apenas a **presença** de um `<svg>` na badge ativa. Como as duas badges renderizam um `<svg>`, colapsar os dois ícones no mesmo símbolo não é detectado — mutante **M6 sobreviveu**. É a reincidência literal da lição **L-024**, fechada em 2.3 e reaberta aqui.
- **Fix task**: adotar o padrão já validado em 2.3 — atributo `data-icone-nome` em cada ícone de `SuperficieRegras.tsx:264,266` e, no teste, coletar os nomes das duas linhas e asserir `new Set(nomes).size === 2`. Asserir também `data-indicador` (`:261`) e a classe `regra-estado-badge--{estado}` para cobrir o "indicador visual" da AC. Verificar: reaplicar M6 e confirmar que agora morre.
- **Priority**: Major

### Fix 3: Exemplos imediatamente abaixo/acima de cada fronteira do validador (REGRA-02) — **Major**

- **Root cause**: `test_validador_regra.py` cobre `1` e `168` (sobre) e `200` (bem acima), mas nunca `0` nem `169`; e `0.0` (sobre) mas nunca `0.1`. Alargar a faixa em uma unidade nos **dois** extremos não é detectado — mutante **M5 sobreviveu**. REGRA-02 exige literalmente "exemplos imediatamente abaixo, sobre e acima de cada fronteira relevante".
- **Fix task**: acrescentar em `test_validador_regra.py` os casos `antecedencia_horas` `0` → inválido, `1` → válido, `168` → válido, `169` → inválido; e `limiar_meteorologico` `-0.1` → inválido, `0.0` → inválido, `0.1` → válido. Verificar: reaplicar M5 e confirmar que morre.
- **Priority**: Major

### Fix 4: Guardar o filtro de cenários **sintéticos** (M4) — **Major**

- **Root cause**: `repositorio_meteorologia.py:176` filtra `proveniencia = 'sintetico'` — decisão explícita da spec ("reutiliza o conjunto sintético de demonstração já semeado") e do design. Nenhum teste insere um evento **real** do mesmo tipo, então remover o filtro deixa a suíte inteira verde (334 passed). Um evento real entraria no teste determinístico da regra sem que nada acusasse.
- **Fix task**: um teste (em `test_repositorio_meteorologia.py` ou `test_regras_api.py`) que insere um evento `proveniencia='real'` **e** um `'sintetico'` do mesmo `tipo`, e assere que `listar_sinteticos_por_tipo` (ou `POST .../testar`) devolve **exatamente 1 caso**, com o `evento_id` do sintético. Verificar: reaplicar M4 e confirmar que morre.
- **Priority**: Major

### Fix 5: Asserir o conjunto de atributos exibido pela tabela (REGRA-03) — **Minor**

- **Root cause**: a AC enumera 10 informações; o componente as renderiza (`SuperficieRegras.tsx:233-243,249-270`), mas nenhum teste assere o conjunto de colunas nem os valores de `severidade`, `cobertura`, `antecedência`, `canal` e `versão`. Remover uma coluna passa despercebido.
- **Fix task**: em `SuperficieRegras.test.tsx`, asserir `getAllByRole('columnheader').map(th => th.textContent)` contra a lista exata e, dentro da linha da regra ativa, asserir os valores derivados (`≥ 50 mm acumulados`, `24h`, `WhatsApp`, `Residencial`, `1`).
- **Priority**: Minor

### Fix 6: Corrigir a afirmação de "reexecuta o teste determinístico" em `ativar` — **Minor**

- **Root cause**: `gestao_regras.py:246-247` e a `description` publicada no OpenAPI (`http/regras.py:372`, e portanto em `composicao/openapi.json`) afirmam que `ativar` "revalida e reexecuta o teste determinístico". A sonda P2 mediu **0 chamadas** a `avaliar` durante `ativar`: o gate real é `validar` + existência de ao menos um cenário aplicável. O comportamento é defensável (o teste não tem veredito aprovado/reprovado), mas o texto é factualmente falso — e um deles é **contrato publicado**.
- **Fix task**: escolher **uma** das duas: (a) ajustar docstring e `description` para "revalida a configuração e exige ao menos um cenário sintético aplicável"; ou (b) executar de fato `self._portas.avaliar` sobre os cenários em `ativar`, com um teste que assere a chamada. Se (a), regenerar `openapi.json` e manter `test_openapi_sincronizado.py` verde.
- **Priority**: Minor

### Fix 7: Cobrir o cenário literal de REGRA-11 e a preservação de snapshot de REGRA-10 — **Minor**

- **Root cause**: REGRA-11 é testada pelo caminho equivalente (`versao_esperada=99`), não pelas duas tentativas com a **mesma** versão; REGRA-10 não tem nenhum teste nesta história (só evidência estrutural + herdada de 2.3). O comportamento de ambos foi confirmado correto pela sonda P1 e por leitura de código, mas não está guardado contra regressão futura.
- **Fix task**: (a) portar a sonda P1 para `test_regras_api.py` — duas ativações `versao_esperada=1` com chaves distintas, asserindo `200`/`409 conflito_versao` e `listar` com exatamente 2 linhas; (b) um teste que salva uma avaliação de risco, cria nova versão da regra e relê a avaliação, asserindo `regra_id`/`regra_versao` **antigos** inalterados.
- **Priority**: Minor

### Fix 8: Asserções de valor faltantes no contrato HTTP — **Minor**

- **Root cause**: `GET /api/v1/regras` assere só `len(regras) == 2` (nenhum campo, nenhuma ordenação); `POST .../testar` assere `len(criterios) == 2` sem os valores de `operando`/`valor_observado`/`justificativa` — abaixo do padrão que 2.3 estabeleceu em `test_avaliacao_risco_api.py:75-78`. `antecedencia_horas` nunca tem seu valor asserido atravessando escrita+leitura (nota E).
- **Fix task**: fortalecer as duas asserções para incluir valores e ordenação, e asserir `antecedencia_horas == 48` na resposta de ativação.
- **Priority**: Minor

---

## Lições candidatas (grounding para `.specs/lessons.json`)

| Origem fundamentada | Lição proposta |
| --- | --- |
| M6 sobreviveu (REGRA-04) | **L-024 reincidiu.** A lição existente ("quando um requisito exige distinção por texto, ícone e cor, asserir que os três sinais **diferem** entre categorias") deve ser promovida de `candidate` a estabelecida — é a segunda superfície consecutiva em que a asserção de ícone testa presença em vez de distinção |
| M5 sobreviveu (REGRA-02) | Ao testar uma faixa fechada, usar os quatro valores `min-1`, `min`, `max`, `max+1` — um exemplo "bem fora" da faixa não detecta off-by-one na fronteira |
| M4 sobreviveu | Todo filtro `WHERE` que implementa uma decisão de escopo da spec precisa de um teste com **uma linha que o filtro exclui**; sem ela o filtro pode ser removido sem que nada falhe |
| REGRA-14 sem evidência | Uma AC de acessibilidade/teclado precisa de asserção de interação (`focus`/`tab`/`keyboard`), não de estrutura — a existência de `label`, `aria-*` e CSS `:focus-visible` não é evidência de operabilidade |
| Sonda P2 | Uma docstring ou `description` de OpenAPI que afirma um efeito (“reexecuta X”) deve ser guardada por um teste desse efeito, ou reescrita para o que o código faz |

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| REGRA-01 | Implementing | ✅ Verified |
| REGRA-02 | Implementing | ❌ Needs Fix (Fix 3) |
| REGRA-03 | Implementing | ❌ Needs Fix (Fix 5) |
| REGRA-04 | Implementing | ❌ Needs Fix (Fix 2) |
| REGRA-05 | Implementing | ✅ Verified |
| REGRA-06 | Implementing | ✅ Verified |
| REGRA-07 | Implementing | ✅ Verified |
| REGRA-08 | Implementing | ✅ Verified |
| REGRA-09 | Implementing | ✅ Verified |
| REGRA-10 | Implementing | ⚠️ Verified por construção/herança (Fix 7) |
| REGRA-11 | Implementing | ✅ Verified |
| REGRA-12 | Implementing | ✅ Verified |
| REGRA-13 | Implementing | ✅ Verified |
| REGRA-14 | Implementing | ❌ Needs Fix (Fix 1) |
| REGRA-15 | Implementing | ✅ Verified |

---

## Summary

**Overall**: ⚠️ **Issues** — não pronto para fechar sem os Fix 1–4

**Spec-anchored check**: 10/15 ACs com asserção casando exatamente o resultado definido pela spec; **4 GAPs** (REGRA-02, REGRA-03, REGRA-04, REGRA-14) + 1 Partial (REGRA-10). **Zero spec-precision gaps** — a spec 2.4 define resultado preciso para as 15 ACs
**Sensor**: **3/6 mutantes mortos, 3 sobreviventes** (M4 filtro sintético, M5 off-by-one de faixa, M6 distinção de ícone)
**Gate**: 334 backend + 186 frontend passed, 0 failed, 0 skipped; `ruff`/`pyright`/`lint`/`build` verdes — todos re-executados pelo Verificador

**O que funciona**: o núcleo de segurança da história está correto e **comprovadamente discriminado**. A concorrência otimista é real — o `UPDATE ... WHERE id = ? AND versao = ? AND estado = 'ativa' RETURNING versao` dentro de `BEGIN`/`COMMIT` decide o vencedor no banco, não em Python, e a sonda P1 confirmou o cenário literal da AC (`200` → `409`, exatamente duas linhas ao final). A idempotência AD-002 devolve o **corpo inteiro** registrado e assere ausência de versão extra. O `ValidadorRegra` agrega todas as quatro classes de invalidez sem parar na primeira falha, com mensagens em PT-BR por campo, e o formulário preserva os demais valores digitados — asserido com um valor não trivial (`cobertura-customizada`). O `AvaliadorRisco` de 2.3 é reusado sem alteração, então não há segunda implementação de avaliação para divergir. Nenhuma migração nova foi necessária. O conjunto exato de caminhos sob `/api/v1` é guardado por teste, e o snapshot OpenAPI por igualdade exata — o contrato não pode divergir em silêncio. Nenhum teste foi removido ou enfraquecido.

**Problemas encontrados**: todos são **lacunas de asserção**, não defeitos de produção. (1) REGRA-14 (operação por teclado) não tem uma única citação `file:line` — o arquivo de teste da superfície não usa `focus`/`tab`/`keyboard`, apesar de o projeto já ter o padrão pronto em `SuperficieFonteMeteorologica.test.tsx:160-173`. (2) REGRA-04 repete a lição **L-024**: o teste prova que existe um `<svg>`, não que os ícones diferem — colapsar os dois ícones deixa os 9 testes verdes. (3) REGRA-02 pede explicitamente exemplos imediatamente abaixo/sobre/acima de cada fronteira, e a faixa de antecedência pode ser alargada em uma unidade nos dois extremos sem que nada falhe. (4) O filtro `proveniencia = 'sintetico'` — decisão explícita de escopo da spec — pode ser removido com a suíte inteira verde. Somam-se dois itens menores: a docstring e a `description` publicada no OpenAPI afirmam que `ativar` reexecuta o teste determinístico, e a sonda mediu 0 chamadas ao avaliador; e o conjunto de colunas da tabela (REGRA-03) nunca é asserido.

**Next steps**: rotear **Fix 1–4** (Major) como fix tasks para um implementador e re-verificar — são todos testes novos ou fortalecidos, sem mudança de comportamento de produção, exceto a escolha (a)/(b) do Fix 6. Fix 5, 7 e 8 (Minor) podem acompanhar a mesma rodada, já que tocam os mesmos arquivos. Após as correções, reinjetar M4, M5 e M6 e confirmar que os três morrem antes de declarar a história concluída. Esta é a iteração 1 de no máximo 3.
