# Cenário E2E-04 — regeneração automática e esgotamento das três tentativas.

**Arquivo de teste**: `testes-e2e/cenarios/regeneracao.spec.ts`
**Requisitos**: E2E-04
**Status**: PASSOU

## Casos de teste (evidência `file:line`)

| Caso | Local | Resultado |
| --- | --- | --- |
| regenera ate a terceira tentativa e esgota em falhou_conteudo com excecao | `testes-e2e/cenarios/regeneracao.spec.ts:58` | ✅ passou |

## Contexto do cenário

Cópia do comentário de cabeçalho do arquivo de teste — inclui desvios conhecidos, tabelas de rastreabilidade e o que a IA não pode inventar sem editar o teste.

Mesma entrada do cenário de chuva intensa, com uma diferença: o dublê do agente crítico
reprova toda avaliação. Como o crítico e o redator compartilham a rota
`POST /v1/chat/completions` e se distinguem pelo `response_format.json_schema.name`, a
reprovação é programada só na fila do esquema `AvaliacaoEstruturada` — o redator segue
respondendo normalmente, e cada reprovação devolve a mensagem ao redator (REGEN-01).

O cenário comprova as duas metades do AC: o ciclo reprova→regenera acontece até a terceira
tentativa, e a terceira reprovação fecha a mensagem em `falhou_conteudo` com uma `Exceção`
própria, mantendo-a fora do lote simulável — nada do que ela gerou chega ao segurado.
