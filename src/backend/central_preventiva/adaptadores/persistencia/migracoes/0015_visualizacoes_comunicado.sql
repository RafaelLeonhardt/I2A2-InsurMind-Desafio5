-- Migração 15: primeira visualização do comunicado pelo segurado sintético (História 4.3).
-- Uma tabela nova.
--
-- SPEC_DEVIATION: o `design.md` da 4.3 nomeia esta migração `0013_visualizacoes_comunicado.sql`.
-- Motivo: `0013`/`0014` já foram consumidos pelas Histórias 3.5/3.6, implementadas antes desta.
-- Mesma renumeração já registrada desde a 2.4 — o conteúdo é o do design.
--
-- `visualizacoes_comunicado`: uma linha por entrega simulada que Carlos (o segurado sintético)
-- abriu efetivamente no perfil Segurado. `UNIQUE (entrega_simulada_id)` é a dedução de conteúdo
-- do AD-010: a primeira abertura grava, e qualquer reabertura ou duas aberturas concorrentes
-- resolvem via `INSERT ... ON CONFLICT DO NOTHING` seguido de `SELECT` da linha já persistida
-- (própria ou de um concorrente), sempre convergindo para a mesma `visualizada_em` (VISU-01,
-- VISU-02, VISU-03) — nenhum lock explícito adicional é necessário.
--
-- `segurado_id` é snapshot, não recalculado: identifica de quem foi a visualização mesmo que o
-- contexto demonstrativo alterne o segurado ativo depois (História 5.7), sem misturar
-- visualizações entre segurados sintéticos.
--
-- Nenhuma coluna declara `REFERENCES` (AD-005); as relações com `entregas_simuladas(id)` e
-- `segurados(id)` são chaves estrangeiras lógicas, documentadas aqui e no `README.md` da
-- persistência. A tabela é nova, então o recreate-and-copy do AD-015 (constraint acrescentada a
-- tabela existente) não se aplica.

CREATE TABLE visualizacoes_comunicado (
    id                   UUID PRIMARY KEY,
    entrega_simulada_id  UUID NOT NULL UNIQUE,  -- relaciona-se a entregas_simuladas(id)
    segurado_id          UUID NOT NULL,  -- relaciona-se a segurados(id); snapshot
    visualizada_em       TIMESTAMP NOT NULL DEFAULT now()
);
