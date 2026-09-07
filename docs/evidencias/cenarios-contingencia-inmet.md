# Cenário E2E-05 — contingência do INMET: indisponibilidade controlada e cenário sintético.

**Arquivo de teste**: `testes-e2e/cenarios/contingencia-inmet.spec.ts`
**Requisitos**: E2E-05
**Status**: PASSOU

## Casos de teste (evidência `file:line`)

| Caso | Local | Resultado |
| --- | --- | --- |
| esgota tentativas, preserva o snapshot e segue pelo cenario sintetico rotulado | `testes-e2e/cenarios/contingencia-inmet.spec.ts:66` | ✅ passou |

## Contexto do cenário

Cópia do comentário de cabeçalho do arquivo de teste — inclui desvios conhecidos, tabelas de rastreabilidade e o que a IA não pode inventar sem editar o teste.

O cenário tem três atos. Primeiro uma coleta bem-sucedida, que deixa um snapshot válido no
histórico. Depois o INMET é derrubado (todas as respostas seguram a conexão até o cliente
desistir): a superfície de Prontidão real passa a exibir o INMET como indisponível, e uma
execução preventiva iniciada nesse estado esgota as três tentativas e termina em
`falhou_coleta` — com o snapshot anterior permanecendo consultável, mas sem nenhuma
avaliação de risco nova a partir dele (RESIL-06/07). Por fim o cenário sintético rotulado é
ativado explicitamente e leva o fluxo até o comunicado, com `proveniencia = sintetico`
visível do evento normalizado até a tela do segurado (AD-013).

As etapas administrativas de coleta/execução são dirigidas pela API REST porque as
superfícies de Administrador dos Épicos 2–4 ainda não estão montadas em `App.tsx` (item
aberto registrado em `.specs/STATE.md`). As duas superfícies montadas que o cenário exige
ver — Prontidão e o painel do Segurado — são exercitadas na interface real.
