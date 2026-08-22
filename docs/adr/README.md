# Registros de Decisões Arquiteturais

Este diretório reúne os Registros de Decisões Arquiteturais (Architecture Decision Records — ADRs) do projeto. Cada ADR documenta uma decisão relevante, seu contexto e suas consequências, formando um histórico que ajuda o time a compreender como e por que a solução evoluiu.

## Índice

| ADR | Título | Status | Data |
| --- | --- | --- | --- |
| [0001](0001-adocao-de-registros-de-decisoes-arquiteturais.md) | Adoção de Registros de Decisões Arquiteturais | Aceito | 22/08/2026 |
| [0002](0002-uso-de-ia-para-assistencia-ao-desenvolvimento.md) | Uso de IA para assistência ao desenvolvimento | Aceito | 22/08/2026 |
| [0003](0003-adocao-de-graph-engineering-e-loop-engineering.md) | Adoção de Graph Engineering e Loop Engineering | Aceito | 22/08/2026 |
| [0004](0004-uso-de-python-no-backend.md) | Uso de Python no backend | Aceito | 22/08/2026 |
| [0005](0005-uso-de-react-vite-e-typescript-no-frontend.md) | Uso de React, Vite e TypeScript no frontend | Aceito | 22/08/2026 |
| [0006](0006-uso-de-duckdb-como-banco-de-dados.md) | Uso de DuckDB como banco de dados | Aceito | 22/08/2026 |
| [0007](0007-uso-do-codex-para-assistencia-ao-desenvolvimento.md) | Uso do Codex para assistência ao desenvolvimento | Aceito | 22/08/2026 |
| [0008](0008-comunicacao-entre-frontend-e-backend-por-api-rest.md) | Comunicação entre frontend e backend por API REST | Aceito | 22/08/2026 |
| [0009](0009-execucao-local-sem-autenticacao-e-autorizacao.md) | Execução local sem autenticação e autorização | Aceito | 22/08/2026 |
| [0010](0010-organizacao-modular-do-codigo-fonte.md) | Organização modular do código-fonte | Aceito | 22/08/2026 |
| [0011](0011-adocao-do-portugues-brasileiro-na-documentacao-e-no-codigo.md) | Adoção do português brasileiro na documentação e no código | Aceito | 22/08/2026 |
| [0012](0012-adocao-de-langchain-e-langgraph-para-agentes.md) | Adoção de LangChain e LangGraph para agentes | Aceito | 22/08/2026 |

## Convenções

- Os arquivos devem seguir o padrão `NNNN-titulo-em-kebab-case.md`.
- A numeração deve ser sequencial e nunca reutilizada.
- Cada ADR deve registrar, no mínimo, título, status, data, contexto, decisão e consequências.
- Um ADR aceito não deve ser alterado para representar uma nova decisão. Mudanças posteriores devem ser registradas em um novo ADR que substitua o anterior.
- O índice deste arquivo deve ser atualizado sempre que um ADR for adicionado.

## Status possíveis

- **Proposto:** decisão em discussão.
- **Aceito:** decisão aprovada e vigente.
- **Rejeitado:** decisão avaliada e não adotada.
- **Substituído:** decisão que deixou de vigorar em favor de outro ADR.
- **Obsoleto:** decisão que não se aplica mais ao projeto.
