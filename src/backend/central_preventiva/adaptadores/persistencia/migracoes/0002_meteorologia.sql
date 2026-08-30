-- Migração 2: tabelas de coleta meteorológica do INMET (História 2.1).
-- Segue a mesma convenção de 0001_schema_inicial.sql: relações declaradas como comentários,
-- nunca como REFERENCES (AD-005).
-- Cria o mapeamento de estação real do INMET para área sintética (AD-007) e o histórico
-- de sincronizações de coleta meteorológica.

CREATE TABLE areas_monitoradas_inmet (
    id                     UUID PRIMARY KEY,
    codigo_estacao_inmet   VARCHAR NOT NULL,
    nome_estacao           VARCHAR NOT NULL,
    codigo_ibge_area       VARCHAR NOT NULL,  -- relaciona-se a segurados/apolices(codigo_ibge_area)
    ativa                  BOOLEAN NOT NULL DEFAULT true,
    criado_em              TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE sincronizacoes_meteorologicas (
    id                   UUID PRIMARY KEY,
    requisicao_id        UUID NOT NULL,
    area_monitorada_id   UUID NOT NULL,  -- relaciona-se a areas_monitoradas_inmet(id)
    origem               VARCHAR NOT NULL CHECK (origem IN ('automatica', 'manual')),
    estado               VARCHAR NOT NULL CHECK (estado IN ('coletando', 'normalizando', 'concluido', 'falha')),
    registros_validos    INTEGER NOT NULL DEFAULT 0,
    motivo_falha         VARCHAR,
    iniciado_em          TIMESTAMP NOT NULL DEFAULT now(),
    finalizado_em        TIMESTAMP
);
