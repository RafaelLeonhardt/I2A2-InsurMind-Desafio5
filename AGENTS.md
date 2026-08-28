<!-- bmad:context -->
<!-- Verified 2026-08-25 against 8fbaede. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## Central Preventiva

Prova de conceito educacional para comunicação preventiva com segurados a partir de eventos meteorológicos. A implementação planejada usa Python, LangChain, LangGraph e DuckDB no backend, com React, Vite e TypeScript no frontend. Requisitos, decisões arquiteturais e referências de design vivem em `docs/`.

## Policy

- Use somente dados sintéticos ou anonimizados; nunca inclua dados pessoais reais em código, testes, prompts, logs, banco ou documentação.
- Mantenha o MVP funcional exclusivamente local e restrito à interface de loopback. Antes de qualquer acesso compartilhado ou remoto, crie uma nova decisão arquitetural e defina e implemente autenticação, autorização, segurança e proteção de dados.
- Use a chave real da OpenAI somente como `OPENAI_API_KEY` em um arquivo `.env` local ignorado pelo Git. Nunca exponha seu valor em código, testes, documentação, prompts, comandos ou logs; revogue e substitua a chave imediatamente em caso de exposição ou suspeita.
- Trate toda alteração gerada por IA como não validada até que uma pessoa a revise e as verificações proporcionais ao risco sejam executadas.
- Não reescreva um ADR aceito para mudar uma decisão. Crie um novo ADR, indique o registro substituído e atualize `docs/adr/README.md`.

## Where things are

- Objetivo, escopo mínimo e entregáveis: `docs/desafio-5.md`
- Decisões arquiteturais vigentes: `docs/adr/README.md` e os ADRs nele indexados
- Regras detalhadas de interface: `.cursor/rules/central-preventiva-design-ux.mdc`
- Mockups aprovados: `docs/design/images/`; descrição dos fluxos: `docs/design/README.md`
- `docs/design/prototype/` é somente referência navegável de design. Não o trate como implementação, estrutura ou configuração do MVP.
- Coloque a implementação final em `src/backend/` e `src/frontend/`.

## Running and verifying

- TODO: o MVP ainda não possui manifestos nem comandos executáveis na raiz. Não invente comandos nem use os comandos do protótipo para validar a aplicação final; registre comandos reproduzíveis quando o scaffold for criado.

## Conventions that differ from defaults

- Escreva documentação, identificadores próprios, mensagens, descrições OpenAPI e logs em português brasileiro. Preserve em inglês somente nomes externos, termos técnicos consolidados e contratos que não podem ser traduzidos.
- Documente em português brasileiro todas as classes e todos os métodos públicos, usando docstrings em Python e TSDoc/JSDoc em TypeScript.
- Implemente todo o frontend final em TypeScript; não copie a escolha de JSX/JavaScript do protótipo.
- Mantenha regras objetivas, elegibilidade e limites de canal determinísticos. Restrinja o modelo de linguagem à geração e avaliação de conteúdo dentro do fluxo definido nos ADRs 0003 e 0012.
- Exponha a integração entre frontend e backend somente pela API REST/JSON cujo contrato OpenAPI acompanha a implementação.

<!-- /bmad:context -->
