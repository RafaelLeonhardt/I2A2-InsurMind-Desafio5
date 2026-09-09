# História 6.7: Monitorar a fonte meteorológica INMET — Specification

## Problem Statement

O protótipo (`SourcePage`/imagem `11-fonte-meteorologica-instabilidade`) mostra o administrador monitorando o status da integração com o INMET: operando, instável, histórico de sincronizações e ações de "tentar novamente"/"usar cenário de demonstração". `SuperficieFonteMeteorologica` (`src/frontend/src/funcionalidades/fonte-meteorologica/SuperficieFonteMeteorologica.tsx`) já calcula os seis estados possíveis da fonte (`operacional`, `em_tentativa`, `indisponivel`, `sintetica`, `recuperada`, `degradada`) a partir de dados já persistidos, e é testada isoladamente — mas hoje só é reaproveitada como utilitário interno (`calcularIdade`) dentro de `VisaoGeralSegurado`, nunca como tela própria do administrador. Sem esta história, o administrador não tem como saber se um evento veio de dado real do INMET ou do cenário sintético de contingência, nem se a fonte está operando normalmente.

## Goals

- [ ] O administrador acessa "Fontes de dados" pela navegação (História 6.1) e vê o estado atual da fonte meteorológica com um rótulo compreensível para cada um dos seis estados já calculados
- [ ] O histórico de sincronizações (tentativas, sucesso/falha, quando cada uma ocorreu) fica visível
- [ ] Uma sincronização com falha pode ser reexecutada pelo administrador diretamente da tela

## Out of Scope

| Feature | Reason |
| --- | --- |
| Alterar a configuração da integração (chaves, endpoint, frequência) | Fora do domínio atual — a configuração de coleta é feita por variável de ambiente (README/`.env.example`), não pela interface |
| Novo endpoint de "usar cenário de demonstração" específico desta tela | Já coberto pela restauração de dados sintéticos existente (Épico 1, `RestaurarDemonstracao`); esta história não duplica esse mecanismo |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Fonte de dado | `SuperficieFonteMeteorologica()` já implementada, sem props, consome os endpoints já existentes (`GET /eventos`, `GET /sincronizacoes`) — a integração é só a montagem do componente na navegação do admin | Confirmado pela assinatura do componente já existente | y — grounded no código-fonte |
| Reexecução de sincronização falha | Reusa o mecanismo de retentativa já existente no backend (`meteorologia`/`cliente_inmet`, RESIL-05..RESIL-15) — a ação "tentar novamente" apenas dispara essa retentativa, não implementa lógica de retry nova | O componente já classifica `em_tentativa`/`indisponivel` a partir do estado real da última sincronização; a ação de retry só precisa acionar o endpoint correspondente | y — grounded no código-fonte e nos comentários de `RESIL-NN` já presentes no arquivo |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Consultar o estado atual da fonte meteorológica ⭐ MVP

**User Story**: Como administrador, quero ver se a fonte meteorológica está operando normalmente, em tentativa, indisponível ou usando dado sintético de contingência, para saber se posso confiar nos eventos climáticos exibidos no restante do painel.

**Why P1**: É a garantia de transparência sobre a origem do dado — sem ela, o administrador não distingue um evento real de um sintético de contingência.

**Acceptance Criteria**:

1. WHEN o administrador abrir "Fontes de dados" THEN a interface SHALL exibir o estado atual da fonte meteorológica (um dos seis já calculados por `calcularEstadoFonte`) com um rótulo em linguagem acessível.
2. WHILE a fonte estiver em `indisponivel` ou `degradada` the interface SHALL destacar isso visualmente de forma distinta do estado `operacional`.
3. IF o evento mais recente tiver proveniência sintética (`sintetica`) THEN a interface SHALL informar explicitamente que aquele dado não veio de uma coleta real.

**Independent Test**: Forçar (via cenário sintético de contingência) uma sequência de falha seguida de sucesso e confirmar que a tela mostra `indisponivel` e depois `recuperada`, na sequência correta.

---

### P1: Consultar o histórico de sincronizações ⭐ MVP

**User Story**: Como administrador, quero ver o histórico de tentativas de sincronização com o INMET para entender a estabilidade recente da integração.

**Why P1**: Complementa o estado atual com contexto histórico — sem ele, um estado pontual não diz se o problema é recorrente.

**Acceptance Criteria**:

1. WHEN o administrador consultar o histórico de sincronizações THEN a interface SHALL listar cada tentativa com seu resultado (sucesso ou falha) e o instante em que ocorreu.

**Independent Test**: Confirmar que o número de entradas do histórico exibido corresponde ao retornado por `GET /sincronizacoes` para o período consultado.

---

### P2: Tentar novamente uma sincronização falha

**User Story**: Como administrador, quero acionar uma nova tentativa de sincronização quando a fonte estiver indisponível, para tentar restabelecer a coleta de dado real sem esperar o próximo ciclo automático.

**Why P2**: Ação de conveniência sobre o monitoramento da P1 — a tela já cumpre seu propósito de transparência sem essa ação.

**Acceptance Criteria**:

1. WHEN o administrador acionar "Tentar novamente" com a fonte em `indisponivel` THEN o sistema SHALL disparar uma nova tentativa de sincronização e atualizar o estado exibido de acordo com o resultado.

**Independent Test**: Com a fonte em `indisponivel` no cenário sintético, acionar "Tentar novamente" e confirmar que o histórico registra a nova tentativa.

---

## Edge Cases

- IF nenhuma sincronização tiver ocorrido ainda (`historico.ultimaTentativa === null`) THEN a interface SHALL mostrar `operacional` com uma indicação de "nenhuma coleta ainda", não um erro.
- WHEN mais de uma condição de estado for verdadeira ao mesmo tempo THEN a interface SHALL seguir exatamente a ordem de precedência já implementada em `calcularEstadoFonte` (em_tentativa/indisponivel → sintética → recuperada → degradada → operacional), sem introduzir uma ordem divergente na exibição.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| MONITORFONTE-01 | P1: Consultar o estado atual da fonte meteorológica | Execute | Implementing — `App.tsx` monta `SuperficieFonteMeteorologica`; evidência pré-existente em `SuperficieFonteMeteorologica.test.tsx`; aguardando Verifier |
| MONITORFONTE-02 | P1: Consultar o estado atual da fonte meteorológica | Execute | Implementing — estados `indisponivel`/`degradada` já destacados (badges), evidência pré-existente; aguardando Verifier |
| MONITORFONTE-03 | P1: Consultar o estado atual da fonte meteorológica | Execute | Implementing — estado `sintetica` já sinalizado, evidência pré-existente; aguardando Verifier |
| MONITORFONTE-04 | P1: Consultar o histórico de sincronizações | Execute | Implementing — histórico já exibido, evidência pré-existente; aguardando Verifier |
| MONITORFONTE-05 | P2: Tentar novamente uma sincronização falha | Execute | Implementing — `solicitarNovaTentativa` já implementado, evidência pré-existente; aguardando Verifier |

**ID format:** `MONITORFONTE-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 5 total, 5 mapped, 0 unmapped — Design feito inline (Medium, componente `SuperficieFonteMeteorologica` já pronto e exaustivamente testado desde antes — só integração de navegação); aguardando Verifier.

---

## Success Criteria

- [ ] O estado exibido nunca diverge do calculado por `calcularEstadoFonte` a partir do dado real
- [ ] Um evento sintético de contingência é sempre identificável como tal na tela
- [ ] Uma retentativa nunca é disparada em duplicidade por um duplo clique
