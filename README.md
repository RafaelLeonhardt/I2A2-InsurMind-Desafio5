# I2A2 - InsurMind - Desafio 5 - Central Preventiva — Comunicação Proativa com o Segurado

Este projeto faz parte do curso de inteligência artificial da I2A2 com foco em área de seguros da equipe Segur.AI.

A **Central Preventiva** é uma prova de conceito desenvolvida para o Desafio 5 do programa I2A2. O projeto explora o uso de Inteligência Artificial para transformar a comunicação entre seguradoras e segurados de um modelo reativo para uma abordagem preventiva.

A solução monitora dados meteorológicos de fontes públicas, identifica eventos climáticos relevantes e aplica regras de negócio para encontrar segurados potencialmente afetados. A partir desse contexto, a IA gera orientações personalizadas com medidas preventivas e simula o envio das notificações pelos canais de comunicação configurados.

O objetivo do projeto não é substituir análises técnicas nem confirmar coberturas securitárias, mas demonstrar como agentes inteligentes, automação e IA generativa podem apoiar uma comunicação antecipada, relevante e auditável antes da ocorrência de um possível sinistro.

## Fluxo da solução

1. Coleta de dados em uma fonte pública de informações meteorológicas;
2. Identificação de eventos climáticos relevantes;
3. Aplicação das regras de negócio;
4. Seleção dos segurados potencialmente afetados;
5. Geração de mensagens preventivas personalizadas com IA;
6. Revisão das mensagens e simulação do envio;
7. Consulta aos resultados e às eventuais falhas da simulação.

## Documentação

- [Enunciado e requisitos do Desafio 5](docs/desafio-5.md): contexto, requisitos mínimos, entregáveis e critérios de avaliação do projeto.
- [Registros de Decisões Arquiteturais — ADRs](docs/adr/README.md): decisões técnicas e arquiteturais, seus contextos e suas consequências.
- [Design e mockups da solução](docs/design/README.md): telas de referência e descrição da experiência dos perfis Administrador e Segurado.

## Execução local

Pré-requisitos: Python 3.14.4 gerenciado pelo `uv`, Node.js 22.12.0 ou superior e npm 11.19.0.

Prepare a configuração local sem substituir um `.env` existente:

```bash
cp -n .env.example .env
```

Instale e verifique o backend:

```bash
uv sync --project src/backend --locked
uv run --directory src/backend pytest
uv run --directory src/backend ruff check .
uv run --directory src/backend pyright
```

Instale e verifique o frontend:

```bash
npm ci --prefix src/frontend
npm test --prefix src/frontend -- --run
npm run lint --prefix src/frontend
npm run build --prefix src/frontend
```

Prepare o banco operacional DuckDB. O comando aplica as migrações versionadas pendentes e semeia os dados sintéticos da demonstração; repeti-lo é seguro e apenas relata que os dados já estavam preparados:

```bash
uv run --directory src/backend python -m central_preventiva.composicao.inicializador
```

O arquivo do banco (`var/central_preventiva.duckdb` por padrão) fica fora do controle de versão e é integralmente recriável por esse comando. Conclua a inicialização antes de iniciar o servidor: o DuckDB aceita um único processo escritor.

Em terminais separados, inicie a API e o frontend. Ambos aceitam conexões somente por `127.0.0.1`:

```bash
uv run --directory src/backend python -m central_preventiva.composicao.servidor
npm run dev --prefix src/frontend
```

A saúde mínima fica disponível em `http://127.0.0.1:8000/api/v1/saude` e o contrato OpenAPI em `http://127.0.0.1:8000/openapi.json`. Com o servidor no ar, a Swagger UI interativa fica disponível em `http://127.0.0.1:8000/docs`.

### Contrato OpenAPI e tipos do frontend

O snapshot versionado do contrato (`src/backend/central_preventiva/composicao/openapi.json`) é gerado a partir da aplicação real e comparado ao schema em execução por `test_openapi_sincronizado.py`. Para regenerá-lo após alterar um roteador:

```bash
uv run --directory src/backend python -m central_preventiva.composicao.openapi_export
```

Os tipos TypeScript consumidos pelo cliente HTTP central (`src/frontend/src/api/clienteHttp.ts`) são gerados a partir desse mesmo contrato. **Os dois comandos abaixo exigem o backend em execução em `127.0.0.1:8000`** (`uv run --directory src/backend python -m central_preventiva.composicao.servidor`):

```bash
npm run gerar-tipos-api --prefix src/frontend    # regera src/frontend/src/api/tipos-gerados.ts
npm run verificar-tipos-api --prefix src/frontend # falha se o arquivo versionado divergir do contrato ao vivo
```

## Testes ponta a ponta (Playwright)

Os cenários ponta a ponta ficam em `testes-e2e/` e rodam contra o backend e o frontend reais,
num navegador Chromium de verdade. Nenhuma chamada sai da máquina: INMET e OpenAI são
substituídos por um servidor de dublês local, iniciado pela própria suíte.

Instale as dependências e o navegador uma vez:

```bash
npm ci --prefix testes-e2e
npm run instalar-navegadores --prefix testes-e2e
```

Rode a suíte completa, ou um cenário específico:

```bash
npm test --prefix testes-e2e
npm test --prefix testes-e2e -- cenarios/chuva-intensa.spec.ts
```

Use `npm --prefix`, e não `npx playwright` a partir da raiz: se houver um executável
`playwright` do pacote Python no `PATH`, o `npx` da raiz o escolhe no lugar do Playwright de
`testes-e2e/node_modules` e a descoberta de cenários falha.

A suíte inicia sozinha o servidor de dublês, prepara um banco DuckDB exclusivo
(`var/e2e/central_preventiva.duckdb`, fora do controle de versão), sobe a API em
`127.0.0.1:8000` e o frontend em `127.0.0.1:5151`, e derruba tudo ao final. **Deixe as duas
portas livres antes de rodar**: a suíte recusa iniciar se já houver um servidor de
desenvolvimento nelas, e o banco de desenvolvimento nunca é tocado.

## Evidências da suíte completa

`scripts/gerar_evidencias.py` roda a suíte inteira (backend, frontend e Playwright) num único
comando e organiza os resultados em `docs/evidencias/`: um relatório markdown por cenário/fluxo
E2E, citando `file:line` do(s) teste(s) que o comprovam, mais um índice (`docs/evidencias/README.md`)
com o resumo de cada suíte.

```bash
python3 scripts/gerar_evidencias.py
```

Esse comando único executa exatamente os três comandos abaixo, na ordem, e depois monta os
relatórios — rodá-los manualmente produz o mesmo resultado de teste sem gerar as evidências:

```bash
uv run --directory src/backend pytest
npm test --prefix src/frontend -- --run
npx playwright test --reporter=list,json   # em testes-e2e/, ou: npm test --prefix testes-e2e
```

## Licença

Este projeto está licenciado sob a [Licença MIT](LICENSE).
