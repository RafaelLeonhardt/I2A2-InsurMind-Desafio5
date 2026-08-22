# ADR 0005: Uso de React, Vite e TypeScript no frontend

- **Status:** Aceito
- **Data:** 22/08/2026

## Contexto

O frontend da prova de conceito precisa apresentar o monitoramento de eventos meteorológicos, os segurados e apólices afetados, as recomendações geradas e o resultado das simulações de envio. A interface deve ser construída rapidamente, permanecer organizada à medida que novos fluxos forem adicionados e consumir de forma segura os contratos expostos pelo backend.

É necessário adotar uma combinação de tecnologias com bom suporte a interfaces baseadas em componentes, inicialização simples do ambiente de desenvolvimento e verificação de tipos durante a implementação.

## Decisão

O frontend será desenvolvido com **React**, **Vite** e **TypeScript**.

- React será utilizado para estruturar a interface em componentes reutilizáveis e gerenciar a composição das telas.
- Vite será responsável pela criação do projeto, servidor de desenvolvimento e processo de build.
- TypeScript será utilizado em todo o código da aplicação para explicitar contratos, estados e propriedades dos componentes.

Os tipos usados na comunicação com o backend deverão representar os contratos da API. A escolha de bibliotecas complementares, como roteamento, requisições e testes, será feita somente quando a necessidade estiver demonstrada.

## Consequências

### Positivas

- Componentes reutilizáveis favorecem consistência e evolução incremental da interface.
- Vite oferece uma configuração enxuta e um ciclo rápido de desenvolvimento para a prova de conceito.
- TypeScript permite detectar antecipadamente incompatibilidades entre componentes e contratos da API.
- As tecnologias possuem ecossistemas amplos para testes, acessibilidade e construção de interfaces.

### Negativas e riscos

- O projeto passa a depender de três tecnologias e de suas respectivas atualizações.
- TypeScript e a configuração das ferramentas acrescentam conceitos e arquivos ao frontend.
- Tipos definidos manualmente podem divergir dos contratos reais do backend.
- A ampla oferta de bibliotecas pode levar à inclusão de dependências desnecessárias.

## Medidas de controle

- Fixar e documentar as versões do runtime e das dependências principais.
- Habilitar verificações estritas do TypeScript e executar o build na validação do projeto.
- Centralizar os contratos de comunicação com a API e validar dados recebidos quando necessário.
- Priorizar componentes pequenos e dependências justificadas pelas necessidades da prova de conceito.
