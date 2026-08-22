# ADR 0007: Uso do Codex para assistência ao desenvolvimento

- **Status:** Aceito
- **Data:** 22/08/2026

## Contexto

O ADR 0002 estabelece que o projeto será desenvolvido com assistência de inteligência artificial, sob direção, revisão e responsabilidade do time. Para tornar essa prática reproduzível e registrar a ferramenta adotada, é necessário definir qual solução apoiará as atividades de implementação no repositório.

O projeto demanda assistência para compreender o contexto existente, criar e modificar arquivos, propor implementações, executar verificações e manter a documentação coerente com o código.

## Decisão

O **Codex** será a ferramenta principal de inteligência artificial para assistência ao desenvolvimento do projeto.

O Codex poderá ser utilizado para explorar o repositório, gerar e alterar código, criar testes e documentação, investigar falhas e executar verificações no ambiente de desenvolvimento. Toda atuação deverá partir de instruções e contexto fornecidos pelo time e permanecer limitada ao escopo autorizado para cada tarefa.

As alterações produzidas pelo Codex deverão ser revisadas e validadas antes de serem aceitas. O uso da ferramenta não transfere a autoria das decisões arquiteturais nem a responsabilidade pelo software: ambas permanecem com o time. Esta ADR especializa a decisão geral registrada no ADR 0002 e não substitui suas medidas de controle.

## Consequências

### Positivas

- A ferramenta pode acelerar implementação, testes, documentação e investigação de problemas.
- A capacidade de trabalhar com o contexto do repositório favorece alterações coerentes entre diferentes arquivos.
- A execução de verificações no ambiente ajuda a produzir resultados acompanhados de evidências.
- A ferramenta adotada fica explícita para participantes e avaliadores do projeto.

### Negativas e riscos

- As respostas podem conter erros, pressupostos incorretos, vulnerabilidades ou mudanças além do necessário.
- A qualidade do resultado depende do contexto fornecido e da revisão realizada pelo time.
- O projeto pode desenvolver dependência do comportamento, da disponibilidade e da evolução da ferramenta.
- O envio indevido de código, credenciais ou dados sensíveis pode criar riscos de segurança e privacidade.

## Medidas de controle

- Revisar as alterações geradas e executar testes, análise estática e builds aplicáveis antes da aceitação.
- Fornecer tarefas com escopo, requisitos e critérios de aceite claros.
- Não incluir segredos, credenciais, dados pessoais reais ou outros conteúdos sensíveis nas instruções.
- Manter as decisões arquiteturais relevantes registradas em ADRs, independentemente de quem ou do que as propôs.
- Garantir que o time compreenda, consiga explicar e assuma responsabilidade pelo resultado incorporado ao projeto.
