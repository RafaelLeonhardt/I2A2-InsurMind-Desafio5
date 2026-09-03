-- Migração 10: mensagens preventivas geradas por canal (História 3.2). Duas tabelas novas.
--
-- SPEC_DEVIATION: o `design.md` da 3.2 nomeia esta migração `0008_mensagens.sql`.
-- Motivo: `0008` e `0009` já foram consumidos pelas Histórias 2.6 e 3.1, implementadas antes
-- desta. Mesma renumeração já registrada em 2.4, 2.5, 2.6 e 3.1 — o conteúdo é o do design.
--
-- 1. `mensagens`: uma mensagem por combinação elegibilidade+canal, com o estado de conteúdo do
--    segundo diagrama do AD-4 (`gerando` → `criticando` → ...), a tentativa reservada na entrada
--    em `gerando` e a coluna `versao` de concorrência otimista (AD-008). A restrição
--    `UNIQUE (elegibilidade_id, canal)` é a dedução de conteúdo do AD-010: com ela, reinvocar a
--    geração de um lote já processado é no-op (`ON CONFLICT DO NOTHING`), nunca uma duplicata
--    (GERAR-06, GERAR-11, GERAR-12).
--
-- 2. `versoes_mensagem`: uma linha por tentativa de geração, com o conteúdo estruturado
--    serializado, o veredito determinístico do `ValidadorSaidaCanal` (`valida` +
--    `motivo_invalidez`) e as métricas da chamada (duração, modelo, versão de prompt, tokens).
--    Uma versão inválida fica registrada com o motivo, e a mensagem permanece em `gerando`
--    (GERAR-09) — a política de regeneração é da História 3.4, não desta.
--
-- Nenhuma coluna declara `REFERENCES` (AD-005); as relações são chaves estrangeiras lógicas,
-- documentadas aqui e no `README.md` da persistência. Ambas as tabelas são novas, então o
-- recreate-and-copy do AD-015 (constraint acrescentada a tabela existente) não se aplica.

CREATE TABLE mensagens (
    id                UUID PRIMARY KEY,
    execucao_id       UUID NOT NULL,  -- relaciona-se a execucao_preventiva(id)
    elegibilidade_id  UUID NOT NULL,  -- relaciona-se a elegibilidades_historicas(id)
    canal             VARCHAR NOT NULL CHECK (canal IN ('whatsapp', 'email', 'sms')),
    estado            VARCHAR NOT NULL,
    tentativa_atual   INTEGER NOT NULL DEFAULT 1 CHECK (tentativa_atual BETWEEN 1 AND 3),
    versao            INTEGER NOT NULL DEFAULT 1,
    criado_em         TIMESTAMP NOT NULL DEFAULT now(),
    atualizado_em     TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (elegibilidade_id, canal)
);

CREATE TABLE versoes_mensagem (
    id                UUID PRIMARY KEY,
    mensagem_id       UUID NOT NULL,  -- relaciona-se a mensagens(id)
    numero_tentativa  INTEGER NOT NULL,
    conteudo          VARCHAR NOT NULL,
    valida            BOOLEAN NOT NULL,
    motivo_invalidez  VARCHAR,
    duracao_ms        DOUBLE NOT NULL,
    modelo            VARCHAR NOT NULL,
    versao_prompt     VARCHAR NOT NULL,
    tokens_entrada    INTEGER,
    tokens_saida      INTEGER,
    criado_em         TIMESTAMP NOT NULL DEFAULT now()
);
