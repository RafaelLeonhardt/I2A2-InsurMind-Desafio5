# Cenário E2E-03 (metade "sem risco") — evento que não atinge nenhuma regra.

**Arquivo de teste**: `testes-e2e/cenarios/sem-risco.spec.ts`
**Requisitos**: E2E-03
**Status**: PASSOU

## Casos de teste (evidência `file:line`)

| Caso | Local | Resultado |
| --- | --- | --- |
| encerra em sem_risco com motivo consultavel e sem nenhuma chamada a OpenAI | `testes-e2e/cenarios/sem-risco.spec.ts:29` | ✅ passou |

## Contexto do cenário

Cópia do comentário de cabeçalho do arquivo de teste — inclui desvios conhecidos, tabelas de rastreabilidade e o que a IA não pode inventar sem editar o teste.

Uma leitura real de chuva abaixo do limiar da regra ativa encerra a execução em
`sem_risco`, com motivo tipado e critérios consultáveis. O ponto do AC é o que **não**
acontece a partir daí: nenhuma chamada à OpenAI, nenhuma mensagem gerada e nenhuma
simulação registrada. O diário do servidor de dublês é a evidência direta disso — ele
registra toda requisição que chegaria à OpenAI, e as duas listas precisam estar vazias.
