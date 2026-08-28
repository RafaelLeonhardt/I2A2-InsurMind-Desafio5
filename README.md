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

Pré-requisitos: Python 3.14.7 gerenciado pelo `uv`, Node.js 22.12.0 ou superior e npm 11.19.0.

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

Em terminais separados, inicie a API e o frontend. Ambos aceitam conexões somente por `127.0.0.1`:

```bash
uv run --directory src/backend python -m central_preventiva.composicao.servidor
npm run dev --prefix src/frontend
```

A saúde mínima fica disponível em `http://127.0.0.1:8000/api/v1/saude` e o contrato OpenAPI em `http://127.0.0.1:8000/openapi.json`.

## Licença

Este projeto está licenciado sob a [Licença MIT](LICENSE).
