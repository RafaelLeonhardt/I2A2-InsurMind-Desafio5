-- Migração 9: prepara a produção agêntica (História 3.1). Duas mudanças.
--
-- 1. `execucao_preventiva.execucao_origem_id`: a execução correlacionada criada por uma nova
--    tentativa depois de `falhou_preparacao_ia` aponta para a execução terminal que a originou
--    (AD-009). A coluna é nula, sem `NOT NULL`, sem `UNIQUE`/`CHECK` e sem backfill — `NULL` já é
--    o valor correto de toda linha pré-existente (execução não correlacionada). Por isso o
--    recreate-and-copy do AD-015 não se aplica aqui: ele governa constraints novas e colunas com
--    backfill, e um `ALTER TABLE ADD COLUMN` nulo não é nenhum dos dois.
--
-- 2. `contextos_agente`: o contexto mínimo montado por item elegível e sua proveniência
--    (categorias de dados usadas e não usadas), consultável antes ou depois da geração
--    (PREFL-11..14). `UNIQUE (elegibilidade_id)` garante um contexto por item; é exatamente essa
--    restrição que obriga a nova tentativa a copiar as elegibilidades da origem em vez de
--    reutilizá-las (AD-012).

ALTER TABLE execucao_preventiva ADD COLUMN execucao_origem_id UUID;

CREATE TABLE contextos_agente (
    id                     UUID PRIMARY KEY,
    execucao_id            UUID NOT NULL,  -- relaciona-se a execucao_preventiva(id)
    elegibilidade_id       UUID NOT NULL,  -- relaciona-se a elegibilidades_historicas(id)
    conteudo               VARCHAR NOT NULL,
    categorias_usadas      VARCHAR[] NOT NULL,
    categorias_nao_usadas  VARCHAR[] NOT NULL,
    criado_em              TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (elegibilidade_id)
);
