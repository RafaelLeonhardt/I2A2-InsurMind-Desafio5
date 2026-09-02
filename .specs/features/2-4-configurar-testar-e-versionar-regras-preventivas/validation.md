# História 2.4: Configurar, testar e versionar regras preventivas — Validation

**Date**: 2026-09-02
**Rodada**: **ROUND 3 (final)** — rodada de confirmação da correção da Round 2
**Spec**: `.specs/features/2-4-configurar-testar-e-versionar-regras-preventivas/spec.md`
**Diff range**: `7121003..c0d50d1` (7 commits — T1 `73d2409`, T2 `d11ddab`, T3 `8f13e99`, T4 `ea3efa0`, T5 `e0876e2` + correções `6b33e16` e `c0d50d1`)
**Diff da correção desta rodada em isolado**: `6b33e16..c0d50d1`
**Verifier**: sub-agente independente (author ≠ verifier), **distinto dos verificadores da Round 1 e da Round 2** — read-only sobre a árvore real; mutações apenas em worktree descartável

**Verdict**: ✅ **PASS**

**Histórico**: Round 1 (`7121003..e0876e2`) → ❌ FAIL (4 GAPs + 1 Partial; 3/6 mutantes sobreviveram) → Fix 1–8 em `6b33e16` → Round 2 → ❌ FAIL por **um** item Minor (mutante M10 sobrevivente: o terceiro sinal de REGRA-04) → Fix 9 em `c0d50d1` → Round 3 (este relatório) → ✅ **PASS**.

O único item aberto da Round 2 está **fechado e comprovado por mutação**. O Fix 9 não é cosmético: o mutante **M10 foi reinjetado literalmente** (colapsar as duas badges no mesmo `className="regra-estado-badge"`, sem `data-indicador` e sem sufixo por estado) e **morreu**. Duas mutações **novas e mais sutis** — remover só a classe modificadora mantendo o `data-indicador`, e fixar o `data-indicador` numa constante mantendo a classe — **também morreram**, provando que as duas metades da asserção são independentemente vivas (o teste não passa "por acidente" com uma delas). Nenhuma mudança de produção foi feita nesta rodada de correção: só uma asserção de teste. As 15 ACs da spec agora têm asserção que casa com o resultado definido.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 — `ValidadorRegra` | ✅ Done | Faixa `[1, 168]` com os quatro valores de fronteira (`testes/test_validador_regra.py:109-131`); mutante M5 morto (R2) |
| T2 — `RepositorioRegras` escrita versionada | ✅ Done | `criar_nova_versao` inalterado desde a Round 1; guarda de REGRA-10 em `test_repositorio_regras.py:168-202` |
| T3 — `ServicoGestaoRegras` | ✅ Done | `ativar` delega a `self.testar(...)` (`central_preventiva/aplicacao/gestao_regras.py:261`) — a promessa "reexecuta o teste determinístico" da docstring e do OpenAPI é verdadeira; guardada pelo espião em `test_gestao_regras.py:218-238` (mutante M7 morto na R2) |
| T4 — Roteador HTTP `regras` | ✅ Done | Inalterado; `openapi.json` sincronizado (`test_openapi_sincronizado.py`), conjunto exato de caminhos guardado (`test_saude.py:42-45`) |
| T5 — Superfície "Regras" | ✅ **Done** (era ⚠️ Partial na R2) | Teclado (REGRA-14), conjunto de colunas (REGRA-03), ícone distinto **e agora o indicador visual** (REGRA-04) asseridos e comprovadamente discriminantes (M6, M8, M9, M10, M11, M12 mortos) |
| Fix 1–9 (Verifier R1 + R2) | ✅ **9 fechados** | Fix 1–8 confirmados na Round 2; Fix 9 confirmado nesta rodada |

**Lacuna de integração declarada (não é defeito, inalterada)**: `SuperficieRegras` continua não montada em rota no `App.tsx` — `grep -rn "SuperficieRegras" src/frontend/src/App.tsx` → **zero ocorrências** (reconfirmado nesta rodada). Mesmo padrão já aceito para `SuperficieFonteMeteorologica` (2.1/2.2) e `SuperficieEventoDecisao` (2.3), declarado pelo autor em `tasks.md`. Registrado, não contado como lacuna.

---

## Verificação da correção da Round 2

| Fix | O que a Round 2 pediu | Verificação independente (Round 3) | Resultado |
| --- | --- | --- | --- |
| **Fix 9 (Minor)** — REGRA-04, terceiro sinal (indicador visual) | Localizar a badge de cada linha e asserir `toHaveClass('regra-estado-badge--ativa'/'--substituida')` **ou** o `data-indicador` distinto entre os dois estados; **verificar reaplicando M10** | Feito, e **acima** do pedido — as duas formas foram implementadas. `src/frontend/src/funcionalidades/regras/SuperficieRegras.test.tsx:98-106`, dentro do teste já existente `usa um ícone diferente para a versão ativa e a substituída (REGRA-04)`: `linhaAtiva.querySelector('[data-indicador]')` / `linhaSubstituida.querySelector('[data-indicador]')` (`:98-99`), `toHaveAttribute('data-indicador','ativa')` (`:100`), `toHaveAttribute('data-indicador','substituida')` (`:101`), `toHaveClass('regra-estado-badge--ativa')` (`:102`), `toHaveClass('regra-estado-badge--substituida')` (`:103`) e a distinção explícita entre os dois indicadores (`:104-106`). Os elementos alvo são exatamente os `span` de estado renderizados em `SuperficieRegras.tsx:259-262`, com cores distintas em `SuperficieRegras.css:23-29`. **Mutante M10 reinjetado e morto**; mutantes novos **M11** e **M12** (que atacam cada metade da asserção separadamente) **também mortos** | ✅ **Fechado** |

**Diff da correção**: `6b33e16..c0d50d1` toca 3 arquivos — `SuperficieRegras.test.tsx` (+10 linhas, só asserções), `tasks.md` (+8, registro do Fix 9) e `validation.md` (relatório da R2). **Zero linhas de produção alteradas** — coerente com o diagnóstico da Round 2 (o componente já renderizava os três sinais desde a Round 1; faltava a evidência de teste).

---

## Spec-Anchored Acceptance Criteria

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + asserção | Result |
| --- | --- | --- | --- |
| **REGRA-01** — limiares e janelas SHALL originar de configuração versionada e legível, com padrões e justificativa documentados | Limiar e janela lidos de linha versionada de `regras`, com justificativa escrita | Config versionada: `repositorio_regras.py:93-115` (`listar`/`obter_por_id` com `versao`/`estado`); justificativa das faixas em `dominio/validador_regra.py:7,10,16`. Teste: `test_repositorio_regras.py:107-119` — `nova.versao == 2`, `nova.estado == "ativa"`, `nova.limiar_meteorologico == 60.0`, `nova.canal == "email"`; `:152-155` — versão substituída conserva `limiar_meteorologico == 10.0`. HTTP: `test_regras_api.py:91-94` — `estados == {"ativa","substituida"}`, `versoes == {1,2}` | ✅ PASS (nota D — justificativa em docstring de código, não no README versionado do schema) |
| **REGRA-02** — os testes da regra SHALL incluir exemplos imediatamente **abaixo**, **sobre** e **acima** de cada fronteira relevante | Para cada fronteira: um exemplo de cada lado imediato | Antecedência `[1,168]`: `test_validador_regra.py:114-120` — `0` → `valida is False` + `campo == "antecedencia_horas"`; `169` → idem; `:126-131` — `1` e `168` → `valida is True`; `:98-106` — `200` (bem acima). Limiar `> 0`: `:195` (`-5.0`, abaixo), `:87-95` (`0.0`, sobre, "maior que zero"), `DADOS_CHUVA_VALIDOS` (`50.0`, acima). Mutante **M5 morto** (R2) | ✅ PASS |
| **REGRA-03** — a superfície SHALL exibir tipo de evento, severidade, limiar, área, tipo e situação da apólice, coberturas, antecedência, canal, versão e estado | As informações visíveis por regra | `SuperficieRegras.test.tsx:118-130` — `expect(cabecalhos).toEqual(['Tipo de evento','Severidade','Limiar','Área','Apólice','Cobertura','Antecedência','Canal','Versão','Estado','Ação'])` (igualdade **exata** e ordenada); `:133-139` — na linha da ativa, `Chuva intensa`, `9990001`, `Residencial`, `alagamento`, `24h`, `WhatsApp`, `1`. Código: `SuperficieRegras.tsx:233-243,249-278`. Mutante **M8 morto** (R2) | ✅ PASS (nota H — valores de `Severidade` e `Limiar` não asseridos na célula, só como coluna) |
| **REGRA-04** — a interface SHALL identificar a regra ativa por **texto, ícone e indicador visual** | Os três sinais presentes **e distintos** entre ativa e substituída | **Texto** ✅: `SuperficieRegras.test.tsx:71-72,86-87` — `queryByText('Ativa')` / `queryByText('Substituída')` isolam linhas distintas. **Ícone** ✅: `SuperficieRegras.tsx:264-275` (`data-icone-nome="check-circle"` / `"clock-counter-clockwise"`), `test.tsx:94-96` — `expect(iconeAtiva).not.toBe(iconeSubstituida)`; mutante **M6 morto** (R2). **Indicador visual** ✅ **(novo)**: `SuperficieRegras.tsx:259-262` (`regra-estado-badge--${regra.estado}` + `data-indicador={regra.estado}`, CSS distinto em `SuperficieRegras.css:23-29`), asserido em `test.tsx:100-106` — `toHaveAttribute('data-indicador','ativa'/'substituida')` **e** `toHaveClass('regra-estado-badge--ativa'/'--substituida')` **e** os dois indicadores distintos. Mutantes **M10, M11 e M12 mortos** | ✅ **PASS** (era ⚠️ Partial; **os três sinais agora com evidência e discriminação provada**) |
| **REGRA-05** — o formulário SHALL validar tipos, faixas, combinações obrigatórias e coerência evento↔produto | As 4 classes de invalidez, cada uma com campo identificado | `test_validador_regra.py:40-59` (tipo do domínio), `:62-81` (tipo Python), `:84-131` (faixa, com as 4 fronteiras), `:133-164` (combinação obrigatória), `:166-190` (coerência: motivo cita `"residencial"` **e** `"automovel"`), `:192-215` — `campos_com_erro == {7 campos}` (agregação sem parar na primeira falha). Mutante **M2 morto** (R1) | ✅ PASS |
| **REGRA-06** — erro de validação SHALL aparecer junto ao campo **sem descartar os valores já informados** | Mensagem junto ao campo + demais valores preservados | `SuperficieRegras.test.tsx:199-233` — `findByText('Limiar meteorológico deve ser maior que zero.')` (`:228`), `toHaveAttribute('aria-invalid','true')` (`:230`), **`getByLabelText('Cobertura exigida')` com `'cobertura-customizada'`** (`:231`, valor digitado em outro campo sobrevive), `Ativar` volta a `toBeDisabled()`. Backend: `test_regras_api.py:154-169` — `codigo == "configuracao_invalida"` + `erros[].campo == "limiar_meteorologico"` | ✅ PASS |
| **REGRA-07** — testar/ativar configuração inválida SHALL ser bloqueado com motivos específicos em PT-BR, **sem criar nenhuma nova versão ativa** | Bloqueio + motivo PT-BR + zero escrita | `test_gestao_regras.py:129-137` — `raises(ConfiguracaoInvalida)` com `erro.campo == "limiar_meteorologico"`; `:174-182` — `raises(...)` **e `regras.chamadas == []`**; `:184-191` — idem para `NenhumCenarioAplicavel`. HTTP: `test_regras_api.py:154-169`, `:334-347` (`codigo == "nenhum_cenario_aplicavel"`). Motivos PT-BR: `validador_regra.py:59,66,74,81,97,111,123,125,129,145`. A validação de `ativar` passa por `testar` (`gestao_regras.py:261`), então o bloqueio é o mesmo caminho de código nas duas operações | ✅ PASS |
| **REGRA-08** — teste de configuração válida SHALL aplicar a regra deterministicamente aos cenários sintéticos, e a interface SHALL apresentar **operando, valor observado, resultado e justificativa** por caso | 4 colunas por critério, por cenário | Frontend: `SuperficieRegras.test.tsx:166-198` — `getByText('área aplicável')` (`:190`), `getByText('9990001')` (`:191`), `getByText('Atende')` (`:192`) e a justificativa completa (`:194`), dentro de `findByRole('region', {name:/Resultado do teste/})`. Backend: `test_regras_api.py:143-151` — `motivo == "relevante"`, `valor_observado == "72.5 mm"`, `atende is True`, `"60.0 mm" in justificativa`. Cenários **só sintéticos**: `repositorio_meteorologia.py:179` (`WHERE tipo = ? AND proveniencia = 'sintetico'`), guardado por `test_repositorio_meteorologia.py:123` (M4 morto). Determinismo herdado de `AvaliadorRisco` (2.3, função pura) | ✅ PASS |
| **REGRA-09** — ativar uma alteração testada SHALL criar nova versão imutável e torná-la ativa, **mantendo a anterior consultável e inalterada** | Nova linha `ativa` com `versao+1`; anterior `substituida`, consultável, com campos preservados | `test_repositorio_regras.py:107-119` — `nova.versao == 2`, `nova.estado == "ativa"`, `anterior.estado == "substituida"`, `ativa.id == nova.id`; `:144-160` — `listar` devolve as duas versões e a substituída conserva `limiar_meteorologico == 10.0`; `:197-202` — os campos de uma avaliação ligada à versão anterior seguem intactos após a substituição. HTTP: `test_regras_api.py:214-221`. Imutabilidade: `repositorio_regras.py:132-156` — o único `UPDATE` toca exclusivamente `estado` | ✅ PASS (nota B) |
| **REGRA-10** — execução iniciada antes da alteração SHALL conservar o snapshot da versão originalmente aplicada, sem recálculo silencioso | Avaliação anterior segue reportando `regra_id`/`regra_versao` antigos | `test_repositorio_regras.py:168-202` — salva `ResultadoAvaliacaoRisco` com `regra_versao=1`, executa `criar_nova_versao(..., versao_esperada=1)`, relê por `obter_por_execucao` e assere `regra_id == UUID(id_regra)`, `regra_versao == 1`, `relevante is True`, `criterios == resultado.criterios`. Estrutural: `repositorio_avaliacoes_risco.py` só `INSERT`/`SELECT`; `criar_nova_versao` insere linha nova (`repositorio_regras.py:127,141-156`) | ✅ PASS |
| **REGRA-11** — duas tentativas concorrentes com a mesma `versao_esperada` → só a primeira confirma, a segunda recebe `409` sem sobrescrever nem aplicar parcialmente | 1ª `200`, 2ª `409`, exatamente 2 linhas ao final | **Cenário literal**: `test_regras_api.py:239-269` — mesmo corpo com `versao_esperada: 1`, chaves de idempotência distintas (`chave-concorrente-1/2`); `primeira.status_code == 200` **e** `primeira.json()["versao"] == 2`, `segunda.status_code == 409` **e** `codigo == "conflito_versao"`, `len(regras) == 2`, `{versões} == {1,2}`. Caminho equivalente: `:235-236`; repositório: `test_repositorio_regras.py:126-141` (`raises(ConflitoVersao)` + `anterior.estado == "ativa"` + `len(listar()) == 1`). Mutante **M1 morto** (R1) | ✅ PASS |
| **REGRA-12** — ativação repetida com a mesma `Idempotency-Key` e conteúdo idêntico SHALL devolver a resposta registrada, sem criar outra versão | Corpo idêntico ao da 1ª resposta + zero versão extra | `test_regras_api.py:272-298` — `primeira.status_code == 200`, `segunda.status_code == 200`, **`primeira.json() == segunda.json()`** e `len(regras) == 2`. Serviço: `test_gestao_regras.py:205-216` — `segunda == primeira` e `len(regras.chamadas) == 1` | ✅ PASS |
| **REGRA-13** — mesma `Idempotency-Key` reusada com conteúdo diferente SHALL retornar `409` | `409` + nenhuma mutação | `test_regras_api.py:300-319` — `status_code == 409`, `codigo == "conflito_idempotencia"`; `test_gestao_regras.py:240-250` — `raises(ConflitoIdempotencia)` **e `len(regras.chamadas) == 1`**. Hash = SHA-256 do corpo bruto (`http/regras.py:429`). Mutante **M3 morto** (R1) | ✅ PASS |
| **REGRA-14** — navegar, editar e confirmar **só pelo teclado**: nomes acessíveis, foco visível, ordem lógica, sem depender de hover ou cor isolada | Interação por teclado exercitada; foco visível; distinção não dependente de cor | `SuperficieRegras.test.tsx:262-291` — `botaoEditar.focus()` + `toHaveFocus()` (`:276-277`), `keyboard('{Enter}')` abre o formulário (`:278-280`), `campoLimiar` recebe e assere foco (`:281-282`), `botaoTestar` idem (`:284-286`) e `{Enter}` (`:287`) dispara o teste, com o painel de resultado e `testarRegra` chamado 1× (`:289-290`). Nomes acessíveis: `findByRole('button', {name:'Editar'})`, `findByLabelText('Limiar meteorológico')`. Foco visível: `App.css:17` `button:focus-visible`, `SuperficieRegras.css:51-55`. "Não só cor": ícone distinto (`:96`) **e** indicador com `data-indicador` semântico (`:100-101`) asseridos. Mutante **M9 morto** (R2) | ✅ PASS (nota F — ordem de tabulação não asserida) |
| **REGRA-15** — o MVP SHALL oferecer consulta das versões necessárias à explicação e à auditoria, sem duplicação de regras nem gestão avançada de histórico | Listagem + detalhe por versão; nenhuma rota de duplicação/reversão | `test_regras_api.py:88-94` — `200` + `len(regras) == 2` + `estados`/`versoes` asseridos (ativa **e** substituída visíveis); `:104-108` — detalhe com `id`, `limiar_meteorologico == 50.0`, `estado == "ativa"`; `:117-118` — `404` + `codigo == "regra_inexistente"`; `:128-129` — `422` + `codigo == "regra_id_invalido"`. Ausência de duplicação/reversão guardada por `test_saude.py:42-45` (conjunto **exato** de caminhos sob `/api/v1`) | ✅ PASS |

**Status**: ✅ **Sem gaps** — **15/15 ACs** casam com o resultado definido pela spec. **Zero spec-precision gaps**: a spec 2.4 define resultado preciso para as 15 ACs.

Contagem final: **15 PASS**, 0 Partial, 0 GAP. Movimento em relação à Round 2: REGRA-04 subiu de Partial para PASS; nenhuma AC regrediu (verificado por spot-check dos `file:line` citados — ver abaixo).

### Spot-check de não regressão (Round 3)

Os `file:line` da Round 2 foram reconferidos por amostragem na árvore real, escolhendo os quatro itens mais sensíveis a regressão silenciosa:

| AC amostrada | O que foi reconferido | Resultado |
| --- | --- | --- |
| REGRA-02 | `test_validador_regra.py:109-131` — `test_antecedencia_horas_imediatamente_abaixo_e_acima_da_fronteira_produz_erro` (0 e 169 inválidos, campo identificado) e `..._no_limite_inferior_e_superior_e_valida` (1 e 168 válidos) | ✅ Presente e íntegro |
| REGRA-11 | `test_regras_api.py:239-269` — cenário literal de concorrência, com as 6 asserções (`200`+`versao==2`, `409`+`codigo`, `len==2`, `{1,2}`) | ✅ Presente e íntegro |
| REGRA-14 | `SuperficieRegras.test.tsx:262-291` — foco asserido em 3 elementos + `{Enter}` com efeito observável | ✅ Presente e íntegro (deslocado +10 linhas pelo Fix 9) |
| T3 / REGRA-07-08 | `gestao_regras.py:261` (`casos = self.testar(regra_anterior_id, dados)`) e o espião em `test_gestao_regras.py:218-238` (`len(chamadas) == 1`, `chamadas[0][0] is evento`) | ✅ Presente e íntegro |
| REGRA-08 (filtro) | `repositorio_meteorologia.py:179` — `WHERE tipo = ? AND proveniencia = 'sintetico'` | ✅ Presente |

> Nota de renumeração: o Fix 9 inseriu 10 linhas em `SuperficieRegras.test.tsx` logo após a linha 97. Todas as citações de linha desse arquivo neste relatório estão **atualizadas** para a árvore em `c0d50d1`; as citações da Round 2 acima de `:97` seguem válidas, e as abaixo estão deslocadas em +10.

### Notas de julgamento (todas Minor, nenhuma bloqueante)

**B — REGRA-09 "inalterada".** `test_regras_api.py:220-221` assere só `estado == "substituida"` na versão anterior, não que `limiar_meteorologico` continua `50.0`. Estruturalmente seguro (o `UPDATE` toca só `estado`), e o teste de REGRA-10 (`test_repositorio_regras.py:197-202`) cobre a preservação da linha relacionada.

**D — REGRA-01 documentação.** A justificativa das faixas (antecedência 1..168h, canais válidos, mapa AD-013) segue em docstrings de `dominio/validador_regra.py`, não no `adaptadores/persistencia/README.md` que a lição **L-022** indica. Não bloqueia: a AC pede "documentados", e docstrings são documentação legível e versionada.

**E — `antecedencia_horas` sem asserção de valor no backend.** Nenhum teste backend lê o valor de volta pelo round-trip HTTP; o frontend cobre a exibição (`24h`, `SuperficieRegras.test.tsx:137`).

**F — REGRA-14 ordem de tabulação.** O teste usa `focus()` + `{Enter}`, padrão já vigente no projeto (`SuperficieFonteMeteorologica.test.tsx:160-173`). M9 (R2) prova que a asserção mede operabilidade real; a **ordem** dos campos segue sem guarda.

**G — REGRA-02 fronteira do limiar.** A fronteira `limiar > 0` é de ponto flutuante — "imediatamente acima" não tem valor canônico. Os três lados estão cobertos (`-5.0`, `0.0`, `50.0+`) e a mutação natural (`<= 0` → `< 0`) morre em `test_validador_regra.py:87-95`. A fronteira inteira `[1,168]`, onde o off-by-one é definível, tem os quatro valores.

**H — REGRA-03 células não asseridas.** `Severidade` e `Limiar` aparecem como cabeçalho asserido, mas seus **valores** de célula não são conferidos (a severidade é derivada em `SuperficieRegras.tsx:37-45`). Remover uma coluna morre (M8); trocar a fórmula de severidade sobreviveria.

**I — divergência de contagem em `tasks.md`.** A nota de gate em `tasks.md` afirma "343 testes" no backend; a execução real nesta rodada (e na Round 2) dá **340 passed**. Discrepância de registro no documento de tarefas, não no código nem nos gates. Cosmética.

---

## Discrimination Sensor

Uma worktree isolada e descartável (`git worktree add --detach <scratch> c0d50d1`), revertida com `git checkout -- .` entre mutações e removida com `git worktree remove --force` + `git worktree prune`. O `node_modules` do frontend foi apenas **symlinkado** para dentro da worktree e o link removido antes da remoção — nada foi escrito na árvore real. Nenhum `git stash` usado. **Baseline na worktree antes de mutar: 12/12 testes verdes** em `SuperficieRegras.test.tsx`.

### Mutante reinjetado da Round 2

| # | Mutação | File:line | Descrição | Testes executados | Killed? |
| --- | --- | --- | --- | --- | --- |
| **M10** | Indicador visual colapsado (mutação **literal** da R2) | `funcionalidades/regras/SuperficieRegras.tsx:259-262` | o template literal com o sufixo `regra-estado-badge--${regra.estado}` mais `data-indicador={regra.estado}` → `className="regra-estado-badge"` (sem `data-indicador`, sem sufixo por estado): ativa e substituída passam a ter **o mesmo indicador visual** | `SuperficieRegras.test.tsx` (12 testes) | ✅ **Killed** — `usa um ícone diferente para a versão ativa e a substituída (REGRA-04)` falha em `:100`: `expect(received).toHaveAttribute()` — *received has value: null* (o `querySelector('[data-indicador]')` não acha mais a badge). 1 failed \| 11 passed |

### Mutantes novos desta rodada (cada um ataca **uma metade** da asserção nova)

| # | Mutação | File:line | Descrição | Testes executados | Killed? |
| --- | --- | --- | --- | --- | --- |
| **M11** | Só a classe modificadora removida | `SuperficieRegras.tsx:260` | o template literal com o sufixo `regra-estado-badge--${regra.estado}` → `className="regra-estado-badge"`, **mantendo** `data-indicador={regra.estado}`: o gancho de teste sobrevive, mas o sinal **visual** (a cor por estado, `SuperficieRegras.css:23-29`) desaparece | `SuperficieRegras.test.tsx` | ✅ **Killed** — falha em `:102`: `Expected the element to have class: regra-estado-badge--ativa / Received: regra-estado-badge`. **Prova que a asserção `toHaveClass` é viva por si só** — o teste não passa só pelo `data-indicador` |
| **M12** | Só o `data-indicador` constante | `SuperficieRegras.tsx:261` | `data-indicador={regra.estado}` → `data-indicador="ativa"`, **mantendo** a classe por estado: os dois estados passam a expor o mesmo indicador semântico | `SuperficieRegras.test.tsx` | ✅ **Killed** — falha em `:101`: `toHaveAttribute('data-indicador','substituida')` não casa com `"ativa"`. **Prova que a asserção `toHaveAttribute` é viva por si só** |

**Sensor depth**: lightweight (3 mutações nesta rodada de confirmação — 1 reinjetada + 2 novas e mais sutis; somadas às 6 da Round 1 e 7 da Round 2, **16 mutações no total** sobre a história)

**Result**: **3/3 killed, 0 survived** — ✅ **PASS**. Acumulado da história: **15/16 mutantes mortos**, e o único sobrevivente histórico (M10) está agora morto.

**Verificação de isolamento**: `git status --porcelain` vazio **antes** (`BASELINE:[]`) e **depois** (`POST-SENSOR STATUS:[]`) do ciclo de mutações; `git worktree list` mostra apenas a árvore real em `c0d50d1`; o diretório de scratch não existe mais; `src/frontend/node_modules` da árvore real intacto (diretório real, não symlink). Nenhum arquivo do projeto foi modificado por esta rodada exceto este `validation.md`.

---

## Payload / Conjunction Rule

Regra aplicada: a asserção precisa olhar **valor devolvido e/ou estado persistido**, não "a chamada aconteceu" nem um status isolado.

| Alvo | Asserção verifica valor real? | Evidência |
| --- | --- | --- |
| `GET /api/v1/regras` | ✅ Sim | `test_regras_api.py:88-94` — status **+** `len == 2` **+** `estados == {"ativa","substituida"}` **+** `versoes == {1,2}`. Ordenação (`ORDER BY evento_tipo, versao DESC`) segue não asserida (conjuntos, não listas) |
| `GET /api/v1/regras/{id}` 200 | ✅ Sim | `:104-108` — status **+** `id`, `limiar_meteorologico == 50.0`, `estado == "ativa"` |
| `GET /api/v1/regras/{id}` 404 / 422 | ✅ Sim | `:117-118` — status + `content-type: application/problem+json` + `codigo == "regra_inexistente"`; `:128-129` — `codigo == "regra_id_invalido"` |
| `POST .../testar` 200 | ✅ Sim | `:140-151` — status **+** `len(casos)==1`, `relevante is True`, `motivo == "relevante"`, `valor_observado == "72.5 mm"`, `atende is True`, `"60.0 mm" in justificativa` |
| `POST .../testar` 200 vazio | ✅ Sim | `:181-182` — status **+** `casos == []` (lista vazia explícita, não erro técnico) |
| `POST .../testar` 422 | ✅ Sim | `:165-169` — status + `codigo` + `erros[].campo == "limiar_meteorologico"` |
| `POST .../ativar` 200 | ✅ Sim | `:214-221` — status **+** `versao == 2`, `estado == "ativa"`, `limiar_meteorologico == 60.0` **+ estado persistido relido** (`estado == "substituida"`, nota B) |
| `POST .../ativar` concorrente | ✅ Sim | `:262-269` — `200`+`versao == 2`, `409`+`codigo`, **e** o estado final do banco relido (`len == 2`, `{versões} == {1,2}`) |
| `POST .../ativar` idempotente | ✅ Sim | `:290-297` — **`primeira.json() == segunda.json()`** (corpo inteiro) **e** `len(regras) == 2` |
| `POST .../ativar` 409 (versão / idempotência) | ✅ Sim | `:235-236` e `:318-319` — status **+** `codigo` discriminando as duas causas |
| `POST .../ativar` 404 / 422 | ✅ Sim | `:331-332`, `:198-199`, `:346-347` — status + `codigo` específico em cada caso |
| `ServicoGestaoRegras.ativar` — efeito de avaliação | ✅ Sim | `test_gestao_regras.py:237-238` — `len(chamadas) == 1` **e** `chamadas[0][0] is evento` (identidade do cenário avaliado, não só a contagem) |
| `ServicoGestaoRegras.ativar` — efeito de escrita | ✅ Sim | `test_gestao_regras.py:199` — `regras.chamadas[0] == (regra_anterior_id, 1, DADOS_CHUVA_VALIDOS)`; `:178,187,224` — `chamadas == []` / `len == 1` para provar **ausência** de escrita |
| `RepositorioRegras.criar_nova_versao` | ✅ Sim | `test_repositorio_regras.py:107-119` — objeto devolvido **e** três releituras do banco |
| `RepositorioAvaliacoesRisco` após nova versão | ✅ Sim | `test_repositorio_regras.py:197-202` — releitura real por `obter_por_execucao` com 4 asserções de valor, incluindo a tupla de critérios |
| `listar_sinteticos_por_tipo` | ✅ Sim | `test_repositorio_meteorologia.py:123,154` — `[evento.id …] == [sintetico.id]` / `== [granizo.id]` (identidade, não contagem) |
| Superfície — tabela | ✅ Sim | `SuperficieRegras.test.tsx:118-139` — lista exata de cabeçalhos **e** 7 valores de célula |
| Superfície — teclado | ✅ Sim | `:276-290` — foco asserido em 3 elementos **e** o efeito observável do `{Enter}` (formulário aberto, painel de resultado, `testarRegra` 1×) |
| Superfície — ativação | ✅ Sim | `:255-258` — mensagem de sucesso **e** `ativarRegra` chamado com `(id, versao, objectContaining({limiarMeteorologico: 50}))` |
| **Superfície — indicador visual** | ✅ **Sim (fechado nesta rodada)** | `:100-106` — `data-indicador` **de cada estado** com o valor esperado **e** a classe modificadora **de cada estado**, mais a distinção explícita entre os dois. M10/M11/M12 mortos |

Nenhuma asserção do tipo "só contagem" ou "status isolado" permanece no contrato HTTP nem na superfície.

---

## Code Quality

| Princípio | Status |
| --- | --- |
| Minimum code | ✅ — a correção desta rodada é **+10 linhas de asserção**, zero linhas de produção. Na rodada anterior, o Fix 6 **removeu** 6 linhas duplicadas (`ativar` passou a reusar `testar`) |
| Surgical changes | ✅ — `6b33e16..c0d50d1` toca 1 arquivo de teste + 2 arquivos de documentação de spec; nenhuma migração, nenhuma rota, `openapi.json` inalterado |
| No scope creep | ✅ — o diff mapeia 1:1 para o Fix 9 nomeado pela Round 2 |
| Matches patterns | ✅ — a asserção do indicador segue o padrão de 2.3 (`SuperficieEventoDecisao.test.tsx:153`, distinção por atributo `data-*`), estendido com `toHaveClass` para cobrir também o sinal puramente visual |
| Spec-anchored outcome check | ✅ — **15/15** ACs com asserção casando o resultado da spec |
| Per-layer Coverage Expectation | ✅ — domínio 1:1 com as classes de invalidez **e** as fronteiras; rota cobre feliz + vazio + concorrente + 404 + 422 (×4 causas) + 409 (×2 causas); componente cobre teclado, colunas, ícone **e** indicador visual |
| Every test maps to a spec requirement | ✅ — as asserções novas ficaram dentro do teste já nomeado `(REGRA-04)`; nenhum teste órfão, nenhum teste novo redundante criado |
| Documented guidelines followed | ⚠️ — `AGENTS.md` e o padrão de 2.2/2.3 seguidos; a justificativa das faixas continua fora do README versionado do schema (nota D, lição **L-022**); `tasks.md` registra "343 testes" onde o real é 340 (nota I) |
| Docstring/contrato correspondem ao comportamento | ✅ — `gestao_regras.py:246` e `http/regras.py:372` afirmam reexecução do teste determinístico, e `ativar` de fato chama `avaliar` por cenário (M7 morto, R2) |

---

## Edge Cases

- [x] **Ativar combinação evento↔produto inconsistente → bloqueio com motivo específico antes do teste** — `test_validador_regra.py:166-190` (granizo + residencial; motivo cita ambos os produtos), `test_regras_api.py:165-169`. Mutante M2 morto (R1)
- [x] **Teste sem nenhum cenário sintético aplicável → resultado vazio válido, não erro técnico, e ativação segue bloqueada** — `test_gestao_regras.py:148-154` (`resultados == ()`), `:156-171` (filtragem por tipo), `test_regras_api.py:181-182` (`200` + `casos == []`), bloqueio da ativação em `:346-347` (`422 nenhum_cenario_aplicavel`) + `test_gestao_regras.py:184-191` (`regras.chamadas == []`). Frontend: `SuperficieRegras.tsx:443-444` — continua sem teste de frontend (Minor, inalterado)
- [x] **Ativação idêntica reenviada depois de a resposta ter sumido da UI (chave ainda válida) → resposta originalmente registrada** — `test_regras_api.py:290-297` (`primeira.json() == segunda.json()` + `len(regras) == 2`); serviço em `test_gestao_regras.py:211-216`
- [x] **Cenário sintético vs. evento real** — `test_repositorio_meteorologia.py:92-123` insere um `REAL_INMET` e um `SINTETICO` do mesmo tipo e assere que só o sintético volta. Mutante M4 morto (R2)

---

## Gate Check

- **Gate command (Build)**: `uv run pytest -q && uv run ruff check . && uv run pyright` (em `src/backend`) + `npx vitest run && npm run lint && npm run build` (em `src/frontend`)
- **Executado nesta rodada pelo próprio Verificador** (não herdado do orquestrador), na árvore real em `c0d50d1`:
  - `pytest`: **340 passed**, 0 failed, 0 skipped (exit 0, 18.99s)
  - `ruff check .`: **All checks passed!** (exit 0)
  - `pyright`: **0 errors, 0 warnings, 0 informations** (exit 0)
  - `vitest run`: **189 passed** em 22 arquivos, 0 failed (exit 0, 7.14s)
  - `npm run lint` (`oxlint`): exit 0 — **10 warnings**, todas pré-existentes de `react(set-state-in-effect)` / `react(only-export-components)`; a única em arquivo desta história é `SuperficieRegras.tsx:89`, mesmo padrão já aceito em `SuperficieEventoDecisao.tsx:79`, `SuperficieProntidao.tsx:84` e `SuperficieFonteMeteorologica.tsx:149`
  - `npm run build`: **✓ built in 229ms** (exit 0)
- **Test count antes da feature** (fim de 2.3, `7121003`): 292 backend / 164 frontend
- **Test count na Round 1** (`e0876e2`): 334 backend / 186 frontend
- **Test count na Round 2** (`6b33e16`): 340 backend / 189 frontend
- **Test count na Round 3** (`c0d50d1`): **340 backend / 189 frontend** — **igual à Round 2**, como esperado: o Fix 9 **fortaleceu um teste existente** em vez de acrescentar um novo
- **Delta total da história**: **+48 backend / +25 frontend**
- **Test Integrity**: ✅ nenhum teste removido no diff `6b33e16..c0d50d1`; **nenhuma asserção enfraquecida** — as 6 asserções novas são adições puras dentro de um teste já existente, e o **aumento** de poder discriminante foi medido (M10/M11/M12 morrem hoje e sobreviviam ontem)
- **Skipped**: nenhum
- **Failures**: nenhuma

---

## Fix Plans

**Nenhum item bloqueante.** Todos os Fix 1–9 das Rounds 1 e 2 estão fechados e comprovados por mutação.

### Itens Minor registrados, opcionais (não bloqueiam o encerramento da história)

- **Nota B** — asserir que `limiar_meteorologico` da versão anterior continua `50.0` após a substituição, não só o `estado` (`test_regras_api.py:214-221`).
- **Nota D** — migrar a justificativa das faixas de `dominio/validador_regra.py:7,10,16` para `adaptadores/persistencia/README.md`, como a lição **L-022** e o precedente de 2.3 (`README.md:104-122`) indicam.
- **Nota E** — asserir `antecedencia_horas == 48` na resposta de `POST .../ativar`, fechando o round-trip escrita→leitura desse campo no backend.
- **Nota F** — acrescentar a asserção de **ordem** de tabulação (`userEvent.tab()` encadeado) ao teste de REGRA-14.
- **Nota H** — asserir os valores de célula de `Severidade` e `Limiar` na linha da regra ativa (`SuperficieRegras.test.tsx:133-139`).
- **Nota I** — corrigir a contagem de testes registrada em `tasks.md` (343 → 340).
- **Integração** — montar `SuperficieRegras` em rota no `App.tsx` (lacuna declarada pelo autor, compartilhada com 2.1/2.2/2.3; deve ser tratada como item próprio, não como pendência desta história).

---

## Lições candidatas (grounding para `.specs/lessons.json`)

| Origem fundamentada | Lição proposta |
| --- | --- |
| M10 morto após 3 rodadas; L-024 reincidiu em 3 superfícies consecutivas | **Promover L-024 de `candidate` a estabelecida e ampliar**: quando um requisito enumera N sinais de distinção (texto, ícone, cor/indicador), a rodada de correção precisa asserir **todos os N**, não o subconjunto que o mutante da rodada anterior expôs. Confirmado empiricamente: fechado o terceiro sinal, o mutante correspondente morre |
| M11 e M12 mortos | **Quando um sinal é exposto por dois mecanismos (um atributo `data-*` de teste e uma classe CSS visual), asserir os dois e mutá-los separadamente** — asserir só o `data-*` deixa o sinal **visual** livre para desaparecer sem nenhum teste vermelho (M11 provaria isso); asserir só a classe deixa a semântica livre (M12). O par de asserções custa duas linhas e fecha as duas metades |
| Fix 2 fechado só pela metade na R1→R2 | Uma fix task que enumera várias asserções deve ser reverificada **item a item contra o texto da própria task**; "o mutante da rodada anterior morreu" não é evidência de que a task inteira foi executada |
| Fix 9 sem mudança de produção | Quando o mutante sobrevivente aponta para um atributo que **já existe no componente**, o diagnóstico correto é "gancho de teste morto", e a correção é uma asserção — não código novo. Rodadas de correção que adicionam produção nesse caso estão tratando o sintoma errado |
| Fix 6 (R1→R2) | Quando uma docstring ou `description` de OpenAPI promete um efeito, a correção mais barata costuma ser **fazer o código cumprir a promessa por reuso** — fecha a divergência, remove duplicação e vira testável por espião numa porta já injetável |
| M9 morto (REGRA-14) | Um teste de acessibilidade por teclado é discriminante quando o mutante natural é "trocar o elemento nativo por um `role=` focável": se o teste continua verde com um `<span role="button">`, ele mede foco, não operabilidade |

---

## Requirement Traceability Update

| Requirement | Previous Status (Round 2) | New Status (Round 3, final) |
| --- | --- | --- |
| REGRA-01 | ✅ Verified | ✅ Verified |
| REGRA-02 | ✅ Verified | ✅ Verified |
| REGRA-03 | ✅ Verified | ✅ Verified |
| REGRA-04 | ⚠️ Parcial — Needs Fix (Fix 9) | ✅ **Verified** (texto, ícone **e** indicador visual, todos com mutante morto) |
| REGRA-05 | ✅ Verified | ✅ Verified |
| REGRA-06 | ✅ Verified | ✅ Verified |
| REGRA-07 | ✅ Verified | ✅ Verified |
| REGRA-08 | ✅ Verified | ✅ Verified |
| REGRA-09 | ✅ Verified | ✅ Verified |
| REGRA-10 | ✅ Verified | ✅ Verified |
| REGRA-11 | ✅ Verified | ✅ Verified |
| REGRA-12 | ✅ Verified | ✅ Verified |
| REGRA-13 | ✅ Verified | ✅ Verified |
| REGRA-14 | ✅ Verified | ✅ Verified |
| REGRA-15 | ✅ Verified | ✅ Verified |

**15/15 Verified.**

---

## Summary

**Overall**: ✅ **PASS** — história 2.4 verificada; nenhum item bloqueante aberto

**Spec-anchored check**: **15/15 ACs** com asserção casando exatamente o resultado definido pela spec. **Zero spec-precision gaps**
**Sensor**: **3/3 mutantes mortos** nesta rodada (M10 reinjetado literalmente + M11 e M12 novos, cada um atacando uma metade da asserção nova). Acumulado da história: **15/16 mortos**, e o único sobrevivente histórico está morto
**Gate**: 340 backend + 189 frontend passed, 0 failed, 0 skipped; `ruff`/`pyright`/`lint`/`build` verdes — todos re-executados pelo Verificador na árvore real

**O que funciona**: o Fix 9 fecha o último item da história com o mínimo possível — **zero linhas de produção**, seis asserções dentro do teste `(REGRA-04)` que já existia. E foi medido, não aceito: o mutante M10 da Round 2 foi reinjetado exatamente como descrito (as duas badges colapsadas em `className="regra-estado-badge"`, sem `data-indicador`) e **morre em `:100`**, com o `querySelector` devolvendo `null`. Mais importante, duas mutações **novas e mais sutis** provam que a asserção não tem metade morta: remover só a classe modificadora (mantendo o `data-indicador`) **mata** em `:102`, e fixar o `data-indicador` numa constante (mantendo a classe) **mata** em `:101`. Ou seja, o sinal semântico e o sinal visual estão guardados de forma independente — exatamente o que a AC "texto, ícone **e** indicador visual" exige. O spot-check dos `file:line` das outras ACs (REGRA-02, REGRA-11, REGRA-14 e a delegação `ativar → testar`) confirma que nada regrediu; a contagem de testes é idêntica à da Round 2, coerente com uma correção que fortalece um teste existente em vez de criar um novo.

**Problemas encontrados**: nenhum bloqueante. Persistem seis itens Minor já registrados e aceitos nas rodadas anteriores (notas B, D, E, F, H) mais uma discrepância cosmética nova (nota I: `tasks.md` registra 343 testes backend, o real é 340). A lacuna de integração — `SuperficieRegras` não montada em rota no `App.tsx` — segue **declarada pelo autor** e compartilhada com as três superfícies anteriores; não é defeito desta história, mas deve virar item próprio antes da demonstração.

**Next steps**: encerrar a história 2.4 como **Verified** (15/15 REGRA-NN), atualizar o `Status` da tabela de rastreabilidade na `spec.md` de `Pending`/`Implementing` para `Verified` e promover a lição **L-024** de `candidate` a estabelecida, ampliando-a com o achado de M11/M12 ("quando um sinal tem duas expressões — atributo de teste e classe visual — asserir e mutar as duas"). Os itens das notas B, D, E, F, H e I são opcionais e podem ser agrupados numa varredura de qualidade posterior. Esta foi a **iteração 3 de no máximo 3** e a história fecha dentro do orçamento.
