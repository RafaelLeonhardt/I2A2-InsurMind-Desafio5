# ADR 0009: Execução local sem autenticação e autorização

- **Status:** Aceito
- **Data:** 22/08/2026

## Contexto

A solução será construída como uma prova de conceito destinada exclusivamente a demonstrações em ambiente local. Nesta etapa, o objetivo é validar o fluxo funcional, a integração entre frontend e backend, o processamento dos dados e a geração simulada de notificações.

A implementação de identidade, autenticação, autorização, gestão de sessões, recuperação de acesso e perfis de permissão aumentaria o esforço e a complexidade da prova de conceito sem contribuir diretamente para a validação pretendida. Como compensação, a solução não poderá ser tratada como um sistema pronto para uso compartilhado ou para exposição em rede.

## Decisão

A prova de conceito não implementará mecanismos de autenticação nem de autorização de acesso.

Todos os recursos da interface e todos os endpoints da API REST definida no ADR 0008 estarão disponíveis sem identificação do usuário ou verificação de permissões. A solução completa, incluindo frontend, backend, banco de dados e Swagger UI, será executada apenas localmente para fins de demonstração.

Os serviços deverão escutar somente em interfaces locais sempre que a tecnologia utilizada permitir. Não serão realizados implantação pública, disponibilização em rede compartilhada nem uso com dados pessoais reais, credenciais reais ou informações sigilosas.

Esta decisão é válida exclusivamente para a prova de conceito. Qualquer mudança que permita acesso por outros dispositivos, usuários ou ambientes deverá ser precedida pela definição e implementação de requisitos de autenticação, autorização, segurança e proteção de dados.

## Consequências

### Positivas

- O time concentra o esforço nos fluxos funcionais que a prova de conceito precisa demonstrar.
- A configuração e a execução local permanecem simples.
- Não é necessário administrar usuários, credenciais, sessões ou provedores de identidade.
- O tempo de implementação e a quantidade de componentes da solução são reduzidos.

### Negativas e riscos

- Qualquer processo ou pessoa com acesso aos serviços locais poderá utilizar todas as funcionalidades disponíveis.
- A solução não estará preparada para implantação pública ou acesso por múltiplos usuários.
- Uma configuração de rede incorreta poderá expor endpoints sem proteção.
- A inclusão posterior de autenticação e autorização poderá exigir alterações nos contratos da API, no frontend e nos testes.
- A ausência desses mecanismos impede que a prova de conceito valide perfis, permissões e segregação de acesso.

## Medidas de controle

- Configurar frontend, backend, banco de dados e ferramentas auxiliares para execução exclusivamente local.
- Vincular os serviços a `localhost` ou à interface de loopback, evitando exposição em todas as interfaces de rede.
- Utilizar somente dados fictícios, anonimizados ou preparados especificamente para demonstração.
- Não armazenar credenciais reais, segredos ou dados pessoais reais no código, no banco ou nos arquivos de configuração.
- Indicar na documentação da execução que a solução não possui controle de acesso e não deve ser publicada.
- Reavaliar esta ADR e criar uma nova decisão arquitetural antes de qualquer implantação compartilhada, remota ou produtiva.
