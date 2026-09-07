# Cenário E2E-02 — granizo automóvel, da entrada sintética rotulada ao comunicado.

**Arquivo de teste**: `testes-e2e/cenarios/granizo.spec.ts`
**Requisitos**: E2E-02
**Status**: PASSOU

## Casos de teste (evidência `file:line`)

| Caso | Local | Resultado |
| --- | --- | --- |
| avanca do cenario sintetico rotulado ate o comunicado do segurado elegivel | `testes-e2e/cenarios/granizo.spec.ts:60` | ✅ passou |

## Contexto do cenário

Cópia do comentário de cabeçalho do arquivo de teste — inclui desvios conhecidos, tabelas de rastreabilidade e o que a IA não pode inventar sem editar o teste.

Mesma forma do cenário de chuva intensa, com uma diferença que o AD-013 impõe: granizo não
existe nas leituras horárias de estação automática do INMET, então a entrada meteorológica
vem do cenário sintético rotulado — ativado explicitamente por
`POST /meteorologia/cenarios-sinteticos/granizo-demonstrativo/ativar` e servido pelo dublê
do INMET no mesmo formato de payload que `AdaptadorCenarioSintetico` produz. O evento
resultante carrega `proveniencia = sintetico` do começo ao fim do fluxo.

O cenário confirma o que é específico deste evento: a regra de granizo (limiar, tipo de
apólice, cobertura exigida, canal), a apólice de automóvel do segurado incluído, o canal SMS
e as recomendações preventivas de granizo apresentadas ao segurado.
