-- Migração 4: snapshot imutável da avaliação de relevância meteorológica (História 2.3).
-- Segue a mesma convenção de 0001-0003: relações declaradas como comentários, nunca REFERENCES
-- (AD-005). AD-11 exige que uma mudança futura em `regras` nunca recalcule uma avaliação já
-- feita — por isso `regra_versao` é gravada aqui como valor, não como referência viva.

CREATE TABLE avaliacoes_risco (
    id            UUID PRIMARY KEY,
    execucao_id   UUID NOT NULL,  -- relaciona-se a execucao_preventiva(id)
    evento_id     UUID NOT NULL,  -- relaciona-se a eventos_meteorologicos(id)
    regra_id      UUID NOT NULL,  -- relaciona-se a regras(id)
    regra_versao  INTEGER NOT NULL,
    relevante     BOOLEAN NOT NULL,
    criterios     VARCHAR NOT NULL,
    motivo        VARCHAR NOT NULL,
    criado_em     TIMESTAMP NOT NULL DEFAULT now()
);
