# Cenário E2E-06 — produção agêntica alcançada com a OpenAI indisponível ou mal configurada.

**Arquivo de teste**: `testes-e2e/cenarios/indisponibilidade-openai.spec.ts`
**Requisitos**: E2E-06
**Status**: PASSOU

## Casos de teste (evidência `file:line`)

| Caso | Local | Resultado |
| --- | --- | --- |
| termina em falhou_preparacao_ia sem texto fixo e preserva o trabalho deterministico | `testes-e2e/cenarios/indisponibilidade-openai.spec.ts:68` | ✅ passou |
| termina em falhou_preparacao_ia quando o modelo configurado nao esta no catalogo | `testes-e2e/cenarios/indisponibilidade-openai.spec.ts:150` | ✅ passou |

## Contexto do cenário

Cópia do comentário de cabeçalho do arquivo de teste — inclui desvios conhecidos, tabelas de rastreabilidade e o que a IA não pode inventar sem editar o teste.

O fluxo determinístico (coleta, normalização, relevância, elegibilidade) roda inteiro e
chega a `aguardando_geracao`. Só então o preflight de IA é acionado: as três tentativas
falham, a execução termina em `falhou_preparacao_ia` e nenhuma chamada de geração chega a
acontecer. O que o AC exige provar é o negativo — nenhum texto fixo substituindo a resposta
da IA, nenhum modelo alternativo — e o positivo, que todo o trabalho determinístico anterior
continua consultável.

Dois desfechos de bloqueio são cobertos, ambos terminando em `falhou_preparacao_ia` com
causas distintas: OpenAI inalcançável (falha de transporte) e modelo configurado ausente do
catálogo (configuração inconsistente).

SPEC_DEVIATION: a variante literal "`OPENAI_API_KEY` ausente" não é exercitada aqui. O
backend real da suíte é iniciado uma única vez pelo `globalSetup`, com porta fixa e um único
escritor DuckDB; derrubá-lo e reiniciá-lo sem credencial no meio de um cenário deixaria os
demais arquivos de teste sem backend caso a reinicialização falhasse. O AC é disjuntivo
("indisponibilidade **ou** configuração ausente") e as duas causas cobertas aqui atravessam
exatamente o mesmo caminho de código do curto-circuito por credencial ausente
(`VerificadorDisponibilidadeOpenAI.verificar` → `_preparar_agora` → `falhou_preparacao_ia`).
A causa `CAUSA_CREDENCIAL_AUSENTE` em si já tem cobertura de integração no backend, em
`src/backend/testes/test_preflight_ia_api.py`.
