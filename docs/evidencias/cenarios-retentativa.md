# Cenário E2E-07 — retentativa correlacionada a partir de uma falha terminal, sem duplicação.

**Arquivo de teste**: `testes-e2e/cenarios/retentativa.spec.ts`
**Requisitos**: E2E-07
**Status**: PASSOU

## Casos de teste (evidência `file:line`)

| Caso | Local | Resultado |
| --- | --- | --- |
| cria execucao correlacionada com snapshots validos e nao duplica ao repetir | `testes-e2e/cenarios/retentativa.spec.ts:40` | ✅ passou |

## Contexto do cenário

Cópia do comentário de cabeçalho do arquivo de teste — inclui desvios conhecidos, tabelas de rastreabilidade e o que a IA não pode inventar sem editar o teste.

A execução de origem é levada a `falhou_preparacao_ia` derrubando a OpenAI durante o
preflight (mesmo caminho de E2E-06). Com a OpenAI de volta, a nova tentativa é pedida pelo
comando real: ela cria uma execução nova, correlacionada por `execucao_origem_id`, com
cópias próprias das linhas de elegibilidade da origem (AD-012) — a origem nunca é reaberta
nem mutada (AD-009).

A segunda metade do AC é a idempotência: repetir o comando com a mesma `Idempotency-Key`
devolve a execução já criada, sem criar uma segunda nem duplicar o efeito (AD-002).

As etapas são dirigidas pela API REST porque as superfícies de Administrador dos Épicos 2–4
ainda não estão montadas em `App.tsx` (item aberto registrado em `.specs/STATE.md`).
