# ADR 0001: Adoção de Registros de Decisões Arquiteturais

- **Status:** Aceito
- **Data:** 22/08/2026

## Contexto

O projeto precisa preservar o contexto das decisões técnicas e arquiteturais tomadas ao longo de seu desenvolvimento. Sem um registro estruturado, as razões que levaram a uma escolha podem se perder, dificultando a manutenção, a integração de novos participantes e a avaliação de alternativas no futuro.

## Decisão

Adotaremos Registros de Decisões Arquiteturais (Architecture Decision Records — ADRs) para documentar decisões relevantes do projeto.

Os registros serão mantidos no diretório `docs/adr`, em arquivos Markdown numerados sequencialmente. Cada ADR apresentará, no mínimo, título, status, data, contexto, decisão e consequências. O arquivo `docs/adr/README.md` manterá o índice de todos os registros.

ADRs aceitos serão preservados como documentos históricos. Quando uma decisão vigente mudar, um novo ADR deverá registrar a mudança e indicar qual registro anterior foi substituído.

## Consequências

### Positivas

- As decisões passam a ter justificativas rastreáveis e acessíveis no próprio repositório.
- Novos participantes podem compreender com mais rapidez a evolução da arquitetura.
- Alternativas e mudanças futuras podem ser avaliadas com base no contexto original.
- A documentação evolui junto com o código e pode ser revisada pelo mesmo fluxo de colaboração.

### Negativas

- O time assume o trabalho adicional de criar e manter os registros e seu índice.
- ADRs desatualizados ou pouco claros podem gerar interpretações incorretas.

