# ADR 0012: Adoção de LangChain e LangGraph para agentes

- **Status:** Aceito
- **Data:** 22/08/2026

## Contexto

O fluxo definido no ADR 0003 requer agentes especializados, estado compartilhado, transições condicionais, novas tentativas controladas e integração com um modelo de linguagem. A implementação direta de todas essas capacidades aumentaria o esforço da prova de conceito e criaria mecanismos próprios para composição de mensagens, chamada do modelo, controle do grafo e tratamento das respostas.

É necessário adotar ferramentas compatíveis com o backend em Python que permitam estruturar essas responsabilidades, integrar o modelo de linguagem e manter explícitos os caminhos e limites do fluxo de agentes.

## Decisão

Serão adotados **LangChain** e **LangGraph** como frameworks para a implementação do sistema de agentes.

O LangChain será utilizado para as abstrações e integrações relacionadas ao modelo de linguagem, incluindo mensagens, prompts, respostas estruturadas e ferramentas quando necessárias. O LangGraph será utilizado para representar o estado, os nós, as transições condicionais e os ciclos controlados do fluxo estabelecido no ADR 0003.

O modelo de linguagem será acessado por meio da API da **OpenAI**. A chave de acesso será fornecida pela variável de ambiente `OPENAI_API_KEY` e nunca será incorporada ao código-fonte, à documentação, aos testes, aos logs ou ao histórico do repositório. Um arquivo de exemplo poderá indicar o nome da variável sem conter valor real, conforme as regras de proteção de segredos definidas no ADR 0010.

O nome e os parâmetros do modelo deverão ser configuráveis, evitando que regras de negócio dependam diretamente de um modelo específico. As chamadas ao modelo ficarão encapsuladas em módulos ou serviços próprios, permitindo testes com implementações simuladas e reduzindo o acoplamento do restante da aplicação com os frameworks e o provedor.

## Consequências

### Positivas

- O fluxo de agentes pode ser representado por estados, nós e transições explícitas.
- LangChain reduz o código necessário para integrar prompts, mensagens e respostas do modelo.
- LangGraph oferece suporte aos caminhos condicionais e ciclos limitados definidos para a solução.
- O encapsulamento da integração facilita testes sem chamadas reais à API.
- A configuração externa da chave evita sua inclusão deliberada no código e no repositório.

### Negativas e riscos

- A solução passa a depender das APIs, versões e evolução de LangChain, LangGraph e OpenAI.
- Atualizações dos frameworks podem introduzir incompatibilidades ou exigir alterações no código.
- Chamadas ao modelo dependem de conexão externa, disponibilidade do serviço, limites de uso e saldo da conta.
- Respostas do modelo podem ser variáveis, incorretas ou incompatíveis com os requisitos do fluxo.
- O uso da API pode gerar custos e transmitir ao provedor o conteúdo incluído nas requisições.
- A exposição acidental da chave poderá permitir uso não autorizado da conta associada.

## Medidas de controle

- Fixar versões compatíveis das dependências LangChain, LangGraph e da integração com OpenAI.
- Validar de forma determinística entradas, respostas estruturadas e critérios objetivos do fluxo.
- Definir timeouts, limites de tentativas e tratamento explícito de falhas da API.
- Manter o modelo e seus parâmetros em configuração externa ao código das regras de negócio.
- Utilizar implementações simuladas do modelo nos testes sempre que uma chamada real não for necessária.
- Não enviar dados pessoais reais, credenciais ou outros conteúdos sensíveis ao modelo.
- Manter `OPENAI_API_KEY` somente no ambiente local ou em arquivo de configuração ignorado pelo Git.
- Revogar e substituir imediatamente a chave caso haja suspeita de exposição.
- Registrar métricas de uso e erros sem incluir a chave ou conteúdo sensível nos logs.
