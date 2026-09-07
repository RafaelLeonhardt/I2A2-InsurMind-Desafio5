# História 5.8: Executar e comprovar os cenários ponta a ponta — Specification

## Problem Statement

Depois que os Épicos 1–4 e as Histórias 5.1–5.7 estiverem implementados, nada ainda comprova de ponta a ponta que os cenários completos funcionam juntos, que a acessibilidade WCAG 2.2 AA é respeitada, que o sistema visual de `DESIGN.md`/`EXPERIENCE.md` foi seguido, e que a suíte automatizada cobre os caminhos críticos sem integração externa real. Sem essa história, a pessoa avaliadora não tem como confirmar, de forma reproduzível, que a Central Preventiva funciona como um todo — não é uma história de código novo, é a validação integrada de tudo que já foi construído.

## Goals

- [ ] Cenário de chuva intensa residencial avança da entrada meteorológica até a visualização do comunicado de um segurado elegível, incluindo ao menos um registro não elegível com explicação consultável
- [ ] Cenário de granizo automóvel avança da entrada meteorológica até a visualização do comunicado, preservando regras/apólices/canais/recomendações específicas desse evento (entrada fornecida pelo cenário sintético rotulado — AD-013)
- [ ] Cenários de encerramento antecipado (sem risco, sem elegível) terminam com motivo e evidência determinísticos, sem nenhuma chamada à OpenAI/mensagem/simulação
- [ ] Cenário de regeneração demonstra retorno ao redator, motivos, histórico e limite de 3 tentativas; esgotamento produz exceção e impede a mensagem de entrar na simulação
- [ ] Cenário de contingência do INMET demonstra timeout, tentativas, snapshot informativo e ativação explícita do cenário sintético, com origem sintética visível até o fim do fluxo
- [ ] Cenário de indisponibilidade/configuração ausente da OpenAI termina o agregado em `falhou_preparacao_ia`, sem resposta fixa/modelo alternativo, preservando o trabalho determinístico anterior consultável
- [ ] Cenário de retentativa após falha terminal cria execução correlacionada nova, inicializada só com snapshots válidos, sem reabrir a original; repetição do comando comprova ausência de duplicação
- [ ] Toda evidência (prontidão, evento e decisão, supervisão, resultados, comunicado, explicação, linha do tempo) é localizável sem editar arquivo/banco; OpenAPI/Swagger UI correspondem à API realmente usada
- [ ] Fluxos principais funcionam em 1440×1024 e larguras desktop ≥1024px no Chrome estável, com aviso de resolução não suportada abaixo de 1024px
- [ ] Implementação visual usa os tokens/tipografia/escala/raios/dimensões de `DESIGN.md`, sem copiar código/config do protótipo
- [ ] Componentes e estados enumerados em `DESIGN.md`/`EXPERIENCE.md` estão implementados conforme contrato; nenhuma função aprovada permanece como botão inerte ou dado fixo
- [ ] Auditoria de acessibilidade (teclado, foco, contraste, zoom 200%, nomes acessíveis, movimento reduzido) atende WCAG 2.2 AA nos fluxos principais
- [ ] README e evidências técnicas têm comandos reproduzíveis em PT-BR; evidências estruturadas e exemplos sanitizados alimentam a entrega final (sem assumir o empacotamento em si)
- [ ] Suíte automatizada completa cobre sucesso, encerramentos antecipados, reprovação/esgotamento, falha do INMET, falha da OpenAI, idempotência, contratos da API e jornadas críticas da interface, sem integração externa real, reproduzível a partir de um conjunto restaurado

## Out of Scope

| Feature | Reason |
| --- | --- |
| Qualquer funcionalidade nova de produto | Esta história não implementa nenhuma capacidade nova — só verifica o que os Épicos 1–4 e 5.1–5.7 já entregaram |
| Empacotamento final (PDF, ZIP, checksums, publicação) | História 5.9 — esta história produz as evidências que 5.9 consome, não o pacote em si |
| Correção de bugs encontrados durante a validação | Vira trabalho de fix nas histórias correspondentes (ou uma task de correção pontual referenciando o AC violado), não parte do escopo original desta história |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Forma de "comprovar os cenários" | Testes de integração/E2E automatizados (backend `pytest`, frontend `vitest`/testing-library) cobrindo cada cenário do AC, mais uma auditoria manual assistida por ferramenta (Chrome DevTools/axe ou equivalente) para os critérios de acessibilidade/visual que exigem inspeção humana — não um "roteiro de demonstração" só narrativo sem evidência automatizada | O próprio AC pede "testes automatizados" e "evidências estruturadas"; alguns critérios (contraste visual, fidelidade a `DESIGN.md`) exigem inspeção assistida, não só asserção de código | y — decorre diretamente do próprio texto do AC ("testes automatizados desta história... deverão cobrir") |
| Onde as evidências estruturadas ficam registradas | Um diretório `docs/evidencias/` (novo) com um relatório por cenário (markdown, com referência a `file:line` dos testes que o comprovam e capturas de tela/HTML relevantes), consumido pela História 5.9 para o relatório técnico final | O AC de 5.9 exige "evidências estruturadas e exemplos sanitizados produzidos pela validação integrada" como insumo — precisa de um local versionado e citável | n — decisão técnica de organização, revisável no Design |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Cenários completos e encerramentos determinísticos comprovados ⭐ MVP

**User Story**: Como pessoa avaliadora, quero executar os cenários de chuva intensa, granizo, sem risco e sem elegível de ponta a ponta, para confirmar o funcionamento correto do fluxo principal e dos encerramentos antecipados.

**Why P1**: É a prova de que o produto funciona como um todo — sem ela, nenhuma outra evidência importa.

**Acceptance Criteria**:

1. WHEN o cenário de chuva intensa residencial for executado em um ambiente restaurado com todas as dependências disponíveis THEN ele SHALL avançar da entrada meteorológica até a visualização do comunicado de um segurado elegível, incluindo ao menos um registro não elegível com explicação consultável.
2. WHEN o cenário de granizo automóvel for executado THEN ele SHALL avançar da entrada meteorológica até a visualização do comunicado, preservando regras, apólices, canais e recomendações específicas desse evento, com a entrada meteorológica fornecida pelo cenário sintético rotulado (AD-013 — granizo não existe nas leituras reais de estações automáticas).
3. WHEN os cenários de um evento sem risco e de um evento sem público elegível forem executados THEN ambos SHALL terminar com motivo e evidência determinísticos, sem nenhuma chamada à OpenAI, mensagem ou simulação.

**Independent Test**: Rodar a suíte de testes E2E dos 4 cenários e confirmar todos verdes, com o relatório de evidência de cada um citando os `file:line` dos testes correspondentes.

---

### P1: Resiliência agêntica e de integração comprovada ⭐ MVP

**User Story**: Como pessoa avaliadora, quero comprovar que regeneração, contingência do INMET, indisponibilidade da OpenAI e retentativa correlacionada funcionam exatamente como especificado, para confiar na resiliência do sistema.

**Why P1**: É a prova de que o produto se comporta corretamente sob falha — o diferencial de qualidade da PoC.

**Acceptance Criteria**:

1. WHEN o cenário de regeneração for executado a partir de uma reprovação do agente crítico THEN ele SHALL demonstrar o retorno ao redator, os motivos, o histórico e o limite de 3 tentativas, com o esgotamento produzindo exceção e impedindo a mensagem afetada de entrar na simulação.
2. WHEN o cenário de contingência for executado sobre uma indisponibilidade controlada do INMET THEN ele SHALL demonstrar timeout, tentativas, snapshot apenas informativo e ativação explícita do cenário sintético, com a origem sintética permanecendo visível até o fim do fluxo.
3. WHEN a produção agêntica for alcançada sob indisponibilidade ou configuração ausente da OpenAI THEN o preflight SHALL terminar o agregado em `falhou_preparacao_ia`, sem resposta fixa ou modelo alternativo, com o trabalho determinístico anterior permanecendo consultável.
4. WHEN o cenário de retentativa for executado a partir de uma falha terminal de preparação da IA ou da simulação local THEN uma nova execução correlacionada SHALL ser criada, inicializada somente com snapshots imutáveis válidos, sem reabrir a original, e a repetição do comando SHALL comprovar que execução e efeitos não são duplicados.

**Independent Test**: Rodar a suíte de testes dos 4 cenários de resiliência e confirmar todos verdes, com evidência de que nenhuma chamada real à OpenAI ou ao INMET ocorreu.

---

### P1: Evidências localizáveis, contrato de API fiel e suíte completa ⭐ MVP

**User Story**: Como pessoa avaliadora, quero localizar toda evidência de cada cenário sem editar arquivo ou banco, e confirmar que a suíte automatizada cobre os caminhos críticos, para avaliar o produto com confiança e reprodutibilidade.

**Why P1**: É o fechamento formal da validação — sem evidência localizável e suíte reproduzível, a demonstração não é auditável.

**Acceptance Criteria**:

1. WHEN a pessoa navegar pelas evidências de qualquer cenário executado THEN ela SHALL localizar prontidão, evento e decisão, supervisão, resultados, comunicado, explicação e linha do tempo sem editar arquivos ou banco, e OpenAPI/Swagger UI SHALL corresponder à API realmente utilizada.
2. WHEN a suíte automatizada completa for executada sem integrações externas reais THEN ela SHALL cobrir sucesso, encerramentos antecipados, reprovação e esgotamento, falha do INMET, falha da OpenAI, idempotência, contratos da API e jornadas críticas da interface, com resultados reproduzíveis a partir de um conjunto restaurado.

**Independent Test**: A partir de um `checkout` limpo e um banco restaurado, rodar `uv run --directory src/backend pytest` e `npm test --prefix src/frontend -- --run` e confirmar 100% de sucesso sem nenhuma chamada de rede real registrada.

---

### P2: Fidelidade visual, componentes contratados e acessibilidade WCAG 2.2 AA

**User Story**: Como pessoa avaliadora, quero confirmar que a implementação segue o sistema visual aprovado, que nenhum componente ficou inerte, e que os critérios de acessibilidade são atendidos, para avaliar a qualidade de execução do produto.

**Why P2**: Reforça a qualidade de execução sobre o funcionamento já comprovado pela P1; não bloqueia a validação funcional dos cenários em si.

**Acceptance Criteria**:

1. WHEN os fluxos principais forem verificados na referência de 1440×1024 e em larguras desktop a partir de 1024px no Chrome estável THEN nenhuma função essencial SHALL desaparecer, com o sistema visual aprovado permanecendo consistente, e abaixo de 1024px o aviso de resolução não suportada SHALL ser exibido.
2. WHEN os estilos e componentes forem inspecionados THEN eles SHALL usar os tokens de cores, tipografia Inter/Roboto Condensed, escala de espaçamento, raios e dimensões canônicas de `DESIGN.md`, sem copiar código ou configuração do protótipo.
3. WHEN cada superfície aplicável for verificada contra os componentes e estados de `DESIGN.md`/`EXPERIENCE.md` THEN carregamentos, vazios, processamentos, terminais, exceções, degradações e estados não encontrados SHALL estar implementados conforme seu contrato, sem nenhuma função aprovada permanecendo como botão inerte ou dado fixo.
4. WHEN uma auditoria de acessibilidade dos fluxos principais for realizada (teclado, foco, contraste, zoom 200%, nomes acessíveis, movimento reduzido) THEN os critérios WCAG 2.2 AA do contrato UX SHALL ser atendidos, com estados/mapas/tabelas/drawers/modais possuindo alternativas e comportamento acessíveis.

**Independent Test**: Rodar a auditoria de acessibilidade assistida (ferramenta + inspeção manual) nos fluxos principais e registrar o relatório com cada critério WCAG 2.2 AA marcado como atendido ou com desvio documentado.

---

## Edge Cases

- IF um cenário depender de dado sintético que não existe mais após uma restauração (dado alterado por outro teste) THEN a execução do cenário SHALL falhar de forma clara e diagnosticável, nunca silenciosamente com resultado parcial.
- IF a suíte completa for executada duas vezes seguidas sobre o mesmo banco restaurado THEN os resultados SHALL ser idênticos (determinismo), sem efeito cumulativo entre execuções.
- WHEN um critério WCAG 2.2 AA não puder ser atendido por uma limitação já documentada (ex.: `SPEC_DEVIATION` de uma história anterior) THEN o desvio SHALL ser registrado explicitamente na evidência, não silenciado.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| E2E-01 | P1: Cenários completos e encerramentos determinísticos comprovados | Design | Implementing |
| E2E-02 | P1: Cenários completos e encerramentos determinísticos comprovados | Design | Implementing |
| E2E-03 | P1: Cenários completos e encerramentos determinísticos comprovados | Design | Implementing |
| E2E-04 | P1: Resiliência agêntica e de integração comprovada | Design | Implementing |
| E2E-05 | P1: Resiliência agêntica e de integração comprovada | Design | Implementing |
| E2E-06 | P1: Resiliência agêntica e de integração comprovada | Design | Implementing |
| E2E-07 | P1: Resiliência agêntica e de integração comprovada | Design | Implementing |
| E2E-08 | P1: Evidências localizáveis, contrato de API fiel e suíte completa | Design | Implementing |
| E2E-09 | P1: Evidências localizáveis, contrato de API fiel e suíte completa | Design | Implementing |
| E2E-10 | P2: Fidelidade visual, componentes contratados e acessibilidade WCAG 2.2 AA | Design | Implementing |
| E2E-11 | P2: Fidelidade visual, componentes contratados e acessibilidade WCAG 2.2 AA | Design | Implementing |
| E2E-12 | P2: Fidelidade visual, componentes contratados e acessibilidade WCAG 2.2 AA | Design | Implementing |
| E2E-13 | P2: Fidelidade visual, componentes contratados e acessibilidade WCAG 2.2 AA | Design | Implementing |

**ID format:** `E2E-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 13 total, 13 mapped to tasks, 0 unmapped

---

## Success Criteria

- [ ] Os 8 cenários do AC (chuva, granizo, sem risco, sem elegível, regeneração, contingência INMET, indisponibilidade OpenAI, retentativa) têm teste automatizado verde com evidência citável
- [ ] Suíte completa roda sem nenhuma chamada de rede real e é reproduzível a partir de um conjunto restaurado
- [ ] Toda evidência de qualquer cenário é localizável pela própria interface, sem editar arquivo/banco
- [ ] OpenAPI/Swagger UI correspondem exatamente à API executada
- [ ] Auditoria de acessibilidade WCAG 2.2 AA registrada, com todo desvio documentado explicitamente (nenhum silenciado)
