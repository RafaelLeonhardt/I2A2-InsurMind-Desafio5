-- Migração 11: avaliação crítica de cada versão de mensagem (História 3.3). Uma tabela nova.
--
-- SPEC_DEVIATION: o `design.md` da 3.3 nomeia esta migração `0009_avaliacoes_criticas.sql`.
-- Motivo: `0009` e `0010` já foram consumidos pelas Histórias 3.1 e 3.2, implementadas antes
-- desta. Mesma renumeração já registrada em 2.4, 2.5, 2.6, 3.1 e 3.2 — o conteúdo é o do design.
--
-- `avaliacoes_criticas`: uma linha por versão de mensagem avaliada pelo agente crítico, com a
-- decisão (`aprovada`), os motivos estruturados por categoria fechada (JSON serializado) e a
-- proveniência da chamada (agente, modelo, duração). A avaliação é do conteúdo já validado
-- deterministicamente por 3.2: o crítico nunca revalida campo obrigatório nem limite de canal e
-- nunca sobrepõe a reprovação determinística (CRIT-04, AD-5).
--
-- A restrição `UNIQUE (versao_mensagem_id)` é a dedução de conteúdo do AD-010: uma versão é
-- avaliada uma vez. Com ela, um replay idempotente da geração do lote reaproveita a avaliação já
-- persistida (`INSERT ... ON CONFLICT DO NOTHING` + leitura), sem nova chamada à OpenAI — o
-- terceiro Edge Case da spec.
--
-- Uma saída do crítico inválida ou não interpretável não gera linha nenhuma aqui: ela é falha da
-- tentativa, nunca aprovação e nunca reprovação estruturada (CRIT-07).
--
-- Nenhuma coluna declara `REFERENCES` (AD-005); a relação com `versoes_mensagem(id)` é chave
-- estrangeira lógica, documentada aqui e no `README.md` da persistência. A tabela é nova, então o
-- recreate-and-copy do AD-015 (constraint acrescentada a tabela existente) não se aplica.

CREATE TABLE avaliacoes_criticas (
    id                  UUID PRIMARY KEY,
    versao_mensagem_id  UUID NOT NULL,  -- relaciona-se a versoes_mensagem(id)
    aprovada            BOOLEAN NOT NULL,
    motivos             VARCHAR NOT NULL,
    agente              VARCHAR NOT NULL DEFAULT 'critico',
    modelo              VARCHAR NOT NULL,
    duracao_ms          DOUBLE NOT NULL,
    criado_em           TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE (versao_mensagem_id)
);
