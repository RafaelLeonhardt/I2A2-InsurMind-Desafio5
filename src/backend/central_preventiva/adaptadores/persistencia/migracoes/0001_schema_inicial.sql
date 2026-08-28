-- Migração 1: schema inicial de referência da Central Preventiva.
-- Cria o registro de migrações, as tabelas de referência semeadas pela demonstração,
-- a casca mínima de execucao_preventiva e o armazenamento genérico de idempotência.

CREATE TABLE schema_migracoes (
    versao       INTEGER PRIMARY KEY,
    descricao    VARCHAR NOT NULL,
    aplicada_em  TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE segurados (
    id                    UUID PRIMARY KEY,
    nome                  VARCHAR NOT NULL,
    codigo_ibge_area      VARCHAR NOT NULL,
    canal_preferido       VARCHAR NOT NULL CHECK (canal_preferido IN ('whatsapp', 'email', 'sms')),
    participa_de_alertas  BOOLEAN NOT NULL DEFAULT true,
    criado_em             TIMESTAMP NOT NULL DEFAULT now(),
    atualizado_em         TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE apolices (
    id                        UUID PRIMARY KEY,
    segurado_id               UUID NOT NULL REFERENCES segurados(id),
    numero                    VARCHAR NOT NULL,
    tipo                      VARCHAR NOT NULL CHECK (tipo IN ('residencial', 'automovel')),
    situacao                  VARCHAR NOT NULL CHECK (situacao IN ('ativa', 'cancelada', 'suspensa')),
    vigencia_inicio           DATE NOT NULL,
    vigencia_fim              DATE NOT NULL,
    coberturas                VARCHAR[] NOT NULL,
    endereco_risco_sintetico  VARCHAR NOT NULL,
    codigo_ibge_area          VARCHAR NOT NULL,
    criado_em                 TIMESTAMP NOT NULL DEFAULT now(),
    atualizado_em             TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE regras (
    id                    UUID PRIMARY KEY,
    evento_tipo           VARCHAR NOT NULL CHECK (evento_tipo IN ('chuva_intensa', 'granizo')),
    limiar_meteorologico  DOUBLE NOT NULL,
    area_aplicavel        VARCHAR NOT NULL,
    apolice_tipo          VARCHAR NOT NULL CHECK (apolice_tipo IN ('residencial', 'automovel')),
    cobertura_exigida     VARCHAR NOT NULL,
    antecedencia_horas    INTEGER NOT NULL,
    canal                 VARCHAR NOT NULL,
    versao                INTEGER NOT NULL DEFAULT 1,
    estado                VARCHAR NOT NULL CHECK (estado IN ('ativa', 'substituida')) DEFAULT 'ativa',
    criado_em             TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE eventos_meteorologicos (
    id                  UUID PRIMARY KEY,
    tipo                VARCHAR NOT NULL CHECK (tipo IN ('chuva_intensa', 'granizo')),
    area                VARCHAR NOT NULL,
    periodo_inicio      TIMESTAMP NOT NULL,
    periodo_fim         TIMESTAMP NOT NULL,
    intensidade         DOUBLE NOT NULL,
    proveniencia        VARCHAR NOT NULL CHECK (proveniencia IN ('real_inmet', 'sintetico')),
    instante_observado  TIMESTAMP NOT NULL,
    criado_em           TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE elegibilidades_historicas (
    id             UUID PRIMARY KEY,
    evento_id      UUID NOT NULL REFERENCES eventos_meteorologicos(id),
    regra_id       UUID NOT NULL REFERENCES regras(id),
    segurado_id    UUID NOT NULL REFERENCES segurados(id),
    apolice_id     UUID NOT NULL REFERENCES apolices(id),
    elegivel       BOOLEAN NOT NULL,
    justificativa  VARCHAR NOT NULL,
    criado_em      TIMESTAMP NOT NULL DEFAULT now()
);

-- Casca mínima; os épicos 2 e 3 estendem esta tabela com sua estrutura completa.
CREATE TABLE execucao_preventiva (
    id             UUID PRIMARY KEY,
    estado         VARCHAR NOT NULL,
    versao         INTEGER NOT NULL DEFAULT 1,
    criado_em      TIMESTAMP NOT NULL DEFAULT now(),
    atualizado_em  TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE chaves_idempotencia (
    chave            VARCHAR NOT NULL,
    operacao         VARCHAR NOT NULL,
    hash_requisicao  VARCHAR NOT NULL,
    resposta_status  INTEGER NOT NULL,
    resposta_corpo   VARCHAR NOT NULL,
    criado_em        TIMESTAMP NOT NULL DEFAULT now(),
    PRIMARY KEY (chave, operacao)
);
