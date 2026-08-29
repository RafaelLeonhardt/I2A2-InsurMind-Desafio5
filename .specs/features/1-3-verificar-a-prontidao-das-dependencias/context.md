# História 1.3 Context

**Gathered:** 2026-08-29
**Spec:** `.specs/features/1-3-verificar-a-prontidao-das-dependencias/spec.md`
**Status:** Ready for design

---

## Feature Boundary

Uma superfície de prontidão que mostra, para backend/DuckDB/INMET/OpenAI, estado + última verificação + causa + impacto + ação; backend/DuckDB respondem local e rápido; INMET/OpenAI são sondados por chamada real, assíncrona e idempotente, sem nunca expor a credencial da OpenAI.

---

## Implementation Decisions

### Mecanismo das checagens externas

- INMET: chamada HTTP real a um endpoint público, timeout curto, sem retry automático nesta sonda (a sonda é um "ping" de prontidão, não o adaptador de produção da História 2.1).
- OpenAI: sem `OPENAI_API_KEY` → indisponível sem chamada de rede; com chave → uma chamada real de baixo custo (ex. listar modelos), chave nunca logada nem ecoada.

### Disparo e progresso

- Automático nas 4 dependências ao carregar a superfície.
- Re-verificação manual é uma ação por dependência (4 botões independentes), não um "verificar tudo".
- Progresso consultado por polling HTTP curto (~2s) enquanto o estado for não terminal; sem SSE/websocket.

### Classificação Degradada vs Indisponível

- Degradada: resposta obtida porém lenta (acima de um orçamento de latência a definir em Design) ou status transitório (ex. 429/5xx) numa única tentativa.
- Indisponível: timeout, falha de conexão, ou erro não transitório (ex. DNS, 401 de credencial inválida).
- Os valores numéricos exatos (orçamento de latência, timeout) ficam para Design — são parâmetro técnico, não decisão de produto.

### Persistência

- Estado de prontidão em memória, por processo do backend. Reinício = re-verificação do zero. Nenhuma tabela DuckDB nova para isto.

### Agent's Discretion

- Formato exato do contrato HTTP do job assíncrono (nome do recurso, forma da resposta de progresso) — segue os padrões REST/JSON já estabelecidos no resto da API (recursos plurais, `snake_case`, `Idempotency-Key`).
- Comportamento de conflito quando duas `Idempotency-Key` diferentes chegam para a mesma dependência enquanto uma verificação já está em andamento.

### Declined / Undiscussed Gray Areas → Assumptions

Nenhuma — todas as áreas cinzentas identificadas foram discutidas e estão registradas na tabela de Assumptions do `spec.md`.

---

## Specific References

Nenhuma referência visual/produto específica trazida pelo usuário além das respostas às perguntas de decisão acima.

---

## Deferred Ideas

None — discussion stayed within feature scope.
