# ADR 0011: Adoção do português brasileiro na documentação e no código

- **Status:** Aceito
- **Data:** 22/08/2026

## Contexto

O projeto será desenvolvido, apresentado e mantido por uma equipe cujo idioma de trabalho é o português do Brasil. O uso inconsistente de português e inglês em documentos, nomes de módulos e identificadores do código pode dificultar a leitura, aumentar a carga cognitiva e criar diferentes nomes para o mesmo conceito de negócio.

Além disso, classes e métodos públicos representam pontos de interação entre partes da solução. Apenas seus nomes e assinaturas podem não comunicar suficientemente seu propósito, suas responsabilidades e as condições relevantes de uso.

## Decisão

O **português do Brasil** será o idioma padrão de toda a documentação e de todas as informações produzidas pelo código do projeto.

Serão escritos em português brasileiro:

- documentos, ADRs, instruções de execução e comentários;
- nomes de módulos, pacotes e arquivos próprios da aplicação;
- nomes de classes, métodos, funções, parâmetros e variáveis;
- mensagens exibidas na interface, mensagens de validação e erros definidos pela aplicação;
- descrições da API, dos esquemas OpenAPI e dos registros de log próprios do projeto.

Os identificadores deverão ser claros, descritivos e coerentes com o vocabulário do domínio de seguros e monitoramento meteorológico. Serão mantidas as convenções de escrita de cada linguagem, como `snake_case` em Python e `camelCase` ou `PascalCase` em TypeScript. Caracteres acentuados serão evitados em identificadores técnicos para preservar a compatibilidade entre ferramentas, sem alterar o idioma dos termos utilizados.

Toda classe e todo método público deverão possuir documentação explicativa em português brasileiro. Em Python, essa documentação será registrada por meio de docstrings. Em TypeScript, será utilizado comentário de documentação compatível com TSDoc/JSDoc. A documentação deverá explicar, no mínimo, o propósito da classe ou do método e, quando não forem evidentes, seus parâmetros, retorno, efeitos colaterais, exceções e condições de uso.

Termos técnicos consolidados, nomes de produtos e tecnologias poderão permanecer em seu idioma original, como Python, React, TypeScript, DuckDB, OpenAPI e Swagger UI. Também ficam excetuados identificadores exigidos por linguagens, bibliotecas, frameworks, protocolos, formatos de dados e APIs externas. Nesses casos, a tradução não deverá quebrar contratos ou contrariar convenções obrigatórias.

## Consequências

### Positivas

- O código e a documentação ficam mais acessíveis ao público principal do projeto.
- Conceitos de negócio podem utilizar o mesmo vocabulário em requisitos, interface, API e implementação.
- A documentação de classes e métodos públicos facilita entendimento, uso, revisão e manutenção.
- A padronização reduz a mistura arbitrária de idiomas e nomes ambíguos.

### Negativas e riscos

- A integração com bibliotecas e APIs em inglês produzirá pontos inevitáveis de mistura de idiomas.
- Participantes que não dominam português terão maior dificuldade para colaborar com o projeto.
- Traduções literais de termos técnicos podem gerar nomes pouco naturais ou diferentes da terminologia consolidada.
- A documentação obrigatória pode ficar desatualizada se não for alterada junto com o código.
- Ferramentas e exemplos da comunidade geralmente usam identificadores em inglês, exigindo adaptação ao padrão do projeto.

## Medidas de controle

- Manter um vocabulário consistente para os principais conceitos do domínio.
- Revisar nomes e textos durante a revisão das alterações de código.
- Atualizar a documentação de classes e métodos públicos sempre que seu comportamento ou contrato mudar.
- Evitar comentários que apenas repitam o código; a documentação deve explicar propósito, contrato ou decisões relevantes.
- Preservar nomes externos quando forem parte de um contrato, explicando-os em português quando necessário.
- Configurar ferramentas de documentação e análise estática para verificar docstrings ou comentários de APIs públicas quando isso for viável para o projeto.
