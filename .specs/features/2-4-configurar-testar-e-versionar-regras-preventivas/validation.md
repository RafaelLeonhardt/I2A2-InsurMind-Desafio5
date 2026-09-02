# História 2.4: Configurar, testar e versionar regras preventivas — Validation

**Date**: 2026-09-02
**Rodada**: **ROUND 2** (re-verificação após as correções da Round 1)
**Spec**: `.specs/features/2-4-configurar-testar-e-versionar-regras-preventivas/spec.md`
**Diff range**: `7121003..6b33e16` (6 commits — T1 `73d2409`, T2 `d11ddab`, T3 `8f13e99`, T4 `ea3efa0`, T5 `e0876e2` + correção `6b33e16`)
**Diff das correções em isolado**: `e0876e2..6b33e16`
**Verifier**: sub-agente independente (author ≠ verifier), **distinto do verificador da Round 1** — read-only sobre a árvore real; mutações apenas em worktrees descartáveis

**Verdict**: ❌ **FAIL** (por margem estreita — **um único mutante sobrevivente, severidade Minor**)

**Histórico**: Round 1 (`7121003..e0876e2`) → ❌ FAIL (4 GAPs + 1 Partial; 3/6 mutantes sobreviveram) → Fix 1–8 aplicados pelo orquestrador em `6b33e16` → Round 2 (este relatório) → ❌ FAIL com **um** item aberto.

As oito correções foram verificadas **na árvore real, uma a uma**, sem aceitar o sumário do orquestrador. **Sete estão genuinamente fechadas e comprovadas por mutação**: os três mutantes sobreviventes da Round 1 (M4, M5, M6) foram reinjetados e **os três morreram**, e três mutações **novas** — inclusive a que desfaz literalmente a mudança de produção do Fix 6 — também morreram. O Fix 6 é a única mudança de comportamento de produção da rodada e está correto: `ativar` agora **realmente** reexecuta o teste determinístico, tornando verdadeiras a docstring e a `description` publicada no OpenAPI.

O FAIL vem de **um resto do Fix 2**: a tarefa de correção da Round 1 pedia asserção dos **três** sinais de REGRA-04 (texto, ícone, indicador visual); só dois foram implementados. Uma mutação nova (**M10**) que colapsa o **indicador visual** — remove a classe modificadora `regra-estado-badge--{estado}` e o `data-indicador` — deixa os 12 testes da superfície verdes. É uma correção de uma linha; nenhum defeito de comportamento em produção foi encontrado nesta rodada.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 — `ValidadorRegra` | ✅ Done | Faixa `[1, 168]` agora com os quatro valores de fronteira (`test_validador_regra.py:109-130`); mutante M5 morto |
| T2 — `RepositorioRegras` escrita versionada | ✅ Done | `criar_nova_versao` inalterado nesta rodada; ganhou a guarda de REGRA-10 (`test_repositorio_regras.py:168-202`) |
| T3 — `ServicoGestaoRegras` | ✅ Done | Era ⚠️ Partial na Round 1. `ativar` agora delega a `self.testar(...)` (`gestao_regras.py:264-266`), então a promessa de "reexecuta o teste determinístico" (`gestao_regras.py:246`, `http/regras.py:372`) passou a ser verdadeira — guardada por teste de espião (`test_gestao_regras.py:218-237`) e confirmada pelo mutante **M7 morto** |
| T4 — Roteador HTTP `regras` | ✅ Done | Inalterado; snapshot OpenAPI segue idêntico (`test_openapi_sincronizado.py`) e o conjunto exato de caminhos segue guardado (`test_saude.py:42-45`) |
| T5 — Superfície "Regras" | ⚠️ Partial | Teclado (REGRA-14) e conjunto de colunas (REGRA-03) agora asseridos e **comprovadamente discriminantes** (M9, M8 mortos); ícones distintos por `data-icone-nome` (M6 morto). Resta o **indicador visual** de REGRA-04 sem asserção (M10 sobreviveu) |
| Fix 1–8 (Verifier Round 1) | ⚠️ 7 fechados, 1 parcial | Verificados um a um abaixo |

**Lacuna de integração declarada (não é defeito, inalterada)**: `SuperficieRegras` continua não montada em rota no `App.tsx` — `grep -rn "SuperficieRegras" src/frontend/src/App.tsx` → zero ocorrências. Mesmo padrão já aceito para `SuperficieFonteMeteorologica` (2.1/2.2) e `SuperficieEventoDecisao` (2.3), declarado pelo autor em `tasks.md`. Registrado, não contado como lacuna.

---

## Verificação das correções da Round 1

| Fix | O que Round 1 pediu | Verificação independente (Round 2) | Resultado |
| --- | --- | --- | --- |
| **Fix 1 (Major)** — REGRA-14, operação por teclado | Foco asserido, ativação por `{Enter}`, efeito observável | `SuperficieRegras.test.tsx:252-281` — `botaoEditar.focus()` → `expect(botaoEditar).toHaveFocus()` (`:266-267`) → `usuario.keyboard('{Enter}')` (`:268`) → `findByLabelText('Limiar meteorológico')` + `toHaveFocus()` (`:270-272`) → `botaoTestar.focus()` + `toHaveFocus()` (`:274-276`) → `{Enter}` (`:277`) → `findByText(/Resultado do teste determinístico/)` e `testarRegra` chamado 1× (`:279-280`). Mesmo padrão de `SuperficieFonteMeteorologica.test.tsx:160-173`. **Não é superficial**: mutante **M9** (trocar `<button>` por `<span role="button" tabIndex>`, focável mas ativável só por mouse) **morre** exatamente em `:270`. Não cobre ordem de tabulação (`.tab()`), item menor do plano original | ✅ **Fechado** (com nota F) |
| **Fix 2 (Major)** — REGRA-04, três sinais distintos | `data-icone-nome` **e** asserção de `data-indicador` / classe `regra-estado-badge--{estado}` | Metade feita: `SuperficieRegras.tsx:264,271` — `data-icone-nome="check-circle"` / `"clock-counter-clockwise"`; `SuperficieRegras.test.tsx:79-97` — `expect(iconeAtiva).not.toBe(iconeSubstituida)` (`:96`). Mutante **M6 reinjetado e morto**. **Porém**: `grep -n "data-indicador\|regra-estado-badge\|toHaveClass" SuperficieRegras.test.tsx` → **zero ocorrências**. Mutante **M10 sobreviveu** — remover a classe modificadora e o `data-indicador` deixa 12/12 testes verdes | ⚠️ **Parcialmente fechado** — bloqueia o PASS |
| **Fix 3 (Major)** — REGRA-02, fronteiras imediatas | `0` inválido, `1` válido, `168` válido, `169` inválido | `test_validador_regra.py:109-120` — `validar(antecedencia_horas=0).valida is False` **e** `erro.campo == "antecedencia_horas"`; idem para `169`. Complementa `:123-130` (`1` e `168` válidos) e `:98-106` (`200`). Mutante **M5 reinjetado e morto** em `:117`. Fronteira do limiar: `-5.0` (`:195`), `0.0` (`:87`, "maior que zero") e valores válidos acima — os três lados cobertos (nota G) | ✅ **Fechado** |
| **Fix 4 (Major)** — filtro `proveniencia = 'sintetico'` | Um teste com uma linha que o filtro exclui | `test_repositorio_meteorologia.py:92-123` — insere `SINTETICO` **e** `REAL_INMET` do mesmo `CHUVA_INTENSA` e assere `[evento.id for evento in resultado] == [sintetico.id]` (identidade, não contagem); `:126-154` — filtro por tipo, `== [granizo.id]`. Mutante **M4 reinjetado e morto** em `:123` | ✅ **Fechado** |
| **Fix 5 (Minor)** — REGRA-03, conjunto de colunas | `getAllByRole('columnheader')` contra a lista exata + valores derivados | `SuperficieRegras.test.tsx:99-130` — `expect(cabecalhos).toEqual([...11 rótulos...])` (`:108-120`) e, na linha da regra ativa, `Chuva intensa`, `9990001`, `Residencial`, `alagamento`, `24h`, `WhatsApp`, `1` (`:123-129`). Mutante novo **M8** (remover a coluna `Severidade` e sua célula) **morre** em `:108` | ✅ **Fechado** |
| **Fix 6 (Minor)** — `ativar` "reexecuta o teste determinístico" | Opção (a) reescrever o texto **ou** (b) executar de fato, com teste da chamada | Opção (b), por **reuso**: `gestao_regras.py:264-266` substituiu 6 linhas duplicadas (validar + listar cenários) por `casos = self.testar(regra_anterior_id, dados)` + `if not casos: raise NenhumCenarioAplicavel(...)`. `testar` (`:213-236`) chama `self._portas.avaliar` por cenário, então a docstring (`:246`) e a `description` do OpenAPI (`http/regras.py:372`) passaram a descrever o que o código faz. Guarda: `test_gestao_regras.py:218-237` — espião injetado via `PortasGestaoRegras.avaliar` (`gestao_regras.py:148-150`), `assert len(chamadas) == 1` e `chamadas[0][0] is evento` (identidade do cenário). Mutante novo **M7** (reverter `ativar` à lógica antiga sem avaliar) **morre** em `:236` (`assert 0 == 1`). Sem regressão: `NenhumCenarioAplicavel` e `ConfiguracaoInvalida` continuam nas mesmas condições (`test_gestao_regras.py:174-191`, `test_regras_api.py:334`), `openapi.json` inalterado | ✅ **Fechado** |
| **Fix 7 (Minor)** — REGRA-11 literal + REGRA-10 | Duas ativações com a mesma `versao_esperada=1`; e avaliação relida após nova versão | REGRA-11: `test_regras_api.py:239-269` — mesmo corpo com `versao_esperada: 1` e `Idempotency-Key` distintas (`chave-concorrente-1/2`), `primeira.status_code == 200` **e `versao == 2`**, `segunda.status_code == 409` **e `codigo == "conflito_versao"`**, mais `len(regras) == 2` e `{versões} == {1, 2}` (ausência de escrita parcial). REGRA-10: `test_repositorio_regras.py:168-202` — salva avaliação com `regra_versao=1`, chama `criar_nova_versao(..., versao_esperada=1)`, relê e assere `regra_id == UUID(id_regra)`, `regra_versao == 1`, `relevante is True`, `criterios == resultado.criterios` (tupla inteira com justificativas) | ✅ **Fechado** |
| **Fix 8 (Minor)** — asserções de valor no contrato HTTP | `GET /regras` com campos; `testar` com valores dos critérios; `antecedencia_horas` no round-trip | `test_regras_api.py:91-94` — `estados == {"ativa","substituida"}` e `versoes == {1,2}` (não mais só `len == 2`); `:143-151` — `caso["motivo"] == "relevante"`, `criterio_intensidade["valor_observado"] == "72.5 mm"`, `atende is True`, `"60.0 mm" in justificativa`. **Não feito**: `antecedencia_horas == 48` continua sem asserção no round-trip HTTP (nota E persiste); a ordenação de `GET /regras` continua não asserida (conjuntos, não listas) | ⚠️ **Majoritariamente fechado** (resto é Minor, nota E) |

---

## Spec-Anchored Acceptance Criteria

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + asserção | Result |
| --- | --- | --- | --- |
| **REGRA-01** — limiares e janelas SHALL originar de configuração versionada e legível, com padrões e justificativa documentados | Limiar e janela lidos de linha versionada de `regras`, com justificativa escrita | Config versionada: `repositorio_regras.py:93-115` (`listar`/`obter_por_id` com `versao`/`estado`); justificativa das faixas em `dominio/validador_regra.py:7,10,16`. Teste: `test_repositorio_regras.py:107-119` — `nova.versao == 2`, `nova.estado == "ativa"`, `nova.limiar_meteorologico == 60.0`, `nova.canal == "email"`; `:152-155` — versão substituída conserva `limiar_meteorologico == 10.0`. HTTP: `test_regras_api.py:91-94` — `estados == {"ativa","substituida"}`, `versoes == {1,2}` (reforçado nesta rodada) | ✅ PASS (nota D — justificativa em docstring de código, não no README versionado do schema) |
| **REGRA-02** — os testes da regra SHALL incluir exemplos imediatamente **abaixo**, **sobre** e **acima** de cada fronteira relevante | Para cada fronteira: um exemplo de cada lado imediato | Antecedência `[1,168]`: `test_validador_regra.py:114-120` — `0` → `valida is False` + `campo == "antecedencia_horas"`; `169` → idem; `:126-130` — `1` e `168` → `valida is True`; `:98-106` — `200` (bem acima). Limiar `> 0`: `:195` (`-5.0`, abaixo), `:87-95` (`0.0`, sobre, "maior que zero"), `DADOS_CHUVA_VALIDOS` (`50.0`, acima). Mutante **M5 morto** | ✅ **PASS** (era ❌ GAP; nota G) |
| **REGRA-03** — a superfície SHALL exibir tipo de evento, severidade, limiar, área, tipo e situação da apólice, coberturas, antecedência, canal, versão e estado | As informações visíveis por regra | `SuperficieRegras.test.tsx:105-120` — `expect(cabecalhos).toEqual(['Tipo de evento','Severidade','Limiar','Área','Apólice','Cobertura','Antecedência','Canal','Versão','Estado','Ação'])` (igualdade **exata** e ordenada); `:123-129` — na linha da ativa, `Chuva intensa`, `9990001`, `Residencial`, `alagamento`, `24h`, `WhatsApp`, `1`. Código: `SuperficieRegras.tsx:233-243,249-270`. Mutante **M8 morto** | ✅ **PASS** (era ❌ GAP; nota H — valores de `Severidade` e `Limiar` não asseridos na célula, só como coluna) |
| **REGRA-04** — a interface SHALL identificar a regra ativa por **texto, ícone e indicador visual** | Os três sinais presentes **e distintos** entre ativa e substituída | **Texto** ✅: `SuperficieRegras.test.tsx:71-72,76` — `queryByText('Ativa')` / `queryByText('Substituída')` em linhas distintas. **Ícone** ✅: `SuperficieRegras.tsx:264,271` (`data-icone-nome`), `test.tsx:94-96` — `iconeAtiva` truthy, `iconeSubstituida` truthy, `expect(iconeAtiva).not.toBe(iconeSubstituida)`; mutante **M6 morto**. **Indicador visual** ❌: `SuperficieRegras.tsx:259-260` renderiza `regra-estado-badge--${regra.estado}` + `data-indicador={regra.estado}` (CSS distinto em `SuperficieRegras.css:24-30`), mas `grep "data-indicador\|regra-estado-badge\|toHaveClass"` no arquivo de teste → **zero ocorrências**. Mutante **M10 sobreviveu** (12/12 verdes com os dois badges visualmente idênticos) | ⚠️ **Partial** — 2 de 3 sinais asseridos e discriminados; o terceiro sem evidência (Fix 9) |
| **REGRA-05** — o formulário SHALL validar tipos, faixas, combinações obrigatórias e coerência evento↔produto | As 4 classes de invalidez, cada uma com campo identificado | `test_validador_regra.py:40-59` (tipo do domínio), `:62-81` (tipo Python), `:84-130` (faixa, agora com as 4 fronteiras), `:133-164` (combinação obrigatória), `:166-190` (coerência: motivo cita `"residencial"` **e** `"automovel"`), `:192-215` — `campos_com_erro == {7 campos}` (agregação sem parar na primeira falha). Mutante **M2 morto** (Round 1) | ✅ PASS |
| **REGRA-06** — erro de validação SHALL aparecer junto ao campo **sem descartar os valores já informados** | Mensagem junto ao campo + demais valores preservados | `SuperficieRegras.test.tsx:189-223` — `findByText('Limiar meteorológico deve ser maior que zero.')`, `toHaveAttribute('aria-invalid','true')`, **`getByLabelText('Cobertura exigida')` com `'cobertura-customizada'`** (valor digitado em outro campo sobrevive), `Ativar` volta a `toBeDisabled()`. Backend: `test_regras_api.py:154-169` — `codigo == "configuracao_invalida"` + `erros[].campo == "limiar_meteorologico"` | ✅ PASS |
| **REGRA-07** — testar/ativar configuração inválida SHALL ser bloqueado com motivos específicos em PT-BR, **sem criar nenhuma nova versão ativa** | Bloqueio + motivo PT-BR + zero escrita | `test_gestao_regras.py:129-137` — `raises(ConfiguracaoInvalida)` com `erro.campo == "limiar_meteorologico"`; `:174-182` — `raises(...)` **e `regras.chamadas == []`**; `:184-191` — idem para `NenhumCenarioAplicavel`. HTTP: `test_regras_api.py:154-169`, `:334-347` (`codigo == "nenhum_cenario_aplicavel"`). Motivos PT-BR: `validador_regra.py:59,66,74,81,97,111,123,125,129,145`. **Reforçado**: a validação de `ativar` agora passa por `testar` (`gestao_regras.py:264`), então o bloqueio é o mesmo caminho de código nas duas operações | ✅ PASS |
| **REGRA-08** — teste de configuração válida SHALL aplicar a regra deterministicamente aos cenários sintéticos, e a interface SHALL apresentar **operando, valor observado, resultado e justificativa** por caso | 4 colunas por critério, por cenário | Frontend: `SuperficieRegras.test.tsx:156-188` — `getByText('área aplicável')`, `getByText('9990001')`, `getByText('Atende')` e a justificativa completa, dentro de `findByRole('region', {name:/Resultado do teste/})`. Backend (reforçado nesta rodada): `test_regras_api.py:143-151` — `motivo == "relevante"`, `valor_observado == "72.5 mm"`, `atende is True`, `"60.0 mm" in justificativa`. Cenários **só sintéticos**: `test_repositorio_meteorologia.py:123` (M4 morto). Determinismo herdado de `AvaliadorRisco` (2.3, função pura) | ✅ PASS (nota A fechada) |
| **REGRA-09** — ativar uma alteração testada SHALL criar nova versão imutável e torná-la ativa, **mantendo a anterior consultável e inalterada** | Nova linha `ativa` com `versao+1`; anterior `substituida`, consultável, com campos preservados | `test_repositorio_regras.py:107-119` — `nova.versao == 2`, `nova.estado == "ativa"`, `anterior.estado == "substituida"`, `ativa.id == nova.id`; `:144-160` — `listar` devolve as duas versões e a substituída conserva `limiar_meteorologico == 10.0`; `:197-202` (novo) — os campos de uma avaliação ligada à versão anterior seguem intactos após a substituição. HTTP: `test_regras_api.py:214-221`. Imutabilidade: `repositorio_regras.py:132-156` — o único `UPDATE` toca exclusivamente `estado` | ✅ PASS (nota B) |
| **REGRA-10** — execução iniciada antes da alteração SHALL conservar o snapshot da versão originalmente aplicada, sem recálculo silencioso | Avaliação anterior segue reportando `regra_id`/`regra_versao` antigos | **Teste desta história** (novo): `test_repositorio_regras.py:168-202` — salva `ResultadoAvaliacaoRisco` com `regra_versao=1`, executa `criar_nova_versao(..., versao_esperada=1)`, relê por `obter_por_execucao` e assere `regra_id == UUID(id_regra)`, `regra_versao == 1`, `relevante is True`, `criterios == resultado.criterios`. Estrutural: `repositorio_avaliacoes_risco.py` só `INSERT`/`SELECT`; `criar_nova_versao` insere linha nova (`repositorio_regras.py:127,141-156`) | ✅ **PASS** (era ⚠️ Partial) |
| **REGRA-11** — duas tentativas concorrentes com a mesma `versao_esperada` → só a primeira confirma, a segunda recebe `409` sem sobrescrever nem aplicar parcialmente | 1ª `200`, 2ª `409`, exatamente 2 linhas ao final | **Cenário literal** (novo): `test_regras_api.py:239-269` — mesmo corpo com `versao_esperada: 1`, chaves de idempotência distintas; `primeira.status_code == 200`, `primeira.json()["versao"] == 2`, `segunda.status_code == 409`, `codigo == "conflito_versao"`, `len(regras) == 2`, `{versões} == {1,2}`. Caminho equivalente: `:235-236`; repositório: `test_repositorio_regras.py:126-141` (`raises(ConflitoVersao)` + `anterior.estado == "ativa"` + `len(listar()) == 1`). Mutante **M1 morto** (Round 1) | ✅ **PASS** (nota C fechada) |
| **REGRA-12** — ativação repetida com a mesma `Idempotency-Key` e conteúdo idêntico SHALL devolver a resposta registrada, sem criar outra versão | Corpo idêntico ao da 1ª resposta + zero versão extra | `test_regras_api.py:272-298` — `primeira.status_code == 200`, `segunda.status_code == 200`, **`primeira.json() == segunda.json()`** e `len(regras) == 2`. Serviço: `test_gestao_regras.py:205-216` — `segunda == primeira` e `len(regras.chamadas) == 1` | ✅ PASS |
| **REGRA-13** — mesma `Idempotency-Key` reusada com conteúdo diferente SHALL retornar `409` | `409` + nenhuma mutação | `test_regras_api.py:300-319` — `status_code == 409`, `codigo == "conflito_idempotencia"`; `test_gestao_regras.py:240-250` — `raises(ConflitoIdempotencia)` **e `len(regras.chamadas) == 1`**. Hash = SHA-256 do corpo bruto (`http/regras.py:429`). Mutante **M3 morto** (Round 1) | ✅ PASS |
| **REGRA-14** — navegar, editar e confirmar **só pelo teclado**: nomes acessíveis, foco visível, ordem lógica, sem depender de hover ou cor isolada | Interação por teclado exercitada; foco visível; distinção não dependente de cor | `SuperficieRegras.test.tsx:252-281` — `botaoEditar.focus()` + `toHaveFocus()` (`:266-267`), `keyboard('{Enter}')` abre o formulário (`:268-270`), `campoLimiar` recebe e assere foco (`:271-272`), `botaoTestar` idem (`:274-276`) e `{Enter}` dispara o teste, com o painel de resultado e `testarRegra` chamado 1× (`:279-280`). Nomes acessíveis: `findByRole('button', {name:'Editar'})`, `findByLabelText('Limiar meteorológico')`. Foco visível: `App.css:17` `button:focus-visible`, `SuperficieRegras.css:52-56`. "Não só cor": ícone distinto asserido (`:96`). **Mutante M9 morto** — trocar o `<button>` por um `<span role="button" tabIndex>` (focável, mas ativável só por mouse) quebra o teste em `:270` | ✅ **PASS** (era ❌ GAP; nota F — ordem de tabulação não asserida) |
| **REGRA-15** — o MVP SHALL oferecer consulta das versões necessárias à explicação e à auditoria, sem duplicação de regras nem gestão avançada de histórico | Listagem + detalhe por versão; nenhuma rota de duplicação/reversão | `test_regras_api.py:88-94` — `200` + `len(regras) == 2` + `estados`/`versoes` asseridos (ativa **e** substituída visíveis); `:104-108` — detalhe com `id`, `limiar_meteorologico == 50.0`, `estado == "ativa"`; `:117-118` — `404` + `codigo == "regra_inexistente"`; `:128-129` — `422` + `codigo == "regra_id_invalido"`. Ausência de duplicação/reversão guardada por `test_saude.py:42-45` (conjunto **exato** de caminhos sob `/api/v1`) | ✅ PASS |

**Status**: ❌ **Um gap presente** — **14/15 ACs** casam com o resultado definido pela spec; **1 Partial** (REGRA-04, terceiro sinal sem evidência). **Zero spec-precision gaps**: a spec 2.4 define resultado preciso para as 15 ACs.

Contagem final: **14 PASS**, **1 Partial** (REGRA-04). Movimento em relação à Round 1: REGRA-02, REGRA-03, REGRA-10, REGRA-11 e REGRA-14 subiram para PASS; REGRA-04 subiu de GAP para Partial.

### Notas de julgamento

**A — REGRA-08 no backend (fechada).** `test_regras_api.py:143-151` agora assere `motivo`, `valor_observado == "72.5 mm"`, `atende` e o limiar dentro da justificativa, alcançando o padrão de 2.3 (`test_avaliacao_risco_api.py:75-78`).

**B — REGRA-09 "inalterada" (persiste, Minor).** `test_regras_api.py:220-221` continua asserindo só `estado == "substituida"` na versão anterior, não que `limiar_meteorologico` continua `50.0`. Estruturalmente seguro (o `UPDATE` toca só `estado`), e o novo teste de REGRA-10 (`test_repositorio_regras.py:197-202`) cobre a preservação da linha **relacionada**. Não bloqueia.

**C — REGRA-11 cenário literal (fechada).** `test_regras_api.py:239-269` porta a sonda P1 da Round 1 para a suíte.

**D — REGRA-01 documentação (persiste, Minor).** A justificativa das faixas (antecedência 1..168h, canais válidos, mapa AD-013) continua em docstrings de `dominio/validador_regra.py`, não no `adaptadores/persistencia/README.md` que a lição **L-022** indica. Não bloqueia: a AC pede "documentados", e docstrings são documentação legível e versionada.

**E — `antecedencia_horas` sem asserção de valor (persiste, Minor).** `grep -n antecedencia_horas testes/test_regras_api.py` → só a definição do payload (`:21`) e o `INSERT` da fixture (`:45`); nenhum teste backend lê o valor de volta. O frontend agora cobre a exibição (`24h`, `SuperficieRegras.test.tsx:127`). Uma troca de coluna no `INSERT`/desserialização seria detectada por tipo, não por valor.

**F — REGRA-14 ordem de tabulação.** O plano da Round 1 pedia também tabulação sequencial (`.tab()`) pelos campos. O teste entregue usa `focus()` + `{Enter}`, o padrão já vigente no projeto (`SuperficieFonteMeteorologica.test.tsx:160-173`). M9 prova que a asserção não é vazia — a operabilidade real por teclado está guardada. A **ordem** dos campos segue sem guarda.

**G — REGRA-02 fronteira do limiar.** A fronteira `limiar > 0` é de ponto flutuante: "imediatamente acima" não tem valor canônico. Os três lados estão cobertos (`-5.0`, `0.0`, `50.0+`) e a mutação natural (`<= 0` → `< 0`) morre em `test_validador_regra.py:87-95`. A fronteira **inteira** (`[1,168]`), onde o off-by-one é definível, está agora com os quatro valores.

**H — REGRA-03 células não asseridas.** `Severidade` e `Limiar` aparecem como cabeçalho asserido, mas seus **valores** de célula não são conferidos (a severidade é derivada em `SuperficieRegras.tsx:37-45`). Remover uma coluna morre (M8); trocar a fórmula de severidade sobreviveria. Minor, não bloqueia — a AC exige que a informação seja **exibida**, e a coluna está guardada.

---

## Discrimination Sensor

Duas worktrees isoladas e descartáveis (`git worktree add --detach <scratch> 6b33e16`), revertidas com `git checkout -- .` entre mutações e removidas com `git worktree remove --force`. O `node_modules` do frontend foi apenas **symlinkado** para dentro de cada worktree e o link removido antes da remoção — nada foi escrito na árvore real. Nenhum `git stash` usado.

### Mutantes reinjetados da Round 1

| # | Mutação | File:line | Descrição | Testes executados | Killed? |
| --- | --- | --- | --- | --- | --- |
| **M4** | Filtro de proveniência removido | `adaptadores/persistencia/repositorio_meteorologia.py:179` | `WHERE tipo = ? AND proveniencia = 'sintetico'` → `WHERE tipo = ?`: eventos reais entram no teste determinístico | Suíte backend completa | ✅ **Killed** — `test_listar_sinteticos_por_tipo_exclui_eventos_reais_do_mesmo_tipo` (`test_repositorio_meteorologia.py:123`): a lista volta com 2 ids em vez de 1 |
| **M5** | Off-by-one nas duas fronteiras de antecedência | `dominio/validador_regra.py:104-106` | `range(MIN, MAX + 1)` → `range(MIN - 1, MAX + 2)`: `0h` e `169h` passam a ser aceitos | Suíte backend completa | ✅ **Killed** — `test_antecedencia_horas_imediatamente_abaixo_e_acima_da_fronteira_produz_erro` (`test_validador_regra.py:117`): `assert True is False` |
| **M6** | Distinção de ícone colapsada | `funcionalidades/regras/SuperficieRegras.tsx:268-272` | `<ClockCounterClockwiseIcon data-icone-nome="clock-counter-clockwise">` → `<CheckCircleIcon data-icone-nome="check-circle">`: os dois estados mostram o mesmo ícone | `SuperficieRegras.test.tsx` (12 testes) | ✅ **Killed** — `usa um ícone diferente para a versão ativa e a substituída (REGRA-04)` (`:96`): `expected 'check-circle' not to be 'check-circle'` |

### Mutantes novos desta rodada

| # | Mutação | File:line | Descrição | Testes executados | Killed? |
| --- | --- | --- | --- | --- | --- |
| **M7** | Fix 6 desfeito — `ativar` deixa de avaliar | `aplicacao/gestao_regras.py:264-266` | `casos = self.testar(...)` → lógica antiga: `validar` + `listar_sinteticos_por_tipo` + `if not eventos: raise`, **sem nenhuma chamada a `avaliar`** | Suíte backend completa | ✅ **Killed** — `test_ativar_reexecuta_o_avaliador_para_cada_cenario_sintetico` (`test_gestao_regras.py:236`): `assert 0 == 1`. Nenhum outro teste falhou, confirmando que a mudança do Fix 6 é comportamentalmente neutra fora dessa promessa |
| **M8** | Coluna da tabela removida | `funcionalidades/regras/SuperficieRegras.tsx:234,250` | `<th scope="col">Severidade</th>` e `<td>{descreverSeveridade(regra)}</td>` apagados | `SuperficieRegras.test.tsx` | ✅ **Killed** — `exibe as onze colunas da tabela de regras…` (`:108`): a lista de cabeçalhos deixa de ser igual à esperada |
| **M9** | `Editar` deixa de ser operável por teclado | `funcionalidades/regras/SuperficieRegras.tsx:281-287` | `<button type="button" onClick>` → `<span role="button" tabIndex onClick>`: continua focável e visível como botão, mas `{Enter}` não ativa (só mouse) | `SuperficieRegras.test.tsx` | ✅ **Killed** — 2 falhas, entre elas `abre a edição e dispara o teste inteiramente por teclado…` (`:270`): o formulário nunca abre após `{Enter}`. **Prova que o teste de REGRA-14 não é superficial** |
| **M10** | **Indicador visual colapsado** | `funcionalidades/regras/SuperficieRegras.tsx:259-260` | A classe modificadora `regra-estado-badge--{estado}` e o atributo `data-indicador={estado}` removidos, deixando só `className="regra-estado-badge"`: ativa e substituída passam a ter **o mesmo indicador visual** | `SuperficieRegras.test.tsx` (12 testes) | ❌ **Survived** — 12/12 passed. Nenhum teste assere `toHaveClass`, `data-indicador` nem a classe modificadora → **Fix 9** |

**Sensor depth**: lightweight-plus (7 mutações nesta rodada — 3 reinjetadas + 4 novas; somadas às 6 da Round 1, 13 mutações no total sobre a história)

**Result**: **6/7 killed, 1 survived** — ❌ **FAIL** (o sobrevivente é o **terceiro sinal de REGRA-04**, severidade Minor)

**Verificação de isolamento**: `git status --porcelain` vazio **antes** (`BASELINE:[]`, `BASELINE2:[]`) e **depois** (`POST-SENSOR STATUS:[]`) de cada ciclo; `git worktree list` mostra apenas a árvore real em `6b33e16`; os diretórios de scratch não existem mais; `src/frontend/node_modules` da árvore real intacto.

---

## Payload / Conjunction Rule

Regra aplicada: a asserção precisa olhar **valor devolvido e/ou estado persistido**, não "a chamada aconteceu" nem um status isolado.

| Alvo | Asserção verifica valor real? | Evidência |
| --- | --- | --- |
| `GET /api/v1/regras` | ✅ Sim (**melhorado**) | `test_regras_api.py:88-94` — status **+** `len == 2` **+** `estados == {"ativa","substituida"}` **+** `versoes == {1,2}`. Ordenação (`ORDER BY evento_tipo, versao DESC`) continua não asserida (conjuntos, não listas) |
| `GET /api/v1/regras/{id}` 200 | ✅ Sim | `:104-108` — status **+** `id`, `limiar_meteorologico == 50.0`, `estado == "ativa"` |
| `GET /api/v1/regras/{id}` 404 / 422 | ✅ Sim | `:117-118` — status + `content-type: application/problem+json` + `codigo == "regra_inexistente"`; `:128-129` — `codigo == "regra_id_invalido"` |
| `POST .../testar` 200 | ✅ Sim (**melhorado**) | `:140-151` — status **+** `len(casos)==1`, `relevante is True`, `motivo == "relevante"`, `valor_observado == "72.5 mm"`, `atende is True`, `"60.0 mm" in justificativa` |
| `POST .../testar` 200 vazio | ✅ Sim | `:181-182` — status **+** `casos == []` (lista vazia explícita, não erro técnico) |
| `POST .../testar` 422 | ✅ Sim | `:165-169` — status + `codigo` + `erros[].campo == "limiar_meteorologico"` |
| `POST .../ativar` 200 | ✅ Sim | `:214-221` — status **+** `versao == 2`, `estado == "ativa"`, `limiar_meteorologico == 60.0` **+ estado persistido relido** (`estado == "substituida"`, nota B) |
| `POST .../ativar` concorrente | ✅ Sim (**novo**) | `:262-269` — `200`+`versao == 2`, `409`+`codigo`, **e** o estado final do banco relido (`len == 2`, `{versões} == {1,2}`) |
| `POST .../ativar` idempotente | ✅ Sim | `:290-297` — **`primeira.json() == segunda.json()`** (corpo inteiro) **e** `len(regras) == 2` |
| `POST .../ativar` 409 (versão / idempotência) | ✅ Sim | `:235-236` e `:318-319` — status **+** `codigo` discriminando as duas causas |
| `POST .../ativar` 404 / 422 | ✅ Sim | `:331-332`, `:198-199`, `:346-347` — status + `codigo` específico em cada caso |
| `ServicoGestaoRegras.ativar` — efeito de avaliação | ✅ Sim (**novo**) | `test_gestao_regras.py:236-237` — `len(chamadas) == 1` **e** `chamadas[0][0] is evento` (identidade do cenário avaliado, não só a contagem) |
| `ServicoGestaoRegras.ativar` — efeito de escrita | ✅ Sim | `test_gestao_regras.py:199` — `regras.chamadas[0] == (regra_anterior_id, 1, DADOS_CHUVA_VALIDOS)`; `:178,187,224` — `chamadas == []` / `len == 1` para provar **ausência** de escrita |
| `RepositorioRegras.criar_nova_versao` | ✅ Sim | `test_repositorio_regras.py:107-119` — objeto devolvido **e** três releituras do banco |
| `RepositorioAvaliacoesRisco` após nova versão | ✅ Sim (**novo**) | `test_repositorio_regras.py:197-202` — releitura real por `obter_por_execucao` com 4 asserções de valor, incluindo a tupla de critérios |
| `listar_sinteticos_por_tipo` | ✅ Sim (**novo**) | `test_repositorio_meteorologia.py:123,154` — `[evento.id …] == [sintetico.id]` / `== [granizo.id]` (identidade, não contagem) |
| Superfície — tabela | ✅ Sim (**novo**) | `SuperficieRegras.test.tsx:108-129` — lista exata de cabeçalhos **e** 7 valores de célula |
| Superfície — teclado | ✅ Sim (**novo**) | `:266-280` — foco asserido em 3 elementos **e** o efeito observável do `{Enter}` (formulário aberto, painel de resultado, `testarRegra` 1×) |
| Superfície — ativação | ✅ Sim | `:246-250` — mensagem de sucesso **e** `ativarRegra` chamado com `(id, versao, objectContaining({limiarMeteorologico: 50}))` |
| Superfície — indicador visual | ❌ **Não** | Nenhuma asserção de classe/atributo em nenhum teste (M10 sobreviveu) |

Nenhuma asserção do tipo "só contagem" ou "status isolado" permanece no contrato HTTP.

---

## Code Quality

| Princípio | Status |
| --- | --- |
| Minimum code | ✅ — o Fix 6 **removeu** 6 linhas duplicadas em vez de acrescentar código: `ativar` passou a reusar `testar` (`gestao_regras.py:264`), eliminando a segunda cópia da validação e da listagem de cenários |
| Surgical changes | ✅ — a correção tocou 1 arquivo de produção backend (`gestao_regras.py`, −11/+6 linhas), 1 de produção frontend (`SuperficieRegras.tsx`, só atributos `data-icone-nome`) e 6 de teste; nenhuma migração, nenhuma rota nova, `openapi.json` inalterado |
| No scope creep | ✅ — nenhuma funcionalidade nova; todos os itens do diff mapeiam para um Fix nomeado da Round 1 |
| Matches patterns | ✅ — `data-icone-nome` replica literalmente o padrão validado em 2.3 (`SuperficieEventoDecisao.tsx:41,46,50`); o teste de teclado replica `SuperficieFonteMeteorologica.test.tsx:160-173`; o espião via porta injetável segue `PortasGestaoRegras` |
| Spec-anchored outcome check | ⚠️ — 14/15 ACs com asserção casando o resultado da spec; 1 Partial (REGRA-04) |
| Per-layer Coverage Expectation | ✅ — domínio 1:1 com as classes de invalidez **e** as fronteiras; rota cobre feliz + vazio + concorrente + 404 + 422 (×4 causas) + 409 (×2 causas); componente agora cobre teclado, colunas e distinção de ícone |
| Every test maps to a spec requirement | ✅ — os 6 testes backend e 3 frontend novos citam `REGRA-NN` ou o achado da Round 1 no docstring/nome; nenhum teste órfão |
| Documented guidelines followed | ⚠️ — `AGENTS.md` e o padrão de 2.2/2.3 seguidos; a justificativa das faixas continua fora do README versionado do schema (nota D, lição **L-022**) |
| Docstring/contrato correspondem ao comportamento | ✅ — **corrigido**: `gestao_regras.py:246` e `http/regras.py:372` afirmam reexecução do teste determinístico, e agora `ativar` de fato chama `avaliar` por cenário (M7 morto prova a guarda) |

---

## Edge Cases

- [x] **Ativar combinação evento↔produto inconsistente → bloqueio com motivo específico antes do teste** — `test_validador_regra.py:166-190` (granizo + residencial; motivo cita ambos os produtos), `test_regras_api.py:165-169`. Mutante M2 morto (Round 1)
- [x] **Teste sem nenhum cenário sintético aplicável → resultado vazio válido, não erro técnico, e ativação segue bloqueada** — `test_gestao_regras.py:148-154` (`resultados == ()`), `:156-171` (filtragem por tipo), `test_regras_api.py:181-182` (`200` + `casos == []`), bloqueio da ativação em `:346-347` (`422 nenhum_cenario_aplicavel`) + `test_gestao_regras.py:184-191` (`regras.chamadas == []`). Frontend: `SuperficieRegras.tsx:443-444` — **continua sem teste de frontend** (Minor, inalterado)
- [x] **Ativação idêntica reenviada depois de a resposta ter sumido da UI (chave ainda válida) → resposta originalmente registrada** — `test_regras_api.py:290-297` (`primeira.json() == segunda.json()` + `len(regras) == 2`); serviço em `test_gestao_regras.py:211-216`
- [x] **Cenário sintético vs. evento real** — **fechado nesta rodada**: `test_repositorio_meteorologia.py:92-123` insere um `REAL_INMET` e um `SINTETICO` do mesmo tipo e assere que só o sintético volta. Mutante M4 morto

---

## Gate Check

- **Gate command (Build)**: `uv run pytest -q && uv run ruff check . && uv run pyright` (em `src/backend`) + `npx vitest run && npm run lint && npm run build` (em `src/frontend`)
- **Executado nesta rodada pelo próprio Verificador** (não herdado do orquestrador):
  - `pytest`: **340 passed**, 0 failed, 0 skipped (exit 0, 18.91s)
  - `ruff check .`: **All checks passed!**
  - `pyright`: **0 errors, 0 warnings, 0 informations**
  - `vitest run`: **189 passed** em 22 arquivos, 0 failed (exit 0)
  - `npm run lint` (`oxlint`): exit 0 — **10 warnings**, todas pré-existentes de `react(set-state-in-effect)` / `react(only-export-components)`; a única em arquivo desta história é `SuperficieRegras.tsx:89`, mesmo padrão já aceito em `SuperficieEventoDecisao.tsx:79`, `SuperficieProntidao.tsx:84` e `SuperficieFonteMeteorologica.tsx:149`
  - `npm run build`: **✓ built in 223ms** (exit 0)
- **Test count antes da feature** (fim de 2.3, `7121003`): 292 backend / 164 frontend
- **Test count na Round 1** (`e0876e2`): 334 backend / 186 frontend
- **Test count na Round 2** (`6b33e16`): **340 backend / 189 frontend**
- **Delta da rodada de correção**: **+6 backend** (`test_repositorio_meteorologia` +2, `test_validador_regra` +1, `test_gestao_regras` +1, `test_regras_api` +1, `test_repositorio_regras` +1) / **+3 frontend** (`SuperficieRegras.test.tsx`: ícone, colunas, teclado)
- **Delta total da história**: **+48 backend / +25 frontend**
- **Test Integrity**: ✅ a contagem **só cresceu**; nenhum teste removido no diff `e0876e2..6b33e16`; **nenhuma asserção enfraquecida** — as duas asserções alteradas (`test_regras_api.py:142-151` e `:88-94`) foram **fortalecidas**, trocando contagens por valores
- **Skipped**: nenhum
- **Failures**: nenhuma

---

## Fix Plans

Um único item aberto. Os Fix 1–8 da Round 1 estão fechados, exceto o resto do Fix 2, renumerado abaixo.

### Fix 9: Asserir o **indicador visual** que distingue ativa de substituída (REGRA-04) — **Minor**

- **Root cause**: o Fix 2 da Round 1 pedia três asserções — `data-icone-nome`, `data-indicador` e a classe `regra-estado-badge--{estado}`. Só a primeira foi implementada. `SuperficieRegras.tsx:259-260` renderiza a classe modificadora `regra-estado-badge--{estado}` e o atributo `data-indicador={estado}`, com cores distintas em `SuperficieRegras.css:24-30`, mas `grep -n "data-indicador\|regra-estado-badge\|toHaveClass" SuperficieRegras.test.tsx` devolve **zero ocorrências**. O `data-indicador` é hoje um gancho de teste morto. Mutante **M10** — colapsar o indicador ao mesmo `className="regra-estado-badge"` sem modificador — deixa **12/12 testes verdes**, e a superfície passa a identificar a regra ativa por apenas 2 dos 3 sinais que a AC exige.
- **Fix task**: no teste já existente `usa um ícone diferente para a versão ativa e a substituída (REGRA-04)` (`SuperficieRegras.test.tsx:79-97`), estender para o terceiro sinal: localizar o `span` da badge em cada linha e asserir `toHaveClass('regra-estado-badge--ativa')` / `toHaveClass('regra-estado-badge--substituida')` — ou, equivalente, coletar os `data-indicador` das duas linhas e asserir que são distintos (`new Set(indicadores).size === 2`), no mesmo formato de `SuperficieEventoDecisao.test.tsx:153`. **Verificar**: reaplicar M10 (remover o modificador de classe e o `data-indicador`) e confirmar que agora morre.
- **Priority**: Minor (uma asserção; nenhuma mudança de produção)

### Itens Minor registrados, não bloqueantes (opcionais na mesma rodada)

- **Nota E** — asserir `antecedencia_horas == 48` na resposta de `POST .../ativar`, fechando o round-trip escrita→leitura desse campo no backend (`test_regras_api.py:214-221`).
- **Nota B** — no mesmo teste, asserir que `limiar_meteorologico` da versão anterior continua `50.0` após a substituição, não só o `estado`.
- **Nota H** — asserir os valores de célula de `Severidade` e `Limiar` na linha da regra ativa (`SuperficieRegras.test.tsx:123-129`).
- **Nota D** — migrar a justificativa das faixas de `dominio/validador_regra.py:7,10,16` para `adaptadores/persistencia/README.md`, como a lição **L-022** e o precedente de 2.3 (`README.md:104-122`) indicam.
- **Nota F** — acrescentar a asserção de **ordem** de tabulação (`userEvent.tab()` encadeado) ao teste de REGRA-14.

---

## Lições candidatas (grounding para `.specs/lessons.json`)

| Origem fundamentada | Lição proposta |
| --- | --- |
| M10 sobreviveu (REGRA-04, 3ª superfície consecutiva) | **L-024 deve ser promovida de `candidate` a estabelecida e ampliada**: quando um requisito enumera N sinais de distinção (texto, ícone, cor/indicador), a rodada de correção precisa asserir **todos os N**, não o subconjunto que o mutante da rodada anterior expôs — fechar um sinal deixa os outros com a mesma fragilidade |
| Fix 2 fechado só pela metade | Uma fix task que enumera várias asserções deve ser reverificada **item a item** contra o texto da própria task; "o mutante da rodada anterior morreu" não é evidência de que a task inteira foi executada |
| M7 morto (Fix 6) | Quando uma docstring ou `description` de OpenAPI promete um efeito, a correção mais barata costuma ser **fazer o código cumprir a promessa por reuso** (aqui, `ativar` delegando a `testar`) — fecha a divergência, remove duplicação e vira testável por espião numa porta já injetável |
| M9 morto (REGRA-14) | Um teste de acessibilidade por teclado é discriminante quando o mutante natural é "trocar o elemento nativo por um `role=` focável": se o teste continua verde com um `<span role="button">`, ele mede foco, não operabilidade |
| M4/M5/M8 mortos | As três lições candidatas da Round 1 (filtro `WHERE` precisa de uma linha excluída; faixa fechada precisa de `min-1`/`min`/`max`/`max+1`; conjunto de colunas precisa de igualdade exata) foram **confirmadas empiricamente** — os mutantes correspondentes morrem depois de aplicadas |

---

## Requirement Traceability Update

| Requirement | Previous Status (Round 1) | New Status (Round 2) |
| --- | --- | --- |
| REGRA-01 | ✅ Verified | ✅ Verified |
| REGRA-02 | ❌ Needs Fix (Fix 3) | ✅ **Verified** |
| REGRA-03 | ❌ Needs Fix (Fix 5) | ✅ **Verified** |
| REGRA-04 | ❌ Needs Fix (Fix 2) | ⚠️ **Parcial — Needs Fix (Fix 9)**: texto e ícone verificados; indicador visual sem evidência |
| REGRA-05 | ✅ Verified | ✅ Verified |
| REGRA-06 | ✅ Verified | ✅ Verified |
| REGRA-07 | ✅ Verified | ✅ Verified |
| REGRA-08 | ✅ Verified | ✅ Verified (reforçado no backend) |
| REGRA-09 | ✅ Verified | ✅ Verified |
| REGRA-10 | ⚠️ Verified por construção/herança | ✅ **Verified** (teste próprio desta história) |
| REGRA-11 | ✅ Verified (caminho equivalente) | ✅ **Verified** (cenário literal) |
| REGRA-12 | ✅ Verified | ✅ Verified |
| REGRA-13 | ✅ Verified | ✅ Verified |
| REGRA-14 | ❌ Needs Fix (Fix 1) | ✅ **Verified** |
| REGRA-15 | ✅ Verified | ✅ Verified |

---

## Summary

**Overall**: ⚠️ **Issues** — um único item aberto, de severidade Minor, resolvível com uma asserção

**Spec-anchored check**: **14/15 ACs** com asserção casando exatamente o resultado definido pela spec; **1 Partial** (REGRA-04, terceiro sinal). **Zero spec-precision gaps**
**Sensor**: **6/7 mutantes mortos** nesta rodada (3 reinjetados da Round 1 + 4 novos); **1 sobrevivente** (M10, indicador visual de REGRA-04)
**Gate**: 340 backend + 189 frontend passed, 0 failed, 0 skipped; `ruff`/`pyright`/`lint`/`build` verdes — todos re-executados pelo Verificador

**O que funciona**: as correções são reais, não cosméticas — e isso foi medido, não aceito. Os três mutantes que sobreviveram na Round 1 morreram: o filtro `proveniencia = 'sintetico'` agora tem uma linha que ele exclui (`test_repositorio_meteorologia.py:123`), a faixa `[1,168]` tem os quatro valores de fronteira (`test_validador_regra.py:117`), e os dois ícones da tabela têm identidades distintas asseridas (`SuperficieRegras.test.tsx:96`). Três mutações **novas** confirmaram que as correções não são superficiais: desfazer o Fix 6 (`ativar` volta a não avaliar) morre no teste de espião; remover uma coluna da tabela morre na igualdade exata de cabeçalhos; e trocar o `<button>` `Editar` por um `<span role="button">` — focável, mas ativável só por mouse — **quebra o teste de teclado**, provando que REGRA-14 mede operabilidade e não apenas foco. O Fix 6 é a única mudança de produção da rodada e é uma melhoria dupla: `ativar` passou a **reusar** `testar` em vez de duplicar validação e listagem de cenários, o que ao mesmo tempo remove código e torna verdadeira a `description` publicada no OpenAPI. Nenhum teste foi removido, e as duas asserções alteradas foram fortalecidas (contagens → valores). REGRA-10 e REGRA-11 deixaram de depender de evidência estrutural/equivalente e ganharam testes literais.

**Problemas encontrados**: exatamente um. O Fix 2 da Round 1 enumerava três asserções para REGRA-04 (`data-icone-nome`, `data-indicador`, classe `regra-estado-badge--{estado}`) e apenas a primeira foi implementada. Como a AC exige que a regra ativa seja identificada por **texto, ícone e indicador visual**, o terceiro sinal segue sem nenhuma citação `file:line` — e o mutante M10, que colapsa o indicador visual dos dois estados no mesmo `className`, deixa os 12 testes da superfície verdes. É a mesma família da lição **L-024**, agora reincidindo pela terceira superfície consecutiva, o que sugere promovê-la de `candidate` a estabelecida e ampliá-la para "asserir todos os N sinais, não só o que o mutante anterior expôs". Nenhum defeito de comportamento em produção foi encontrado nesta rodada.

**Next steps**: aplicar o **Fix 9** (uma asserção de classe ou de `data-indicador` no teste `SuperficieRegras.test.tsx:79-97` já existente), reinjetar M10 e confirmar que morre. Os itens das notas B, D, E, F e H são Minor e podem acompanhar a mesma rodada, já que tocam os mesmos arquivos. Esta é a **iteração 2 de no máximo 3** — a próxima rodada deve fechar a história.
