# História 1.5: Consumir e inspecionar a API real — Specification

## Problem Statement

O frontend já consulta saúde, prontidão, contexto e restauração pela API REST/JSON real (sem fixtures), e o backend já responde em `snake_case`, com `application/problem+json` e `Idempotency-Key` nas mutações. O que falta é a prova formal e verificável desse contrato: geração de OpenAPI que corresponda ao que a API realmente executa, tipos de frontend gerados a partir dele (não duplicados à mão para os recursos novos desta história), Swagger UI acessível só via loopback, uma superfície que comprove essa disponibilidade à pessoa avaliadora, e testes automatizados que fechem essas garantias — hoje nenhuma delas é verificada por teste ou script reproduzível.

## Goals

- [ ] `openapi.json` gerado pela aplicação real corresponde 1:1 aos contratos executados sob `/api/v1`, com título/descrição/operações/campos/erros em português brasileiro
- [ ] Swagger UI e `openapi.json` acessíveis somente via loopback (`127.0.0.1`), com um comando reproduzível documentado no README
- [ ] Um cliente HTTP central no frontend, tipado a partir de `openapi-typescript`, existe e é a única forma de acesso à API para os recursos que esta história adiciona (a superfície de Documentação da API)
- [ ] Verificação automatizada falha se o contrato OpenAPI, os tipos gerados e as chamadas existentes divergirem
- [ ] Nova superfície "Documentação da API" no perfil Administrador mostra carregando/disponível/indisponível com causa e endereço local, sem dado fixo mascarando indisponibilidade real
- [ ] Testes automatizados cobrem contratos de sucesso e erro, CORS restrito à origem local, documentação acessível e sincronização de tipos; comandos registrados no README

## Out of Scope

| Feature | Reason |
| --- | --- |
| Migrar `contexto.ts`, `prontidao.ts`, `dadosSinteticos.ts` para o cliente HTTP central/tipos gerados | Decisão do usuário: escopo desta história é criar o cliente central e os tipos gerados; a migração dos 3 módulos existentes permanece como dívida já registrada em AD-003, revisitável em história futura |
| Autenticação, autorização ou controle de acesso à API | Fora do MVP; a API só aceita loopback, sem múltiplos usuários |
| Publicar a especificação OpenAPI fora da rede local (portal público, versionamento semântico de contrato) | A PoC roda inteiramente local; nenhum consumidor externo existe |
| Novos recursos de negócio (Épico 2+) | Esta história é sobre disciplina de contrato da API já existente, não sobre novas capacidades |
| Client SDK tipado para consumo por terceiros | Só o frontend da própria PoC consome a API |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Forma da "interface técnica" de disponibilidade da documentação | Nova superfície dedicada "Documentação da API", visível só no perfil Administrador, com link para abrir o Swagger UI (`/docs`) numa nova aba | Decisão do usuário: tela nova, não indicador embutido em superfície existente | y |
| Escopo do cliente HTTP central e tipos gerados | Criar o cliente central e os tipos via `openapi-typescript` agora; usá-los só para o recurso que esta história adiciona (verificação de disponibilidade da documentação); não migrar os 3 módulos de API já existentes | Decisão do usuário | y |
| Onde a checagem de disponibilidade da documentação aponta | A nova superfície faz `GET` em `http://127.0.0.1:8000/openapi.json` (mesma origem-alvo que `/api/v1`, já liberada no CORS) para decidir disponível/indisponível; não introduz endpoint novo no backend | `/openapi.json` já é servido pelo FastAPI nativamente; não há necessidade de um endpoint próprio em `/api/v1` só para reportar a própria existência do OpenAPI | n — assunção técnica de baixo risco, revisável no Design |
| Verificação automatizada de sincronia contrato↔tipos | Um script reproduzível (documentado no README) gera `openapi.json` e os tipos TypeScript a partir da aplicação real e falha (`git diff --exit-code`) se os artefatos versionados divergirem do que a aplicação gera agora; roda como parte da suíte verificada localmente (não implica CI hospedado, que não existe neste projeto) | Único jeito objetivo de cumprir "incompatibilidades... deverão falhar na verificação automatizada" sem inventar infraestrutura de CI inexistente | n — assunção técnica, revisável no Design |
| Idioma e forma de erro quando a documentação está indisponível | Reusa o mesmo formato de erro tipado por causa/impacto/próxima ação já usado em `contexto.ts`/`prontidao.ts` (não `application/problem+json` do backend, pois a falha é de rede/indisponibilidade do próprio `/openapi.json`, não uma resposta de erro estruturada da API) | Consistência com o padrão de tratamento de erro já estabelecido no frontend (AD-003 herda esse padrão) | n — assunção técnica, revisável no Design |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Contrato OpenAPI fiel e documentado em PT-BR ⭐ MVP

**User Story**: Como pessoa avaliadora da prova de conceito, quero que a especificação OpenAPI gerada pela API corresponda exatamente ao que ela executa, com textos em português brasileiro, para confiar no contrato sem precisar ler o código-fonte.

**Why P1**: Sem isso, nada mais nesta história tem uma fonte de verdade para se apoiar — tipos gerados e testes de sincronia dependem de um `openapi.json` correto primeiro.

**Acceptance Criteria**:

1. The API SHALL expose `GET /openapi.json` gerado pelo FastAPI a partir dos roteadores reais registrados em `criar_aplicacao`.
2. The OpenAPI document SHALL contain `title`, `description`, `summary` de cada operação e descrições de cada campo e resposta de erro em português brasileiro para todo recurso sob `/api/v1`.
3. WHEN a especificação OpenAPI for comparada aos contratos de sucesso e erro efetivamente executados pelos testes de integração existentes (`test_contexto_api.py`, `test_prontidao_api.py`, `test_dados_sinteticos_api.py`) THEN os `status_code`, `response_model` e schemas de erro documentados SHALL corresponder exatamente aos códigos e corpos retornados nesses testes.
4. IF um teste automatizado detectar um endpoint, status code ou schema de erro presente na aplicação em execução mas ausente ou divergente no `openapi.json` gerado THEN a suíte de testes SHALL falhar apontando o endpoint e o campo divergente.

**Independent Test**: Rodar a aplicação, buscar `http://127.0.0.1:8000/openapi.json`, e conferir manualmente que cada operação documentada tem descrição em português e bate com o comportamento observado nos testes de integração existentes.

---

### P1: Swagger UI e OpenAPI acessíveis somente via loopback ⭐ MVP

**User Story**: Como pessoa avaliadora, quero abrir a documentação interativa da API pelo endereço local, para explorar o contrato sem depender de ferramentas externas.

**Why P1**: É o critério de aceitação explícito da história ("deverá conseguir abrir a especificação OpenAPI e a Swagger UI somente via loopback").

**Acceptance Criteria**:

1. WHEN o servidor local for iniciado com a configuração padrão do projeto THEN `GET http://127.0.0.1:8000/docs` SHALL retornar a Swagger UI com status `200`.
2. WHEN o servidor local for iniciado com a configuração padrão do projeto THEN `GET http://127.0.0.1:8000/openapi.json` SHALL retornar o contrato OpenAPI com status `200` e `Content-Type` JSON.
3. The server SHALL recusar bind fora de `127.0.0.1` (já garantido por `Configuracao.validar_host_api`; esta história apenas adiciona um teste que comprova `/docs` e `/openapi.json` respondem no host configurado).
4. The README SHALL documentar o comando e o endereço para abrir a Swagger UI localmente.

**Independent Test**: Com o servidor rodando localmente, abrir `http://127.0.0.1:8000/docs` no navegador e confirmar que a UI carrega e lista os recursos de `/api/v1`.

---

### P1: Cliente HTTP central tipado por `openapi-typescript` ⭐ MVP

**User Story**: Como pessoa desenvolvedora mantendo o frontend, quero um serviço HTTP central que consuma tipos gerados automaticamente do contrato OpenAPI, para que a superfície de Documentação da API não duplique DTOs manualmente e quebre a verificação se o contrato mudar.

**Why P1**: É o mecanismo que a história pede para eliminar duplicação manual de DTOs e detectar incompatibilidade de contrato — pré-requisito técnico para a superfície de Documentação da API (próxima story).

**Acceptance Criteria**:

1. The frontend SHALL declarar `openapi-typescript` como dependência de desenvolvimento e um script `npm run gerar-tipos-api --prefix src/frontend` que lê `http://127.0.0.1:8000/openapi.json` e escreve os tipos gerados em `src/frontend/src/api/tipos-gerados.ts`.
2. The frontend SHALL expor um módulo `src/frontend/src/api/clienteHttp.ts` que constrói requisições a partir dos tipos gerados (via `openapi-fetch` ou equivalente já presente no ecossistema `openapi-typescript`) sem redeclarar manualmente os campos de request/response cobertos pelo contrato.
3. IF o `openapi.json` mudar um campo, tipo ou status code usado pela superfície de Documentação da API e os tipos não forem regenerados THEN a verificação de tipos (`tsc -b`) SHALL falhar.
4. The npm script de verificação (`npm test --prefix src/frontend -- --run` ou um script dedicado documentado no README) SHALL incluir a checagem de que `tipos-gerados.ts` versionado é idêntico ao que a regeneração produz a partir da aplicação em execução.

**Independent Test**: Rodar o script de geração de tipos com o backend no ar, confirmar que `tipos-gerados.ts` é escrito, e que alterar manualmente um campo nesse arquivo e rodar `tsc -b` produz erro de tipo em `clienteHttp.ts`.

---

### P1: Superfície "Documentação da API" sem dado fixo ⭐ MVP

**User Story**: Como pessoa avaliadora usando o perfil Administrador, quero uma tela que confirme se a documentação da API está disponível, com causa e endereço local, para verificar a demonstração sem abrir o terminal.

**Why P1**: É a prova visual, do lado do frontend, de que a inspeção do contrato depende da API real e não de um resultado fixo — fecha o loop de "não deverá substituir o resultado por dados fixos que aparentem processamento real".

**Acceptance Criteria**:

1. The frontend SHALL adicionar `'documentacao-api'` a `Superficie` e a `SUPERFICIES_POR_PERFIL.administrador`, com item de navegação próprio.
2. WHEN a superfície "Documentação da API" for aberta THEN o frontend SHALL exibir estado de carregamento até a primeira resposta de `GET http://127.0.0.1:8000/openapi.json` via o cliente HTTP central.
3. WHEN a requisição responder com sucesso THEN a superfície SHALL exibir estado "Disponível", o endereço local da Swagger UI (`http://127.0.0.1:8000/docs`) e um link que a abre em nova aba.
4. IF a requisição falhar (rede indisponível ou status de erro) THEN a superfície SHALL exibir estado "Indisponível" com a causa (mensagem de erro tipada) e o endereço local esperado, sem exibir dado de exemplo que simule disponibilidade.
5. The component SHALL não usar nenhum valor fixo de exemplo de resposta da API como conteúdo padrão antes da primeira resposta real.

**Independent Test**: Com o backend desligado, abrir a superfície e ver "Indisponível" com causa e endereço; ligar o backend, reabrir a superfície e ver "Disponível" com o link funcional.

---

### P2: Testes de contrato consolidados (CORS, erro, sincronia)

**User Story**: Como pessoa mantenedora, quero uma suíte de testes que valide CORS restrito, formato de erro e sincronia de tipos em um só lugar, para detectar regressão de contrato antes de qualquer PR.

**Why P2**: Reforça e centraliza garantias que os testes de recurso individuais (`test_*_api.py`) já cobrem parcialmente; importante para manutenção contínua, mas não bloqueia a demonstração da P1.

**Acceptance Criteria**:

1. WHEN uma requisição `OPTIONS`/`fetch` partir de uma origem diferente de `http://127.0.0.1:5173` THEN a API SHALL recusar CORS (sem cabeçalho `Access-Control-Allow-Origin` correspondente).
2. WHEN uma requisição partir da origem configurada `http://127.0.0.1:5173` THEN a API SHALL responder com os cabeçalhos CORS liberando `GET`, `POST`, `Accept`, `Content-Type`, `Idempotency-Key`.
3. The test suite SHALL incluir um teste que gera `openapi.json` a partir da aplicação em execução e falha se divergir do arquivo versionado (mesma checagem do frontend, do lado do backend).

**Independent Test**: Rodar a suíte de testes backend e ver os testes de CORS e sincronia de OpenAPI passando isoladamente.

---

## Edge Cases

- IF `openapi-typescript` gerar tipos e o backend estiver fora do ar durante `npm run gerar-tipos-api` THEN o script SHALL falhar com mensagem clara indicando que o backend precisa estar rodando em `127.0.0.1:8000`, sem sobrescrever `tipos-gerados.ts` com conteúdo vazio ou inválido.
- IF a superfície "Documentação da API" for aberta enquanto o backend está inicializando (schema pendente) THEN o estado exibido SHALL ser "Indisponível" com a causa retornada, não travar em carregamento indefinido.
- WHEN o link para a Swagger UI for clicado THEN SHALL abrir em nova aba (`target="_blank"` com `rel="noopener noreferrer"`) sem navegar a própria SPA para fora de sua origem.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| API15-01 | P1: Contrato OpenAPI fiel e documentado em PT-BR | Design | Pending |
| API15-02 | P1: Contrato OpenAPI fiel e documentado em PT-BR | Design | Pending |
| API15-03 | P1: Contrato OpenAPI fiel e documentado em PT-BR | Design | Pending |
| API15-04 | P1: Contrato OpenAPI fiel e documentado em PT-BR | Design | Pending |
| API15-05 | P1: Swagger UI e OpenAPI acessíveis somente via loopback | Design | Pending |
| API15-06 | P1: Swagger UI e OpenAPI acessíveis somente via loopback | Design | Pending |
| API15-07 | P1: Swagger UI e OpenAPI acessíveis somente via loopback | Design | Pending |
| API15-08 | P1: Swagger UI e OpenAPI acessíveis somente via loopback | Design | Pending |
| API15-09 | P1: Cliente HTTP central tipado por openapi-typescript | Design | Pending |
| API15-10 | P1: Cliente HTTP central tipado por openapi-typescript | Design | Pending |
| API15-11 | P1: Cliente HTTP central tipado por openapi-typescript | Design | Pending |
| API15-12 | P1: Cliente HTTP central tipado por openapi-typescript | Design | Pending |
| API15-13 | P1: Superfície "Documentação da API" sem dado fixo | Design | Pending |
| API15-14 | P1: Superfície "Documentação da API" sem dado fixo | Design | Pending |
| API15-15 | P1: Superfície "Documentação da API" sem dado fixo | Design | Pending |
| API15-16 | P1: Superfície "Documentação da API" sem dado fixo | Design | Pending |
| API15-17 | P1: Superfície "Documentação da API" sem dado fixo | Design | Pending |
| API15-18 | P2: Testes de contrato consolidados | Design | Pending |
| API15-19 | P2: Testes de contrato consolidados | Design | Pending |
| API15-20 | P2: Testes de contrato consolidados | Design | Pending |

**ID format:** `API15-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 20 total, 0 mapped to tasks, 20 unmapped ⚠️ (mapeamento ocorre na fase Tasks)

---

## Success Criteria

- [ ] `http://127.0.0.1:8000/docs` e `http://127.0.0.1:8000/openapi.json` abrem com sucesso a partir de um backend recém-iniciado, com textos em português
- [ ] `npm run gerar-tipos-api --prefix src/frontend` produz `tipos-gerados.ts` que `tsc -b` aceita sem erro, e falha de forma clara se o backend estiver fora do ar
- [ ] A superfície "Documentação da API" mostra "Indisponível" com causa quando o backend está desligado e "Disponível" com link funcional quando ligado — sem nenhum dado fixo entre os dois estados
- [ ] `uv run --directory src/backend pytest` cobre CORS restrito, formato de erro `problem+json` e sincronia do `openapi.json`
- [ ] README lista os comandos de geração/verificação de tipos e de abertura da Swagger UI
