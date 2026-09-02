-- Migração 7: corrige o backfill de `criterios` das linhas semeadas da migração `0006` e
-- adiciona `nome_segurado` como snapshot imutável (AD-11, ELEG-04.3).
--
-- Bug do backfill original: `0006` gravou `'{"origem": "seed_demonstrativo"}'` (um objeto
-- JSON) na coluna `criterios`, mas o parser de critérios (`serializacao_criterios.py`)
-- espera uma lista — `obter_por_id`/`listar_por_execucao` levantavam `TypeError` ao ler
-- qualquer linha semeada, e o roteador HTTP devolvia `500` em vez de `404` (achado do
-- Verificador da Round 1). Corrigido para `'[]'` (lista vazia), mesma convenção já usada
-- em `avaliacoes_risco` (migração `0005`, 2.3) para "nenhum critério real avaliado".
--
-- `nome_segurado`: antes lido ao vivo de `segurados.nome` no momento da consulta — um
-- nome alterado depois de uma avaliação concluída reescreveria a explicação histórica,
-- violando ELEG-04.3 (AD-11 já exige o mesmo tratamento para `regra_versao` em 2.3/2.4).
-- Gravado como snapshot a partir daqui; `RepositorioElegibilidades.salvar` passa a
-- recebê-lo explicitamente em vez de depender de um `JOIN`.
--
-- DuckDB não suporta `ALTER TABLE ADD COLUMN ... NOT NULL` sobre uma tabela com linhas
-- existentes: a tabela é recriada dentro desta transação (recreate-and-copy, AD-015).

CREATE TABLE elegibilidades_historicas_nova (
    id             UUID PRIMARY KEY,
    execucao_id    UUID,
    evento_id      UUID NOT NULL,
    regra_id       UUID NOT NULL,
    segurado_id    UUID NOT NULL,
    apolice_id     UUID NOT NULL,
    elegivel       BOOLEAN NOT NULL,
    criterios      VARCHAR NOT NULL,
    canal          VARCHAR NOT NULL,
    nome_segurado  VARCHAR NOT NULL,
    justificativa  VARCHAR NOT NULL,
    criado_em      TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (execucao_id, evento_id, regra_id, segurado_id, apolice_id)
);

INSERT INTO elegibilidades_historicas_nova
SELECT
    e.id,
    e.execucao_id,
    e.evento_id,
    e.regra_id,
    e.segurado_id,
    e.apolice_id,
    e.elegivel,
    CASE WHEN e.execucao_id IS NULL THEN '[]' ELSE e.criterios END,
    e.canal,
    s.nome,
    e.justificativa,
    e.criado_em
FROM elegibilidades_historicas AS e
JOIN segurados AS s ON s.id = e.segurado_id;

DROP TABLE elegibilidades_historicas;

ALTER TABLE elegibilidades_historicas_nova RENAME TO elegibilidades_historicas;
