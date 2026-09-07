# História 5.9: Preparar e empacotar a entrega final — Validation

**Date**: 2026-09-07
**Spec**: `.specs/features/5-9-preparar-e-empacotar-a-entrega-final/spec.md`
**Diff range**: `e0aed8a..HEAD` — feature completa T1–T4 (`165c54f`, `7fcbf30`, `cdd24ce`, `b974132`, `0b2a126`, `1c56ae9`, `be3c61a`, `5319eac`)
**Verifier**: independent sub-agent (author ≠ verifier)
**Rodada de verificação**: **2** de no máximo 3 (loop fix→re-verify)

**Verdict**: ✅ **PASS** — os cinco blockers/majors da rodada 1 estão corrigidos e comprovados: 11 de 12 mutações injetadas agora são mortas (contra 2 de 7 na rodada 1), todas as cinco ACs em escopo têm evidência `file:line` que mira o valor definido pela spec, e os três artefatos foram regerados e inspecionados de forma independente por este Verifier. Resta **um** ponto sinalizado, não bloqueante: uma sobrevivência estreita (M10) que degrada a riqueza da seção "Arquitetura implementada" sem violar nenhum resultado definido pela spec — classificada como **spec-precision gap**, não como falha de cobertura (ver Discrimination Sensor).

**Escopo desta passagem**: apenas ENTREGA-01..ENTREGA-05 (T1–T4). **ENTREGA-06/ENTREGA-07 (T5 — publicação em serviço externo) estão fora de escopo por decisão explícita da pessoa usuária nesta sessão ("Not now")**: é uma ação manual, irreversível e de blast radius remoto que, pela própria AC ENTREGA-06 e pelo contrato de blast radius do processo, só pode ocorrer mediante autorização explícita para aquele ato específico. A ausência de T5 **não é um gap** — é o estado pendente correto e sancionado pela spec.

---

## Task Completion

| Task | Status | Notes |
| --- | --- | --- |
| T1 `gerar_relatorio_tecnico.py` | ✅ Done | Testes agora comparam contra marcadores lidos direto do arquivo-fonte; M3/M4/M5 mortos |
| T2 `empacotar_entrega.py` | ✅ Done | Bug real corrigido em `_esta_excluido()` (padrões aninhados); filtro defensivo, licença MIT e varredura de segredos agora cobertos; M1/M7/M8/M9/M11/M12 mortos |
| T3 `gerar_inventario.py` | ✅ Done | Teste vacuoso de auto-exclusão corrigido; M2/M6 mortos |
| T4 Validação de checkout/ZIP | ✅ Done | Evidência movida para `docs/evidencias/validacao-checkout-entrega.md`, rastreada pelo Git e confirmada dentro do ZIP gerado |
| T5 Publicação autorizada | ⛔ Fora de escopo | Autorização explícita recusada nesta sessão; estado pendente correto por ENTREGA-06 |

---

## Spec-Anchored Acceptance Criteria

| Criterion (WHEN X THEN Y) | Spec-defined outcome | `file:line` + assertion | Result |
| --- | --- | --- | --- |
| **ENTREGA-01** (`spec.md:49`) WHEN o relatório for gerado THEN um PDF SHALL existir com arquitetura, agentes, tecnologias, fluxo, decisões, limitações, evidências e exemplos sanitizados, verificável contra a implementação e os artefatos canônicos | PDF com as 8 seções nomeadas, cada uma com **corpo derivado do artefato canônico real** | Cabeçalhos: `testes/test_gerar_relatorio_tecnico.py:69-71` — `assert cabecalho in relatorio_pdf` (8 parametrizações). Corpo, cada um contra marcador lido **direto da fonte** via `_ler_bruto()`: `:80-83` (`"Uso de DuckDB como banco de dados"` ← `ADR_README`), `:86-90` (título do ADR-0012 lido do arquivo), `:93-96` (`"duckdb>=1.4.4,<2"` ← `BACKEND_PYPROJECT`), `:99-103` (`"Coleta de dados em uma fonte pública…"` ← `README_MD`), `:106-110` (`"DuckDB schema evolves through numbered"` ← `STATE_MD`), `:113-117` (`"Superfícies órfãs do perfil"` ← `STATE_MD`), `:120-124` (`"chuva intensa residencial"` ← `EVIDENCIAS_DIR/README.md`). Cada teste tem asserção de sanidade da fonte antes da asserção sobre o PDF. **Confirmado por execução real deste Verifier**: PDF de 9 páginas, 21.643 caracteres, 8/8 seções e 6/6 marcadores presentes | ✅ **PASS** — assertions agora miram o conteúdo canônico, não só o rótulo. M3 e M4 mortos |
| **ENTREGA-01** (exemplos sanitizados, `spec.md:49`) | Mensagens = a constante canônica `CONTEUDO_PADRAO_DUBLE` de `testes-e2e/suporte/servidor-dubles.ts`, não texto inventado | `testes/test_gerar_relatorio_tecnico.py:33-37` — literais `WHATSAPP_CANONICO`/`SMS_CANONICO` hardcoded como valor independente; `:127-132` — `assert WHATSAPP_CANONICO in relatorio_pdf` / `assert SMS_CANONICO in relatorio_pdf`; `:135-140` — `assert conteudo["whatsapp"] == WHATSAPP_CANONICO` (trava que aponta onde atualizar se o dublê mudar). Confirmado na execução real: `"Comunicacao preventiva"` presente no PDF | ✅ **PASS** — tautologia da rodada 1 eliminada; os dois lados da comparação não vêm mais da mesma função. M5 morto |
| **ENTREGA-02** (`spec.md:50`) WHEN o pacote for montado THEN um ZIP completo e sanitizado SHALL ser gerado, sem `.env`, chaves, dados pessoais reais, caches ou artefatos operacionais indevidos | Nenhum `.env`, `.venv/`, `node_modules/`, `__pycache__/`, `var/`, `*.duckdb`, `*.pyc`, `docs/entrega/`; presença de `src/`, `docs/evidencias/`, `README.md`, `LICENSE` | Nomes: `testes/test_empacotar_entrega.py:52-54`, `:57-60` (6 padrões), `:63-66` (3 sufixos), `:69-71`, `:74-87` (5 arquivos essenciais). **Filtro defensivo, antes descoberto**: `:102-123` — `assert modulo._esta_excluido(caminho) is esperado` em 15 casos, incluindo os aninhados `sub/.env`, `sub/.venv/lib/x.py`; `:126-143` — repositório temporário com `.env` **force-added ao Git**, provando que é `_esta_excluido()`, não o `.gitignore`, que o remove. Confirmado por execução real: 612 arquivos, varredura de padrões proibidos = 0 resultados | ✅ **PASS** — M1, M7, M8, M9 mortos |
| **ENTREGA-03** (`spec.md:64`) WHEN os arquivos e o histórico do repositório forem verificados THEN eles SHALL conter README reproduzível, licença MIT e toda a documentação exigida, livres de segredos conhecidos e arquivos impróprios | `LICENSE` com texto MIT + zero segredos conhecidos no conteúdo dos arquivos (o Independent Test de `spec.md:52` exige busca automatizada **no conteúdo**, não só em nomes) | Dono agora existe: `tasks.md:93` T2 → `ENTREGA-02, ENTREGA-03`, com Done-when em `tasks.md:101`. `testes/test_empacotar_entrega.py:90-92` — `assert conteudo.startswith("MIT License")` lido do ZIP; `:36-42` + `:95-99` — varredura de 5 padrões (`sk-…`, `AKIA…`, `gh[pousr]_…`, `xox[baprs]-…`, cabeçalho PEM) sobre **os bytes de todos os 612 arquivos do ZIP**. Confirmado independentemente: `LICENSE:1` = `MIT License`; varredura própria deste Verifier sobre o ZIP = 0 resultados | ✅ **PASS** — gap da rodada 1 fechado. M11 (LICENSE trocada por Apache) e M12 (segredo plantado em arquivo rastreado) mortos |
| **ENTREGA-04** (`spec.md:65`) WHEN instalação e execução forem validadas a partir de checkout limpo e do ZIP final THEN ambas SHALL funcionar só com os comandos documentados, sem etapa manual oculta nem dependência de artefato operacional local | Ambos os caminhos instalam e executam com comandos do README; `var/central_preventiva.duckdb` criado do zero | `docs/evidencias/validacao-checkout-entrega.md:23-33` (tabela de 9 comandos do README × 2 ambientes) e `:44-56` (confirmações do AC: nenhuma etapa oculta além do `cp -n .env.example .env` documentado; `var/` criado do zero em ambos; ZIP sem `.git/`). **Agora rastreado pelo Git** (`git ls-files` confirma) e **presente dentro do ZIP gerado** (`central-preventiva/docs/evidencias/validacao-checkout-entrega.md`, verificado por este Verifier). Os 4 comandos citados foram conferidos por este Verifier como literalmente presentes em `README.md` | ✅ **PASS** — gate manual por natureza (a AC exige execução em ambiente limpo), mas a evidência agora acompanha a entrega, como exige "repositório contém toda a documentação exigida". Fix 6 resolvido |
| **ENTREGA-05** (`spec.md:66`) WHEN o inventário for fechado THEN nomes, tamanhos e checksums SHALL ser registrados, permitindo verificar a integridade do PDF, ZIP e demais arquivos | `nome`, `tamanho_bytes`, `sha256` por artefato, batendo com o conteúdo real | `testes/test_gerar_inventario.py:32-42` — `assert registro["tamanho_bytes"] == caminho.stat().st_size` e `assert registro["sha256"] == hashlib.sha256(caminho.read_bytes()).hexdigest()`; `:45-65` — checksum diverge após alteração e volta a bater após regenerar; `:81-91` — auto-exclusão agora testada com **duas** chamadas a `gerar()` (a 1ª cria `inventario.json`, só a 2ª exercita o filtro). Confirmado independentemente: os 3 artefatos batem em tamanho e SHA-256 recalculado | ✅ **PASS** — M2 e M6 mortos |

**Status**: ✅ 5/5 ACs em escopo cobertas e ancoradas na spec; 1 spec-precision gap sinalizado (não bloqueante, ver M10).

---

## Discrimination Sensor

Escopo isolado: `git worktree add -f <scratchpad>/wt HEAD` (detached em `5319eac`); baseline no worktree = **70 passed**. Cada mutação aplicada isoladamente e revertida com `git checkout -- .` antes da seguinte. Nenhuma mutação tocou a árvore real.

M1–M7 são as **mesmas sete mutações da rodada 1**, reinjetadas do zero (não confiando na alegação do autor). M8–M12 são novas, desenhadas por este Verifier para atacar exatamente os testes recém-criados.

| # | Mutação | File:line | Descrição | Rodada 1 | Rodada 2 |
| --- | --- | --- | --- | --- | --- |
| M1 | Filtro de sanitização neutralizado | `scripts/empacotar_entrega.py:49` | `_esta_excluido()` devolve sempre `False` | ❌ Sobreviveu | ✅ **Killed** (`test_esta_excluido_…`, `test_filtro_defensivo_remove_env_mesmo_se_rastreado_pelo_git`) |
| M2 | Checksum constante | `scripts/gerar_inventario.py:34` | `_sha256()` devolve `sha256(b"")` | ✅ Killed | ✅ **Killed** (2 failed) |
| M3 | Seção de evidências vazia | `scripts/gerar_relatorio_tecnico.py:241` | `montar_evidencias()` devolve `""` | ❌ Sobreviveu | ✅ **Killed** (`test_secao_evidencias_contem_cenario_real_de_5_8`) |
| M4 | Falha silenciosa em artefato ausente | `scripts/gerar_relatorio_tecnico.py:80` | `_ler()` devolve `""` em vez de levantar `EvidenciaAusente` | ❌ Sobreviveu | ✅ **Killed** (`test_gerar_nao_escreve_saida_quando_artefato_citado_esta_ausente`) |
| M5 | Exemplo de mensagem inventado | `scripts/gerar_relatorio_tecnico.py:251` | `_extrair_conteudo_duble()` devolve `"texto fixo inventado"` | ❌ Sobreviveu | ✅ **Killed** (`test_extrator_de_mensagem_bate_com_o_literal_canonico`) |
| M6 | Inventário se auto-inclui | `scripts/gerar_inventario.py:45` | `listar_artefatos()` deixa de filtrar `excluir` | ❌ Sobreviveu | ✅ **Killed** (`test_inventario_nao_inclui_a_si_mesmo`) |
| M7 | Pasta raiz do ZIP removida | `scripts/empacotar_entrega.py:87` | `arcname` sem o prefixo `central-preventiva/` | ✅ Killed | ✅ **Killed** |
| **M8** *(nova)* | Regressão do bug de caminho aninhado | `scripts/empacotar_entrega.py:58` | `elif prefixo in partes` → `elif partes[0] == prefixo` (restaura o bug real corrigido em `1c56ae9`: padrão só casava na raiz) | — | ✅ **Killed** (`sub/.env`, `sub/.venv/lib/x.py`) |
| **M9** *(nova)* | Filtro de sufixos desligado | `scripts/empacotar_entrega.py:62` | `*.duckdb`/`*.pyc`/`*.pyo` deixam de ser excluídos | — | ✅ **Killed** |
| **M10** *(nova)* | Prosa de arquitetura silenciosamente vazia | `scripts/gerar_relatorio_tecnico.py:86` | `_intro()` devolve `""` — a seção "Arquitetura implementada" perde a prosa do `README.md` e do `docs/design/README.md`, mantendo só as linhas de ADR | — | ⚠️ **Sobreviveu** (ver análise abaixo) |
| **M11** *(nova)* | Licença trocada por não-MIT | dado: `LICENSE` | `LICENSE` substituída por texto Apache 2.0 no scratch | — | ✅ **Killed** (`test_zip_licenca_e_mit`) |
| **M12** *(nova)* | Segredo plantado em arquivo rastreado | dado: `docs/evidencias/vazamento-teste.md` | Arquivo `git add -f` contendo `AKIAIOSFODNN7EXAMPLE` e `sk-…` | — | ✅ **Killed** (`test_zip_nao_contem_nenhum_padrao_de_chave_conhecida`) |

**Sensor depth**: P0-estendido (12 mutações, cobrindo todos os ramos novos dos três scripts)
**Result**: **11/12 killed, 1 survived** — ✅ PASS (rodada 1 foi 2/7)

**Isolamento verificado**: `git status --porcelain` da árvore real antes do sensor = `?? .specs/features/5-9-…/validation.md`; depois do sensor = idêntico (`diff` vazio). `git worktree remove --force` + `git worktree prune` executados; `git worktree list` mostra apenas a árvore principal. Nenhum `git stash` usado.

### Análise da sobrevivência (M10) — spec-precision gap, não gap de cobertura

`_intro()` alimenta apenas `montar_arquitetura()` (`scripts/gerar_relatorio_tecnico.py:116-117`), somando a prosa introdutória do `README.md` e do `docs/design/README.md` às linhas de ADR de arquitetura. Com `_intro()` devolvendo `""`, a seção **continua não-vazia e continua derivada de artefato canônico**: as linhas de `docs/adr/README.md` permanecem, e a guarda `if not linhas_relevantes: raise EvidenciaAusente` (`:123-124`) continua ativa. O PDF resultante ainda satisfaz a letra de ENTREGA-01 ("arquitetura implementada … verificável contra a implementação e os artefatos canônicos").

Ou seja: a spec **não define com precisão** qual prosa do README/design deve aparecer nessa seção, então a mutação degrada a riqueza sem violar nenhum resultado definido pela spec. Pela regra de `validate.md:50`, isso é marcado como **⚠️ spec-precision gap** e sinalizado — não silenciosamente aprovado, e não tratado como falha de discriminação. **Correção sugerida (não bloqueante, ~4 linhas)**: acrescentar a `testes/test_gerar_relatorio_tecnico.py` uma asserção de que um marcador da introdução do `README.md` e outro da introdução do `docs/design/README.md` (ambos lidos por `_ler_bruto`) aparecem no PDF.

---

## Code Quality

| Princípio | Status |
| --- | --- |
| Minimum code | ✅ |
| Surgical changes | ✅ — as correções tocaram só os 3 testes, 1 script (bug real) e os artefatos de spec; nenhum arquivo de aplicação alterado |
| No scope creep | ✅ — T5 corretamente não implementada |
| Matches patterns | ✅ — pt-BR, docstrings citando a AC, convenção de `docs/evidencias/` herdada de 5.8 |
| Spec-anchored outcome check | ✅ — todas as asserções miram valor definido pela spec, lido da fonte independente |
| Per-layer Coverage Expectation met | ✅ — a matriz de `tasks.md:24-27` exige "falha explícita se evidência ausente"; agora discriminado por `test_ler_falha_explicita_com_mensagem_precisa_quando_arquivo_ausente` e pelas 8 parametrizações de `test_gerar_nao_escreve_saida_…` |
| Todo teste mapeia a um requisito | ✅ — nenhum teste órfão |
| Diretrizes documentadas seguidas | ✅ — `AGENTS.md`, `README.md` |

**Observações menores, não bloqueantes (cosméticas, documentais):**

1. `tasks.md:27` — a linha 4 da Test Coverage Matrix ainda aponta o roteiro para `docs/entrega/validacao-checkout.md`; o corpo de T4 (`tasks.md:133,145`) já foi corrigido para `docs/evidencias/validacao-checkout-entrega.md`. Resíduo do Fix 6.
2. `testes/test_gerar_inventario.py:3` — a docstring ainda rotula o arquivo como `ENTREGA-03`; após a correção de rótulos (`5319eac`) o inventário é `ENTREGA-05`. Só a docstring; o mapeamento em `tasks.md:115` está correto.
3. `scripts/gerar_relatorio_tecnico.py:245-248` — `arquivos` segue calculado só para a guarda de diretório vazio e descartado (observação repetida da rodada 1; permanece funcional).

---

## Edge Cases

- [x] `spec.md:89` — regenerar PDF/ZIP sobrescreve de forma limpa: `testes/test_gerar_relatorio_tecnico.py:192-203` e `testes/test_empacotar_entrega.py:186-193`. ✅
- [x] `spec.md:90` — evidência ausente faz o script falhar explicitamente sem gerar PDF com lacuna: `testes/test_gerar_relatorio_tecnico.py:143-151` (mensagem exata da exceção, via `pytest.raises(match=…)`) e `:154-179` (8 artefatos citados × asserção de que **nenhuma saída** `.md`/`.pdf` é escrita). Discriminado — M4 morto. ✅
- [x] `spec.md:91` — checksums refletem o conteúdo atual após alteração: `testes/test_gerar_inventario.py:45-65`, reconferido independentemente com `hashlib.sha256` sobre os 3 artefatos reais. ✅

---

## Gate Check

- **Quick/Build gate**: `uv run --directory . pytest testes/` → **70 passed, 0 failed, 0 skipped, 2.41s**
- **Build gate (pipeline completa)**: `gerar_relatorio_tecnico.py && empacotar_entrega.py && gerar_inventario.py` → exit 0
  - `docs/entrega/relatorio-tecnico.pdf` — 18.382 bytes, 9 páginas, 8/8 seções e 6/6 marcadores canônicos presentes
  - `docs/entrega/entrega.zip` — 31.541.536 bytes, 612 arquivos, 0 padrões proibidos, 0 padrões de chave conhecida no conteúdo, `LICENSE` = MIT, evidência de checkout inclusa
  - `docs/entrega/inventario.json` — 3 artefatos, tamanhos e SHA-256 reconferidos byte a byte
- **Test count antes da feature**: 0 em `testes/`
- **Test count na rodada 1**: 38
- **Test count depois (rodada 2)**: 70 — **Delta total: +70; delta desta rodada: +32**
- **Skipped**: nenhum
- **Failures**: nenhuma
- **Test Integrity Check**: contagem só cresceu; nenhuma asserção enfraquecida — ao contrário, a tautologia de `_extrair_conteudo_duble()` foi substituída por literal independente e o teste vacuoso de auto-exclusão passou a exercitar o filtro

---

## Fix Plans

Nenhum bloqueador. Itens opcionais, todos sinalizados acima e nenhum impedindo a conclusão de T1–T4:

### Fix A (Minor, opcional): fechar o spec-precision gap M10

- **Root cause**: nenhum teste afirma que a prosa introdutória do `README.md` e do `docs/design/README.md` chega à seção "Arquitetura implementada"; a spec também não define esse conteúdo com precisão.
- **Fix task**: em `testes/test_gerar_relatorio_tecnico.py`, acrescentar asserção de um marcador de cada uma dessas duas introduções, lido por `_ler_bruto()`.
- **Priority**: Minor (ENTREGA-01)

### Fix B (Cosmetic): resíduos documentais

- `tasks.md:27` — atualizar a Test Coverage Matrix para `docs/evidencias/validacao-checkout-entrega.md`.
- `testes/test_gerar_inventario.py:3` — trocar `ENTREGA-03` por `ENTREGA-05` na docstring.
- **Priority**: Cosmetic

---

## Requirement Traceability Update

| Requirement | Previous Status | New Status |
| --- | --- | --- |
| ENTREGA-01 | Implementing | ✅ **Verified** (com spec-precision gap M10 sinalizado) |
| ENTREGA-02 | Implementing | ✅ **Verified** |
| ENTREGA-03 | Implementing | ✅ **Verified** |
| ENTREGA-04 | Implementing | ✅ **Verified** |
| ENTREGA-05 | Implementing | ✅ **Verified** |
| ENTREGA-06 | Pending | Pending — fora de escopo (autorização de publicação recusada nesta sessão) |
| ENTREGA-07 | Pending | Pending — fora de escopo (depende de ENTREGA-06) |

---

## Summary

**Overall**: ✅ Ready (T1–T4). História permanece pendente quanto a T5, exatamente como ENTREGA-06 exige.

**Spec-anchored check**: 5/5 ACs em escopo com asserção que mira o resultado definido pela spec; 1 spec-precision gap sinalizado
**Sensor**: 11/12 mutações mortas (rodada 1: 2/7)
**Gate**: 70 passed, 0 failed

**O que funciona**: os três scripts produzem artefatos corretos e independentemente verificáveis — PDF de 9 páginas cujo conteúdo este Verifier confrontou marcador a marcador com os artefatos-fonte; ZIP de 612 arquivos sem `.env`, cache, artefato operacional ou padrão de chave conhecida no **conteúdo** dos arquivos, com `LICENSE` MIT; inventário cujos SHA-256 batem byte a byte. A evidência de ENTREGA-04 agora é rastreada pelo Git e viaja dentro do ZIP. Todos os seis Fixes da rodada 1 foram aplicados e, mais importante, **comprovados por reinjeção independente das mutações originais** — não apenas pela alegação do autor. A correção de `_esta_excluido()` (`1c56ae9`) foi um bug real de sanitização, não cosmético: padrões como `.venv/` e `__pycache__/` só casavam na raiz e nunca em subdiretórios.

**Problemas encontrados**: uma sobrevivência estreita (M10) que empobrece a seção de arquitetura sem violar resultado definido pela spec, e dois resíduos documentais cosméticos. Nada bloqueante.

**Next steps**: T1–T4 concluídas e verificadas; marcar ENTREGA-01..05 como `Verified` em `spec.md`. Fixes A e B são opcionais. **T5 (ENTREGA-06/07) permanece pendente até autorização explícita da pessoa usuária para publicar** — não deve ser executada, sugerida como automática, nem presumida.
