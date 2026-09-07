# Cenário E2E-03 (metade "sem público elegível") — evento relevante, ninguém elegível.

**Arquivo de teste**: `testes-e2e/cenarios/sem-elegivel.spec.ts`
**Requisitos**: E2E-03
**Status**: PASSOU

## Casos de teste (evidência `file:line`)

| Caso | Local | Resultado |
| --- | --- | --- |
| encerra em sem_elegiveis com motivo consultavel e sem nenhuma chamada a OpenAI | `testes-e2e/cenarios/sem-elegivel.spec.ts:41` | ✅ passou |

## Contexto do cenário

Cópia do comentário de cabeçalho do arquivo de teste — inclui desvios conhecidos, tabelas de rastreabilidade e o que a IA não pode inventar sem editar o teste.

Diferente do cenário `sem_risco`, aqui o evento **é** relevante: a regra de chuva intensa é
atingida e a avaliação de elegibilidade roda. O que falta é público. O conjunto sintético
traz um segurado que já não é elegível (apólice cancelada); o outro sai do público pela
própria superfície de preferências, desligando a participação em alertas (PREFS) — nenhuma
edição de arquivo ou de banco, só a API real.

O encerramento é `sem_elegiveis`, com o motivo de exclusão de cada registro consultável, e
de novo sem nenhuma chamada à OpenAI, mensagem ou simulação.
