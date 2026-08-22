# Desafio 5 — Ferramenta Inteligente para Comunicação Proativa com o Segurado

> Conteúdo extraído de `docs/Desafios.pdf`, páginas impressas 6 e 16–19.

## Objetivo

Desenvolver uma solução baseada em Inteligência Artificial capaz de realizar comunicação proativa com segurados a partir da análise de eventos externos.

O objetivo é aplicar os conceitos estudados sobre agentes inteligentes, automação, integração com APIs e IA Generativa para criar um sistema capaz de identificar situações de risco e gerar comunicações relevantes antes que um sinistro ocorra.

Mais importante do que desenvolver uma aplicação completa é demonstrar como agentes inteligentes podem ser utilizados para agregar valor ao relacionamento entre seguradoras e segurados.

## Contexto

Grande parte das interações entre seguradoras e clientes acontece apenas após a ocorrência de um sinistro. A Inteligência Artificial permite transformar esse modelo reativo em uma abordagem preventiva, monitorando eventos externos e enviando orientações personalizadas antes que um problema aconteça.

Neste desafio, os grupos atuarão como uma equipe responsável por desenvolver um sistema capaz de monitorar condições meteorológicas e gerar comunicações automáticas para segurados.

Exemplos:

- Alerta de chuva intensa para clientes com seguro residencial;
- Alerta de granizo para segurados com seguro automóvel;
- Aviso de ventos fortes para regiões costeiras;
- Recomendações preventivas para minimizar possíveis danos.

## O que deverá ser desenvolvido

Cada grupo deverá desenvolver um protótipo funcional (MVP) capaz de monitorar eventos externos e gerar mensagens personalizadas para diferentes perfis de segurados.

A solução deverá contemplar, no mínimo, as seguintes etapas:

1. Coleta de informações em uma fonte externa de dados meteorológicos;
2. Identificação de eventos relevantes;
3. Aplicação de regras de negócio;
4. Geração automática das mensagens;
5. Simulação do envio das notificações.

Não é necessário realizar o envio real de SMS, e-mails ou notificações push. A simulação do processo é suficiente para atender aos objetivos do desafio.

## Requisitos mínimos

A solução deverá:

- Consumir dados provenientes de pelo menos uma API pública de informações meteorológicas;
- Identificar automaticamente eventos climáticos relevantes;
- Aplicar regras de decisão para determinar quais segurados devem receber notificações;
- Gerar mensagens personalizadas utilizando Inteligência Artificial ou modelos de linguagem;
- Simular o envio das notificações;
- Permitir demonstrar o fluxo completo da solução, desde a obtenção dos dados até a geração da comunicação.

## Fontes de dados sugeridas

Os grupos poderão utilizar qualquer fonte pública de dados meteorológicos. Algumas opções são:

- INMET (Instituto Nacional de Meteorologia);
- OpenWeatherMap;
- NOAA (National Oceanic and Atmospheric Administration);
- Copernicus Climate Data Store.

Outras fontes públicas poderão ser utilizadas, desde que devidamente documentadas.

## Tecnologias sugeridas

Os grupos poderão utilizar livremente as tecnologias apresentadas durante o curso, entre elas:

- Frameworks para construção de agentes inteligentes;
- APIs de modelos de linguagem, como OpenAI, Anthropic, Gemini ou equivalentes;
- Ferramentas de automação de fluxo;
- Bancos de dados;
- Frameworks Python;
- Plataformas Low-Code ou No-Code.

## Boas práticas recomendadas

Sempre que possível:

- Separar claramente as etapas de coleta, processamento, decisão e comunicação;
- Utilizar agentes especializados para diferentes responsabilidades;
- Documentar o fluxo da solução;
- Explicar como as regras de negócio foram definidas;
- Demonstrar diferentes tipos de mensagens para diferentes cenários;
- Organizar o código em módulos;
- Ocultar chaves de API e credenciais.

Essas práticas não são obrigatórias, mas agregam qualidade técnica ao projeto.

## Entregáveis

Cada grupo deverá entregar:

- Relatório técnico em formato PDF contendo:
  - Arquitetura da solução;
  - Descrição dos agentes desenvolvidos, quando aplicável;
  - Tecnologias utilizadas;
  - Fluxo de processamento;
  - Exemplos das mensagens geradas.
- Arquivo ZIP contendo todo o código-fonte;
- Opcionalmente, o link para o repositório público no GitHub.

## Critérios gerais de avaliação

Os trabalhos serão avaliados segundo os seguintes critérios, quando aplicáveis:

| Critério                   |    Peso  |
| :------------------------- | -------: |
| Funcionamento              |     20%  |
| Qualidade técnica          |     15%  |
| Organização do código      |     15%  |
| Documentação               |     10%  |
| Criatividade               |     10%  |
| Uso correto de IA          |     30%  |
| **Total**                  | **100%** |

## Critérios específicos de avaliação

Além dos critérios gerais, serão observados:

- Correta integração com fontes externas de dados;
- Qualidade da arquitetura da solução;
- Clareza das regras de negócio implementadas;
- Qualidade das mensagens produzidas;
- Organização da documentação;
- Criatividade na solução proposta.

## O que não esperamos

O objetivo é o aprendizado. Assim, não são esperados:

- Integração com sistemas reais de seguradoras;
- Envio efetivo de SMS, e-mails ou notificações push;
- Cobertura de todos os eventos climáticos possíveis;
- Soluções comerciais prontas para produção.

Um protótipo funcional, capaz de demonstrar claramente o fluxo de decisão e geração das mensagens, possui maior valor didático do que uma solução excessivamente complexa.

## Considera-se uma entrega completa quando

- [ ] A solução consulta uma fonte externa de dados meteorológicos;
- [ ] As regras de negócio são aplicadas corretamente;
- [ ] As mensagens são geradas automaticamente;
- [ ] O fluxo completo da solução pode ser demonstrado;
- [ ] O relatório descreve claramente a arquitetura implementada;
- [ ] O código-fonte foi entregue.

## Prazo de entrega

**Data-limite: 13/09/2026 às 23h59.**

Caso haja alterações no cronograma do curso, uma nova data será comunicada aos grupos.

Os grupos que desejarem apresentar sua solução durante o encontro de revisão deverão manifestar interesse até essa mesma data.

## Observações importantes

- O repositório do GitHub deverá possuir acesso público;
- O arquivo `README.md` deverá conter instruções para instalação e execução da solução;
- O `README.md` deverá informar que o projeto está licenciado sob a licença MIT;
- Esta atividade é obrigatória e constitui requisito para a continuidade do grupo no curso.

## Dica de arquitetura

O documento recomenda modelar a solução como um fluxo composto por agentes especializados, por exemplo:

- Um agente responsável pela obtenção dos dados meteorológicos;
- Um agente para análise dos eventos climáticos;
- Um agente para aplicação das regras de negócio;
- Um agente para geração das mensagens.

Embora uma arquitetura multiagente não seja obrigatória, ela permite aplicar diversos conceitos apresentados ao longo do curso e facilita a evolução da solução.
