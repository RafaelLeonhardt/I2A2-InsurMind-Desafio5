# ADR 0008: Comunicação entre frontend e backend por API REST

- **Status:** Aceito
- **Data:** 22/08/2026

## Contexto

O frontend definido no ADR 0005 precisa consultar dados, acionar operações e apresentar os resultados produzidos pelo backend em Python definido no ADR 0004. Para evitar acoplamento direto entre as duas aplicações, é necessário estabelecer uma interface de comunicação explícita, independente das implementações internas e acessível durante o desenvolvimento e os testes.

Além de transportar os dados, essa interface precisa oferecer um contrato compreensível e verificável. Sem documentação sincronizada com a implementação, o frontend pode adotar formatos, parâmetros ou comportamentos diferentes daqueles efetivamente fornecidos pelo backend.

## Decisão

Toda comunicação entre o frontend e o backend será realizada por meio de uma **API HTTP REST**, definida e fornecida pelo backend.

A API utilizará recursos e métodos HTTP coerentes com as operações expostas, códigos de status apropriados e representações em JSON. Os formatos de requisição, resposta e erro deverão ser explícitos e consistentes.

O contrato da API será publicado no formato **OpenAPI** e será considerado a referência para a integração com o frontend. A documentação interativa será disponibilizada pelo backend por meio do **Swagger UI**, permitindo consultar ao vivo as operações, os parâmetros, os esquemas e as respostas previstas e, quando permitido pelo ambiente, executar requisições de teste.

Alterações incompatíveis no contrato deverão ser tratadas de forma deliberada, com atualização da especificação, comunicação ao frontend e adoção de versionamento quando necessário.

## Consequências

### Positivas

- Frontend e backend ficam desacoplados por um contrato de comunicação explícito.
- A especificação OpenAPI fornece uma referência legível por pessoas e ferramentas.
- O Swagger UI facilita a descoberta, a consulta e o teste manual dos endpoints disponíveis.
- O contrato documentado favorece testes de integração e eventual geração de tipos ou clientes.
- Outros consumidores poderão integrar-se à API sem depender da implementação interna do backend.

### Negativas e riscos

- O time precisa manter a implementação e a especificação OpenAPI sincronizadas.
- Mudanças incompatíveis podem interromper o frontend ou outros consumidores da API.
- A comunicação HTTP acrescenta tratamento de latência, indisponibilidade, serialização e falhas de rede.
- Uma documentação interativa exposta sem controle pode revelar operações ou modelos que não deveriam ser públicos.
- O estilo REST pode não ser o mais eficiente para todos os tipos de interação futura, como atualizações em tempo real.

## Medidas de controle

- Gerar ou validar a especificação OpenAPI a partir dos contratos efetivamente implementados pelo backend.
- Definir esquemas consistentes para dados, paginação, validação e respostas de erro.
- Cobrir os endpoints e os principais fluxos de integração com testes automatizados.
- Configurar CORS apenas para as origens necessárias em cada ambiente.
- Aplicar autenticação, autorização e proteção de dados quando os endpoints ou dados assim exigirem.
- Restringir ou desabilitar o Swagger UI em ambientes nos quais sua exposição represente risco.
- Atualizar a documentação no mesmo fluxo de alteração do código da API.
