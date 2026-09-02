-- Migração 6: estende `elegibilidades_historicas` para a avaliação real de elegibilidade
-- (ELEG-04..07). Acrescenta `execucao_id` (nulo identifica linha semeada de demonstração,
-- anterior ao motor de execuções), `criterios` (snapshot JSON critério a critério, mesmo
-- formato de `avaliacoes_risco.criterios`) e `canal` (canal preferencial do segurado
-- congelado no momento da avaliação, nunca referência viva a `segurados.canal_preferido`,
-- AD-11). `UNIQUE(execucao_id, evento_id, regra_id, segurado_id, apolice_id)` garante no
-- máximo um resultado por combinação (AD-10) — linhas semeadas com `execucao_id NULL`
-- nunca colidem entre si, pois `NULL` é sempre distinto de outro `NULL` em `UNIQUE`.
--
-- DuckDB não suporta ALTER TABLE ADD COLUMN ... NOT NULL nem ADD CONSTRAINT sobre uma
-- tabela com linhas existentes: a tabela é recriada dentro desta transação
-- (recreate-and-copy, AD-015), com backfill determinístico das 4 linhas semeadas do
-- Épico 1 (`canal` via JOIN em `segurados`, `criterios` com o marcador de origem).

CREATE TABLE elegibilidades_historicas_nova (
    id             UUID PRIMARY KEY,
    execucao_id    UUID,           -- nulo identifica linha semeada de demonstração
    evento_id      UUID NOT NULL,  -- relaciona-se a eventos_meteorologicos(id)
    regra_id       UUID NOT NULL,  -- relaciona-se a regras(id)
    segurado_id    UUID NOT NULL,  -- relaciona-se a segurados(id)
    apolice_id     UUID NOT NULL,  -- relaciona-se a apolices(id)
    elegivel       BOOLEAN NOT NULL,
    criterios      VARCHAR NOT NULL,
    canal          VARCHAR NOT NULL,
    justificativa  VARCHAR NOT NULL,
    criado_em      TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (execucao_id, evento_id, regra_id, segurado_id, apolice_id)
);

INSERT INTO elegibilidades_historicas_nova
SELECT
    e.id,
    NULL,
    e.evento_id,
    e.regra_id,
    e.segurado_id,
    e.apolice_id,
    e.elegivel,
    '{"origem": "seed_demonstrativo"}',
    s.canal_preferido,
    e.justificativa,
    e.criado_em
FROM elegibilidades_historicas AS e
JOIN segurados AS s ON s.id = e.segurado_id;

DROP TABLE elegibilidades_historicas;

ALTER TABLE elegibilidades_historicas_nova RENAME TO elegibilidades_historicas;
