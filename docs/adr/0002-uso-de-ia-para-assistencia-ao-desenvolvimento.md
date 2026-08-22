# ADR 0002: Uso de IA para assistência ao desenvolvimento

- **Status:** Aceito
- **Data:** 22/08/2026

## Contexto

O projeto tem caráter educacional e busca aplicar inteligência artificial tanto na solução desenvolvida quanto no processo de construção do software. O time deseja utilizar ferramentas de IA para acelerar a implementação, explorar alternativas e apoiar atividades como geração de código, testes, documentação, revisão e correção de problemas.

O uso de IA não elimina a necessidade de direção técnica, validação humana e responsabilidade coletiva sobre o resultado entregue.

## Decisão

Todo o código do projeto será gerado integralmente por ferramentas de inteligência artificial, guiadas pelo time de desenvolvimento.

O time será responsável por definir requisitos, fornecer contexto, orientar as ferramentas, avaliar as soluções propostas e aprovar as alterações. Nenhum código gerado será considerado correto apenas por ter sido produzido por IA: antes de ser incorporado ao projeto, deverá ser revisado e validado de maneira proporcional ao seu risco, por meio de inspeção, testes e demais verificações aplicáveis.

As decisões técnicas e a responsabilidade pelo produto permanecem com o time de desenvolvimento. Informações sigilosas, dados pessoais, credenciais e outros conteúdos sensíveis não deverão ser fornecidos a ferramentas de IA sem autorização e proteção adequadas.

## Consequências

### Positivas

- O time pode acelerar a criação de implementações, testes e documentação.
- A IA pode propor alternativas e apoiar a exploração de tecnologias pouco conhecidas pelo time.
- O processo produz aprendizado prático sobre desenvolvimento de software assistido por IA.
- A abordagem fica explícita e pode ser considerada na avaliação e na manutenção do projeto.

### Negativas e riscos

- O código gerado pode conter erros, vulnerabilidades, dependências inadequadas ou comportamentos diferentes dos requisitos.
- A qualidade do resultado depende da clareza das orientações e da capacidade do time de revisar e validar as respostas.
- O uso das ferramentas pode introduzir riscos de privacidade, licenciamento, segurança e dependência tecnológica.
- A geração integral por IA pode dificultar a manutenção caso o time não compreenda o código produzido.

## Medidas de controle

- Revisar todas as alterações antes de incorporá-las ao projeto.
- Executar testes automatizados e verificações de qualidade sempre que aplicáveis.
- Manter credenciais e informações sensíveis fora dos comandos e contextos enviados às ferramentas.
- Verificar a necessidade, a licença e a procedência das dependências sugeridas.
- Garantir que ao menos um integrante do time compreenda e consiga explicar cada parte relevante da solução.
- Registrar em novos ADRs as decisões arquiteturais significativas propostas durante o desenvolvimento.
