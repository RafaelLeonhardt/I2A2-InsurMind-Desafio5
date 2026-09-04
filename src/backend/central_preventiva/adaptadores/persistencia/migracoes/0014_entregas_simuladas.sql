-- Migração 14: entrega simulada por mensagem e canal (História 3.6). Uma tabela nova.
--
-- SPEC_DEVIATION: o `design.md` da 3.6 nomeia esta migração `0012_entregas_simuladas.sql`.
-- Motivo: `0009`–`0013` já foram consumidos pelas Histórias 3.1–3.5, implementadas antes desta.
-- Mesma renumeração já registrada desde a 2.4 — o conteúdo é o do design.
--
-- `entregas_simuladas`: uma linha por mensagem aprovada que a simulação local apresentou em seu
-- canal (SIMUL-05). Nenhum conector real de WhatsApp, e-mail ou SMS participa disso: a
-- `apresentacao` é uma cópia exata do `conteudo` da versão aprovada em `versoes_mensagem` (3.2),
-- serializada no mesmo formato (`{corpo}` ou `{assunto, corpo}`). A tabela não tem coluna de
-- confirmação nem de falha de provedor externo, deliberadamente: a simulação nunca inventa um
-- desfecho de canal que não existiu (SIMUL-06, ADR-0009/0013).
--
-- `UNIQUE (mensagem_id)` é a dedução de conteúdo do AD-010: uma mensagem tem no máximo uma
-- entrega simulada, e uma segunda confirmação do mesmo lote é recusada pelo próprio banco em vez
-- de duplicar a simulação (SIMUL-07, SIMUL-08). A `UNIQUE` fica no par natural — a mensagem, que
-- já carrega seu canal — e não em `(execucao_id, mensagem_id)`: uma mensagem pertence a uma única
-- execução, então incluir a execução afrouxaria a dedução sem ganho nenhum.
--
-- Nenhuma coluna declara `REFERENCES` (AD-005); as relações com `execucao_preventiva(id)` e
-- `mensagens(id)` são chaves estrangeiras lógicas, documentadas aqui e no `README.md` da
-- persistência. A tabela é nova, então o recreate-and-copy do AD-015 (constraint acrescentada a
-- tabela existente) não se aplica.

CREATE TABLE entregas_simuladas (
    id            UUID PRIMARY KEY,
    execucao_id   UUID NOT NULL,  -- relaciona-se a execucao_preventiva(id)
    mensagem_id   UUID NOT NULL UNIQUE,  -- relaciona-se a mensagens(id)
    canal         VARCHAR NOT NULL CHECK (canal IN ('whatsapp', 'email', 'sms')),
    apresentacao  VARCHAR NOT NULL,
    criado_em     TIMESTAMP NOT NULL DEFAULT now()
);
