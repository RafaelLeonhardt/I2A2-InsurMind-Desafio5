# ADR 0003: Adoção de Graph Engineering e Loop Engineering

- **Status:** Aceito
- **Data:** 22/08/2026
- **Decisor:** Bruno (desenvolvedor e arquiteto da solução)

## Contexto

O Desafio 5 requer uma solução capaz de consultar dados meteorológicos, identificar eventos relevantes, selecionar os segurados afetados, gerar recomendações preventivas personalizadas e simular o envio das notificações.

Um pipeline estritamente linear dificultaria o encerramento antecipado de execuções sem risco, o tratamento de caminhos condicionais e a recuperação de falhas temporárias. Além disso, mensagens produzidas por um modelo de linguagem podem não respeitar o tom corporativo, não apresentar uma ação clara ou exceder o limite do canal de comunicação.

A arquitetura precisa, portanto, tornar explícitos o estado do processamento, as transições entre etapas e os limites dos ciclos de correção.

## Decisão

A solução será orquestrada em Python com LangGraph, combinando **Graph Engineering**, para modelar o processamento como um grafo orientado a estados, e **Loop Engineering**, para implementar ciclos controlados de resiliência e revisão.

O grafo será composto pelos seguintes nós de responsabilidade única:

1. **Fetcher:** consulta a fonte meteorológica e normaliza a resposta.
2. **Risk & Policy Matcher:** identifica eventos relevantes e aplica as regras de elegibilidade às apólices e aos perfis de segurados.
3. **Copywriter Agent:** gera a recomendação preventiva personalizada.
4. **Critic Agent:** avalia tom, segurança, clareza da ação e restrições do canal.
5. **Notifier Simulator:** registra ou produz a representação da entrega da mensagem aprovada, sem realizar um envio real.

Arestas condicionais controlarão o fluxo. Quando não houver risco relevante ou segurado elegível, a execução será encerrada antes de chamar o modelo de linguagem. Quando houver correspondência, o fluxo seguirá para geração, avaliação e simulação da notificação.

Serão adotados dois ciclos limitados:

- **Resiliência da coleta:** falhas temporárias ou respostas inválidas da API meteorológica poderão provocar novas tentativas controladas antes de a execução ser encerrada com erro.
- **Revisão da mensagem:** uma mensagem reprovada pelo Critic Agent retornará ao Copywriter Agent acompanhada do motivo da reprovação. Serão permitidas, no máximo, três tentativas de geração por mensagem.

Os critérios de aprovação da mensagem serão:

- tom preventivo, objetivo e não alarmista;
- orientação prática e coerente com o evento e a cobertura;
- respeito às restrições do canal, incluindo o limite configurado de caracteres.

Ao atingir o limite de tentativas sem aprovação, a mensagem não será encaminhada ao Notifier Simulator e a ocorrência será registrada para análise.

## Consequências

### Positivas

- O estado e os caminhos condicionais do processamento ficam explícitos e rastreáveis.
- O encerramento antecipado evita chamadas desnecessárias ao modelo de linguagem.
- Nós especializados podem ser testados e evoluídos de forma isolada.
- A revisão iterativa reduz a chance de mensagens inadequadas ou incompatíveis com o canal.
- As tentativas controladas aumentam a tolerância a falhas transitórias de integrações externas.

### Negativas e riscos

- O grafo e seus ciclos aumentam a complexidade de implementação, testes e observabilidade.
- A revisão por outro agente baseado em modelo de linguagem não garante conformidade determinística.
- Ciclos de nova tentativa aumentam latência e consumo de APIs e modelos.
- O estado compartilhado entre os nós exige contratos claros para evitar transições incorretas.
- A adoção de LangGraph cria dependência do framework e de sua evolução.

## Medidas de controle

- Limitar e registrar todas as novas tentativas, sem ciclos infinitos.
- Aplicar validações determinísticas para regras objetivas, como tamanho, campos obrigatórios e elegibilidade.
- Definir timeouts e tratamento explícito para falhas da fonte meteorológica e do modelo de linguagem.
- Não simular o envio de mensagens reprovadas ou produzidas após uma falha não recuperada.
- Manter logs das transições, decisões, reprovações e motivos de encerramento, sem expor dados pessoais ou credenciais.
- Cobrir com testes os caminhos de sucesso, encerramento antecipado, reprovação, esgotamento de tentativas e falha de integração.
