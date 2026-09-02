-- Migração 5: permite persistir o terminal `sem_risco` quando não há regra ativa (RISCO-09).
-- `regra_id`/`regra_versao` passam a aceitar nulo — sem regra ativa para o tipo do evento,
-- não há regra real a referenciar, mas a execução ainda precisa de um snapshot explicável
-- (código e motivo persistidos), em vez de terminar sem nenhum registro consultável.
--
-- DuckDB não suporta ALTER TABLE ALTER COLUMN DROP NOT NULL nem ADD/DROP CONSTRAINT: a
-- coluna é relaxada recriando a tabela dentro desta transação (recreate-and-copy, AD-015),
-- preservando todas as linhas existentes.

CREATE TABLE avaliacoes_risco_nova (
    id            UUID PRIMARY KEY,
    execucao_id   UUID NOT NULL,  -- relaciona-se a execucao_preventiva(id)
    evento_id     UUID NOT NULL,  -- relaciona-se a eventos_meteorologicos(id)
    regra_id      UUID,           -- nulo quando não havia regra ativa para o tipo do evento
    regra_versao  INTEGER,        -- nulo pelo mesmo motivo; nunca referência viva (AD-11)
    relevante     BOOLEAN NOT NULL,
    criterios     VARCHAR NOT NULL,
    motivo        VARCHAR NOT NULL,
    criado_em     TIMESTAMP NOT NULL DEFAULT now()
);

INSERT INTO avaliacoes_risco_nova
SELECT id, execucao_id, evento_id, regra_id, regra_versao, relevante, criterios, motivo,
       criado_em
FROM avaliacoes_risco;

DROP TABLE avaliacoes_risco;

ALTER TABLE avaliacoes_risco_nova RENAME TO avaliacoes_risco;
