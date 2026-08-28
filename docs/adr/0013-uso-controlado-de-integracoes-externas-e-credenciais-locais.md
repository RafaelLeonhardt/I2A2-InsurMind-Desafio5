# ADR 0013: Uso controlado de integrações externas e credenciais locais

- **Status:** Aceito
- **Data:** 25/08/2026
- **Substitui parcialmente:** ADR 0009 — Execução local sem autenticação e autorização

## Contexto

O ADR 0009 restringiu a prova de conceito ao ambiente local, sem autenticação, autorização, dados pessoais reais, credenciais reais ou informações sigilosas. Essa restrição protege corretamente a aplicação contra exposição e uso compartilhado, mas sua redação também impede duas integrações necessárias às decisões posteriores e ao escopo do desafio:

- consulta a dados meteorológicos públicos reais do INMET;
- acesso à API da OpenAI por meio de uma `OPENAI_API_KEY`, conforme definido no ADR 0012.

É necessário distinguir o acesso à aplicação, que deve permanecer exclusivamente local, das conexões de saída controladas realizadas pelo backend. Também é necessário diferenciar dados meteorológicos públicos de dados pessoais, securitários ou sigilosos.

## Decisão

A prova de conceito continuará integralmente restrita ao ambiente local e à interface de loopback, sem autenticação, autorização, implantação pública ou acesso por rede compartilhada.

O backend poderá realizar somente as conexões externas de saída necessárias ao escopo aprovado:

- consulta a dados meteorológicos públicos reais do INMET;
- chamadas à API da OpenAI para geração e avaliação de conteúdo dentro do fluxo definido nos ADRs 0003 e 0012.

A credencial real da OpenAI será permitida exclusivamente como `OPENAI_API_KEY` no ambiente local ou em arquivo `.env` local ignorado pelo Git. Seu valor não poderá ser incorporado ao código-fonte, banco de dados, testes, documentação, prompts, comandos, logs, artefatos de entrega ou histórico do repositório.

Dados de segurados, apólices, contatos, endereços, comunicações e demais informações securitárias permanecerão exclusivamente sintéticos, anonimizados ou preparados para demonstração. Dados pessoais reais e informações sigilosas continuam proibidos.

Esta decisão substitui somente as partes do ADR 0009 que proíbem, de maneira irrestrita, credenciais reais em configuração local e dados públicos reais necessários às integrações aprovadas. Permanecem vigentes todas as demais restrições do ADR 0009, especialmente a execução em loopback, a ausência de controles de acesso e a proibição de disponibilização remota ou compartilhada.

## Consequências

### Positivas

- Resolve a incompatibilidade entre os ADRs 0009 e 0012 sem enfraquecer a restrição de acesso local.
- Permite demonstrar a integração real exigida com uma fonte meteorológica pública.
- Permite executar os agentes conectados à OpenAI conforme a arquitetura aprovada.
- Mantém explícita a separação entre dados meteorológicos públicos e dados securitários sintéticos.

### Negativas e riscos

- A demonstração passa a depender de conexão com a internet, disponibilidade dos provedores, limites de uso e saldo da conta OpenAI.
- Uma configuração incorreta poderá expor a chave ou permitir que serviços locais escutem em interfaces não autorizadas.
- Conteúdo enviado à OpenAI deixa o ambiente local, ainda que seja limitado a dados meteorológicos públicos e dados securitários sintéticos.
- A indisponibilidade das integrações externas poderá impedir parte do fluxo conectado.

## Medidas de controle

- Vincular frontend, backend, banco e ferramentas auxiliares exclusivamente a `localhost` ou à interface de loopback.
- Manter `.env` e arquivos equivalentes ignorados pelo Git e fornecer somente arquivos de exemplo sem valores reais.
- Validar na inicialização a presença da configuração necessária sem exibir o valor da chave.
- Nunca registrar a chave, cabeçalhos de autenticação ou conteúdo sensível em logs, erros ou respostas da API.
- Enviar à OpenAI apenas os dados mínimos necessários, limitados a dados meteorológicos públicos e dados securitários sintéticos.
- Utilizar implementações simuladas da integração com o modelo nos testes que não precisem validar a chamada real, conforme o ADR 0012.
- Definir timeouts, limites de tentativas e estados terminais explícitos para as integrações externas.
- Revogar e substituir imediatamente a chave em caso de exposição ou suspeita.
- Criar nova decisão arquitetural antes de adicionar outro provedor externo, usar dados pessoais reais ou permitir acesso remoto ou compartilhado.
