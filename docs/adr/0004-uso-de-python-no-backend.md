# ADR 0004: Uso de Python no backend

- **Status:** Aceito
- **Data:** 22/08/2026

## Contexto

O backend precisa integrar fontes meteorológicas, aplicar regras de negócio, consultar dados de apólices e segurados e orquestrar o fluxo de agentes definido para a solução. Por se tratar de uma prova de conceito, o time também precisa desenvolver e validar essas capacidades com rapidez, sem introduzir complexidade operacional desnecessária.

Python possui um ecossistema consolidado para integração de APIs, processamento de dados, inteligência artificial e construção de serviços web. Além disso, sua adoção é coerente com o uso de LangGraph estabelecido no ADR 0003.

## Decisão

Python será a linguagem principal do backend da aplicação.

As APIs, regras de negócio, integrações, acesso a dados e a orquestração do fluxo de agentes serão implementados em Python. Bibliotecas e frameworks específicos poderão ser escolhidos conforme a necessidade, desde que sejam compatíveis com a versão de Python definida pelo projeto e não comprometam a simplicidade da prova de conceito.

O frontend não será incluído nesta decisão e terá sua tecnologia registrada em ADR própria.

## Consequências

### Positivas

- A solução aproveita um amplo ecossistema de bibliotecas para IA, dados, APIs e testes.
- A integração com LangGraph e outros componentes do fluxo de agentes é direta.
- A linguagem favorece prototipação rápida e código conciso para a prova de conceito.
- Backend, processamento de dados e orquestração podem compartilhar modelos e utilitários.

### Negativas e riscos

- O desempenho pode ser inferior ao de linguagens compiladas em tarefas intensivas de CPU.
- Dependências e ambientes virtuais exigem controle para garantir execuções reproduzíveis.
- A flexibilidade da linguagem pode permitir erros de tipos detectados apenas em execução.
- O uso de operações síncronas inadequadas pode limitar a concorrência das integrações externas.

## Medidas de controle

- Fixar e documentar a versão de Python utilizada pelo projeto.
- Manter as dependências declaradas e com versões controladas.
- Adotar anotações de tipos, validação estática e testes automatizados nas partes relevantes.
- Separar regras de negócio, integrações e persistência para facilitar testes e futuras substituições.
