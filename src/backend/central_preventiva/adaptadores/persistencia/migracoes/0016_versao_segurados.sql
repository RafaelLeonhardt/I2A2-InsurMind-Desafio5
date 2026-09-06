-- Migração 16: adiciona `versao` a `segurados` (História 5.6, PREFS-02) — concorrência
-- otimista para a primeira escrita legítima nessa tabela (`canal_preferido`,
-- `participa_de_alertas`), mesmo padrão já usado em `regras.versao`/`execucao_preventiva.versao`.
--
-- `design.md` da história numera o arquivo `0014_versao_segurados.sql`; `0014`/`0015` já
-- haviam sido consumidos pelas Histórias 3.1–3.5/4.3, então a migração entrou como `0016`
-- — mesma renumeração já registrada desde a 2.4.
--
-- DuckDB não suporta `ALTER TABLE ADD COLUMN ... NOT NULL` sobre uma tabela com linhas
-- existentes (AD-015): a tabela é recriada dentro desta transação (recreate-and-copy),
-- com `versao` iniciando em `1` para todo segurado sintético já semeado.

CREATE TABLE segurados_nova (
    id                    UUID PRIMARY KEY,
    nome                  VARCHAR NOT NULL,
    codigo_ibge_area      VARCHAR NOT NULL,
    canal_preferido       VARCHAR NOT NULL CHECK (canal_preferido IN ('whatsapp', 'email', 'sms')),
    participa_de_alertas  BOOLEAN NOT NULL DEFAULT true,
    versao                INTEGER NOT NULL DEFAULT 1,
    criado_em             TIMESTAMP NOT NULL DEFAULT now(),
    atualizado_em         TIMESTAMP NOT NULL DEFAULT now()
);

INSERT INTO segurados_nova
SELECT
    id,
    nome,
    codigo_ibge_area,
    canal_preferido,
    participa_de_alertas,
    1,
    criado_em,
    atualizado_em
FROM segurados;

DROP TABLE segurados;

ALTER TABLE segurados_nova RENAME TO segurados;
