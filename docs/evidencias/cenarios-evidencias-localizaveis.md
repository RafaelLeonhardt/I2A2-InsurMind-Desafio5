# Cenário E2E-08 — toda evidência de um cenário executado é localizável, e o contrato bate.

**Arquivo de teste**: `testes-e2e/cenarios/evidencias-localizaveis.spec.ts`
**Requisitos**: E2E-08
**Status**: PASSOU

## Casos de teste (evidência `file:line`)

| Caso | Local | Resultado |
| --- | --- | --- |
| localiza prontidao, evento, supervisao, resultados, comunicado, explicacao e linha do tempo | `testes-e2e/cenarios/evidencias-localizaveis.spec.ts:121` | ✅ passou |
| openapi servido pelo processo corresponde ao contrato versionado e a suite usada | `testes-e2e/cenarios/evidencias-localizaveis.spec.ts:227` | ✅ passou |

## Contexto do cenário

Cópia do comentário de cabeçalho do arquivo de teste — inclui desvios conhecidos, tabelas de rastreabilidade e o que a IA não pode inventar sem editar o teste.

Executa o cenário de chuva intensa até a conclusão e percorre, sobre esse mesmo dado, as
sete evidências que o AC exige: prontidão, evento e decisão, supervisão, resultados,
comunicado, explicação e linha do tempo. Nenhuma delas exige editar arquivo ou banco: tudo
é alcançado por navegação na interface ou por leitura (`GET`) da API pública. A única
mutação do cenário é a restauração inicial, feita pelo endpoint público de demonstração.

Divisão entre interface e API, e por quê: as superfícies de Administrador dos Épicos 2–4
(evento e decisão, supervisão, resultados, linha do tempo) e a gaveta de explicação do
comunicado (`SuperficieExplicacaoComunicado`) existem e são testadas em `vitest`, mas ainda
não estão montadas em `App.tsx` — item aberto já registrado em `.specs/STATE.md`. As
evidências dessas quatro superfícies são alcançadas aqui pela API REST real, que é o mesmo
contrato que elas consomem. O que **está** montado é exercitado na interface real:
Prontidão, Documentação da API, e, no perfil Segurado, alertas (com explicação e linha do
tempo do alerta) e comunicados.

A segunda metade do AC — "OpenAPI/Swagger UI correspondem à API realmente utilizada" —
compara o documento servido pelo processo em execução com o instantâneo versionado em
`composicao/openapi.json` e confirma que toda rota exercitada pela suíte está documentada.
O `pytest` já garante que o instantâneo não diverge do app montado
(`src/backend/testes/test_openapi_sincronizado.py`); aqui a checagem é sobre o processo
realmente no ar, que é o que o AC pede.
