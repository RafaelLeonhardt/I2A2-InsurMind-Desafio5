-- Migração 3: resiliência e contingência sintética da coleta meteorológica (História 2.2).
-- Segue a mesma convenção de 0001/0002: relações declaradas como comentários, nunca REFERENCES
-- (AD-005). Adiciona as tabelas de tentativa individual, exceção operacional e ativação de
-- cenário sintético, e acrescenta a UNIQUE de deduplicação de conteúdo a eventos_meteorologicos.

-- O DuckDB não suporta ALTER TABLE ADD CONSTRAINT: a UNIQUE é adicionada recriando a tabela
-- dentro desta mesma transação (recreate-and-copy, AD-015), preservando as linhas existentes.
-- Seguro porque nenhuma tabela declara REFERENCES (AD-005); a constraint de tabela (e não um
-- índice posterior) garante a semântica de INSERT ... ON CONFLICT DO NOTHING exigida por AD-010.
CREATE TABLE eventos_meteorologicos_nova (
    id                  UUID PRIMARY KEY,
    tipo                VARCHAR NOT NULL CHECK (tipo IN ('chuva_intensa', 'granizo')),
    area                VARCHAR NOT NULL,
    periodo_inicio      TIMESTAMP NOT NULL,
    periodo_fim         TIMESTAMP NOT NULL,
    intensidade         DOUBLE NOT NULL,
    proveniencia        VARCHAR NOT NULL CHECK (proveniencia IN ('real_inmet', 'sintetico')),
    instante_observado  TIMESTAMP NOT NULL,
    criado_em           TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (tipo, area, periodo_inicio, periodo_fim)
);

INSERT INTO eventos_meteorologicos_nova
SELECT id, tipo, area, periodo_inicio, periodo_fim, intensidade, proveniencia,
       instante_observado, criado_em
FROM eventos_meteorologicos;

DROP TABLE eventos_meteorologicos;

ALTER TABLE eventos_meteorologicos_nova RENAME TO eventos_meteorologicos;

CREATE TABLE tentativas_coleta_meteorologica (
    id                 UUID PRIMARY KEY,
    sincronizacao_id   UUID NOT NULL,  -- relaciona-se a sincronizacoes_meteorologicas(id)
    numero_tentativa   INTEGER NOT NULL CHECK (numero_tentativa BETWEEN 1 AND 3),
    codigo_resultado   VARCHAR NOT NULL CHECK (
        codigo_resultado IN ('sucesso', 'timeout', 'erro_transporte', 'status_erro')
    ),
    iniciado_em        TIMESTAMP NOT NULL,
    finalizado_em      TIMESTAMP NOT NULL
);

CREATE TABLE excecoes_operacionais (
    id            UUID PRIMARY KEY,
    execucao_id   UUID NOT NULL,  -- relaciona-se a execucao_preventiva(id)
    causa         VARCHAR NOT NULL,
    tentativas    INTEGER NOT NULL,
    impacto       VARCHAR NOT NULL,
    criado_em     TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE cenarios_sinteticos_ativados (
    id                     UUID PRIMARY KEY,
    sincronizacao_id       UUID NOT NULL,  -- relaciona-se a sincronizacoes_meteorologicas(id)
    identificador_cenario  VARCHAR NOT NULL,
    ativado_em             TIMESTAMP NOT NULL DEFAULT now()
);
