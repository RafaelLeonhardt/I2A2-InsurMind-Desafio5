# História 2.4: Configurar, testar e versionar regras preventivas — Specification

## Problem Statement

A História 2.3 consome a regra ativa da tabela `regras`, mas nada ainda permite a Marina consultar, editar, testar e ativar essas regras com segurança. Sem essa gestão, qualquer ajuste de limiar exigiria mudar dado diretamente no banco, sem validação, sem teste prévio e sem preservar o histórico que as execuções já concluídas dependem (AD-11).

## Goals

- [ ] Marina consulta e cria versões de regra a partir de configuração versionada e legível, com padrões e justificativa documentados, e testes cobrindo exemplos abaixo/sobre/acima de cada fronteira
- [ ] A superfície Regras exibe tipo de evento, severidade, limiar, área, tipo/situação da apólice, coberturas, antecedência, canal, versão e estado, com a regra ativa identificada por texto, ícone e indicador
- [ ] O formulário de edição valida tipos, faixas, combinações obrigatórias e coerência evento↔produto, com erros junto ao campo sem descartar valores informados
- [ ] Configuração inválida bloqueia teste e ativação com motivos específicos em português brasileiro, sem criar nova versão ativa
- [ ] Marina testa deterministicamente uma configuração válida contra cenários sintéticos antes de ativar, vendo operando/valor observado/resultado/justificativa por caso
- [ ] Ativar uma configuração testada cria uma nova versão imutável e a torna ativa; a versão anterior permanece consultável e inalterada
- [ ] Uma execução já iniciada preserva o snapshot da versão originalmente aplicada, sem recálculo silencioso quando a regra ativa mudar
- [ ] Duas edições concorrentes da mesma regra usam `versao_esperada`: só a primeira confirma, a segunda recebe `409`
- [ ] Ativação repetida com a mesma `Idempotency-Key` e conteúdo idêntico devolve a resposta registrada; conteúdo diferente retorna `409`
- [ ] Tabela, formulário e teste são totalmente operáveis por teclado, sem depender de hover ou cor isolada

## Out of Scope

| Feature | Reason |
| --- | --- |
| Consumo da regra ativa durante a avaliação de risco | História 2.3 — esta história só gerencia o ciclo de vida da regra, não a consome em produção |
| Duplicação de regras e gestão avançada de histórico | Explicitamente fora do MVP nos ACs da própria história |
| Regras para tipos de evento além de chuva intensa e granizo | Consistente com o escopo suportado definido na História 2.3 |
| Aprovação/fluxo de múltiplos usuários para ativar uma regra | Fora do MVP; a PoC não tem múltiplos perfis operacionais concorrentes com aprovação formal (ADR-0009) |

---

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Cenários sintéticos usados no teste determinístico de uma regra | Reutiliza o conjunto sintético de demonstração já semeado (Épico 1), sem introduzir um gerador de cenários hipotéticos novo | A história pede "aplicar deterministicamente a regra aos cenários sintéticos selecionados"; o conjunto demonstrativo do Épico 1 já é a fonte de verdade de dados sintéticos do projeto | y — decisão do usuário refletida no PRD (Épico 1 é pré-requisito) |
| Mecanismo de concorrência otimista | Campo `versao_esperada` enviado pelo cliente em toda mutação de regra, comparado à `versao` corrente da linha ativa antes de aceitar a mudança, dentro da mesma transação | Já é o comportamento literal exigido pelo AC de concorrência; a tabela `regras` já tem coluna `versao` | y — já decidido no schema/AC, apenas confirmado aqui |
| Granularidade da "nova versão imutável" | Ativar uma alteração cria uma nova linha em `regras` com `versao` incrementada e `estado = ativa`; a linha anterior muda para `estado = substituida` e nunca é editada novamente | Alinhado ao schema já existente (`regras.estado` com `CHECK` em `ativa`, `substituida`) e ao AD-11 (histórico preservado) | y — já decidido no schema do Épico 1, apenas confirmado aqui |

**Open questions:** none — todas resolvidas ou registradas acima.

---

## User Stories

### P1: Consulta e edição validada de regras ⭐ MVP

**User Story**: Como Marina, quero consultar as regras existentes e editar seus critérios com validação clara, para ajustar parâmetros objetivos sem risco de configuração inconsistente.

**Why P1**: É o ponto de entrada de toda a história — sem consulta e edição validada não há nada para testar ou ativar.

**Acceptance Criteria**:

1. The system SHALL originar os limiares e janelas usados pelas regras de configuração versionada e legível, com padrões e justificativa documentados.
2. The rule tests SHALL incluir exemplos imediatamente abaixo, sobre e acima de cada fronteira relevante da regra.
3. WHEN Marina abrir a superfície Regras THEN o sistema SHALL exibir tipo de evento, severidade, limiar meteorológico, área, tipo e situação da apólice, coberturas, antecedência, canal, versão e estado de cada regra.
4. The interface SHALL identificar a regra ativa por texto, ícone e indicador visual.
5. WHEN Marina iniciar a edição de uma regra e alterar seus critérios THEN o formulário SHALL validar tipos, faixas, combinações obrigatórias e coerência entre evento e produto.
6. IF o formulário encontrar um erro de validação THEN o sistema SHALL exibi-lo junto ao campo correspondente sem descartar os valores já informados.

**Independent Test**: Abrir a superfície Regras, editar um limiar para um valor fora de faixa e confirmar que o erro aparece junto ao campo sem apagar os demais valores digitados.

---

### P1: Teste determinístico e ativação versionada ⭐ MVP

**User Story**: Como Marina, quero testar uma configuração válida contra cenários conhecidos antes de ativá-la, e ver o histórico preservado depois, para nunca alterar decisões já registradas por engano.

**Why P1**: É o núcleo de segurança da história — impedir ativação sem teste e preservar histórico.

**Acceptance Criteria**:

1. IF Marina tentar testar ou ativar uma configuração inválida THEN a operação SHALL ser bloqueada com motivos específicos em português brasileiro, sem criar nenhuma nova versão ativa.
2. WHEN Marina solicitar o teste de uma configuração válida ainda não testada THEN o backend SHALL aplicar deterministicamente a regra aos cenários sintéticos selecionados, e a interface SHALL apresentar, para cada caso, operando, valor observado, resultado e justificativa.
3. WHEN Marina salvar e ativar uma alteração cujo teste válido foi concluído THEN o sistema SHALL criar uma nova versão imutável da regra e torná-la ativa para execuções futuras, mantendo a versão anterior consultável e inalterada.
4. IF a regra ativa receber uma nova versão enquanto uma execução iniciada antes da alteração está em curso THEN essa execução SHALL conservar o snapshot da versão originalmente aplicada, sem recalcular silenciosamente seu resultado ou sua explicação.

**Independent Test**: Testar uma configuração válida, confirmar os resultados por caso, ativá-la, e confirmar que uma execução previamente iniciada continua referenciando a versão antiga da regra.

---

### P2: Concorrência, idempotência e acessibilidade

**User Story**: Como Marina, quero editar e ativar regras com segurança mesmo sob concorrência ou repetição acidental, e operar toda a superfície só pelo teclado, para confiar na ferramenta em qualquer condição de uso.

**Why P2**: Reforça robustez operacional sobre o fluxo principal já coberto pelas stories P1; não bloqueia a primeira demonstração de edição/teste/ativação.

**Acceptance Criteria**:

1. IF duas tentativas concorrentes de alterar a mesma regra informarem a mesma `versao_esperada` THEN somente a primeira transação válida SHALL ser confirmada, e a segunda SHALL receber `409` sem sobrescrever ou aplicar parcialmente a mudança.
2. WHEN o comando de ativação for repetido com a mesma `Idempotency-Key` e conteúdo idêntico THEN o sistema SHALL devolver a resposta registrada sem criar outra versão.
3. IF a mesma `Idempotency-Key` for reusada com conteúdo diferente THEN o sistema SHALL retornar `409`.
4. WHEN Marina navegar, editar e confirmar pela tabela, formulário e teste usando somente o teclado THEN cabeçalhos, campos, resultados e ações SHALL possuir nomes acessíveis, foco visível e ordem lógica, sem depender de hover ou cor isolada.
5. The MVP scope SHALL oferecer consulta das versões necessárias à explicação e à auditoria, sem duplicação de regras nem gestão avançada de histórico.

**Independent Test**: Disparar duas ativações concorrentes com a mesma `versao_esperada` e confirmar que só uma é aceita e a outra retorna `409`; navegar a superfície inteira só com teclado e confirmar foco visível em cada etapa.

---

## Edge Cases

- IF Marina tentar ativar uma regra cuja combinação evento↔produto for inconsistente (ex.: granizo associado a apólice residencial fora do padrão configurado) THEN o formulário SHALL bloquear com um motivo específico antes de permitir o teste.
- IF o teste determinístico não encontrar nenhum cenário sintético aplicável ao tipo de evento da regra THEN o sistema SHALL retornar um resultado vazio válido, não um erro técnico, e SHALL continuar bloqueando a ativação até que a configuração seja revisada.
- WHEN uma ativação idêntica for reenviada após a resposta original já ter expirado da UI (mas a chave ainda válida no backend) THEN o sistema SHALL continuar devolvendo a resposta originalmente registrada.

---

## Requirement Traceability

| Requirement ID | Story | Phase | Status |
| --- | --- | --- | --- |
| REGRA-01 | P1: Consulta e edição validada de regras | Design | Pending |
| REGRA-02 | P1: Consulta e edição validada de regras | Design | Pending |
| REGRA-03 | P1: Consulta e edição validada de regras | Design | Pending |
| REGRA-04 | P1: Consulta e edição validada de regras | Design | Pending |
| REGRA-05 | P1: Consulta e edição validada de regras | Design | Pending |
| REGRA-06 | P1: Consulta e edição validada de regras | Design | Pending |
| REGRA-07 | P1: Teste determinístico e ativação versionada | Design | Pending |
| REGRA-08 | P1: Teste determinístico e ativação versionada | Design | Pending |
| REGRA-09 | P1: Teste determinístico e ativação versionada | Design | Pending |
| REGRA-10 | P1: Teste determinístico e ativação versionada | Design | Pending |
| REGRA-11 | P2: Concorrência, idempotência e acessibilidade | Design | Pending |
| REGRA-12 | P2: Concorrência, idempotência e acessibilidade | Design | Pending |
| REGRA-13 | P2: Concorrência, idempotência e acessibilidade | Design | Pending |
| REGRA-14 | P2: Concorrência, idempotência e acessibilidade | Design | Pending |
| REGRA-15 | P2: Concorrência, idempotência e acessibilidade | Design | Pending |

**ID format:** `REGRA-NN`

**Status values:** Pending → In Design → In Tasks → Implementing → Verified

**Coverage:** 15 total, 0 mapped to tasks, 15 unmapped ⚠️ (mapeamento ocorre na fase Tasks)

---

## Success Criteria

- [ ] Uma configuração inválida nunca produz nova versão ativa
- [ ] Ativar uma regra testada cria versão nova e preserva a versão anterior consultável e inalterada
- [ ] Uma execução em curso nunca tem seu resultado recalculado por uma mudança posterior na regra ativa
- [ ] Duas edições concorrentes com a mesma `versao_esperada` resultam em exatamente uma aceita e uma `409`
- [ ] Toda a superfície Regras é operável por teclado com foco visível em cada etapa
