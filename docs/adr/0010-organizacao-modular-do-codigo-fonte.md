# ADR 0010: Organização modular do código-fonte

- **Status:** Aceito
- **Data:** 22/08/2026

## Contexto

O projeto reúne um backend em Python, um frontend em React, Vite e TypeScript, integrações externas, acesso a dados e um fluxo de agentes. Mesmo sendo uma prova de conceito, uma estrutura pouco clara aumentaria o acoplamento, dificultaria a localização de responsabilidades e tornaria a solução mais difícil de compreender, testar e apresentar.

O código também poderá consumir serviços externos que exigem chaves de API ou outras credenciais. Esses valores não podem ser incorporados ao código-fonte, à documentação, aos dados de exemplo nem ao histórico do repositório.

## Decisão

O código-fonte será organizado de forma modular, com separação principal entre backend e frontend no diretório `src`:

```text
src/
├── backend/
└── frontend/
```

O conteúdo de `src/backend` será organizado em módulos e serviços com responsabilidades claras, separando, quando aplicável, API HTTP, regras de negócio, agentes, integrações externas, persistência, modelos e configurações.

O conteúdo de `src/frontend` será organizado em componentes, páginas, serviços de acesso à API, tipos e recursos compartilhados. Componentes visuais não deverão incorporar diretamente regras de integração ou detalhes internos do backend.

A organização interna deverá priorizar a compreensão por pessoas humanas. Nomes de arquivos, módulos, componentes, serviços, funções e variáveis deverão comunicar sua finalidade. Cada unidade deverá possuir responsabilidade coesa, interfaces explícitas e dependências tão simples quanto possível. Abstrações e subdivisões somente serão introduzidas quando tornarem o código mais claro ou reduzirem acoplamento e repetição relevantes.

Chaves de API, credenciais, tokens e demais segredos serão fornecidos ao processo por configuração externa, como variáveis de ambiente ou arquivos locais não versionados. O repositório poderá conter um arquivo de exemplo com os nomes das configurações necessárias, mas nunca com valores reais.

## Consequências

### Positivas

- A separação entre frontend e backend fica explícita e previsível.
- Responsabilidades menores e coesas facilitam leitura, testes e manutenção.
- Novos participantes conseguem localizar componentes e serviços com mais rapidez.
- Integrações e implementações internas podem evoluir com menor impacto sobre outras partes da solução.
- Segredos permanecem separados do código e do histórico do repositório.

### Negativas e riscos

- A modularização acrescenta diretórios, arquivos e contratos internos à prova de conceito.
- Divisões excessivas podem fragmentar o código e dificultar a navegação.
- A separação incorreta de responsabilidades pode criar dependências circulares ou camadas artificiais.
- Configurações externas exigem documentação e preparação do ambiente antes da execução.
- Arquivos ignorados pelo Git não impedem, sozinhos, que um segredo seja incluído acidentalmente em outro arquivo versionado.

## Medidas de controle

- Manter todo o código da aplicação sob `src/backend` ou `src/frontend`, conforme sua responsabilidade.
- Agrupar código por responsabilidade funcional e evitar arquivos genéricos que acumulem comportamentos não relacionados.
- Manter contratos explícitos entre módulos e evitar dependências diretas entre detalhes internos do frontend e do backend.
- Documentar as variáveis de ambiente necessárias em arquivo de exemplo sem valores sensíveis.
- Incluir arquivos locais de configuração e segredos nas regras do `.gitignore`.
- Não registrar segredos em código, testes, documentação, logs, dados de demonstração ou histórico do Git.
- Revogar e substituir imediatamente qualquer credencial que seja exposta acidentalmente.
- Revisar periodicamente a estrutura e simplificá-la quando a modularização deixar de favorecer o entendimento humano.
