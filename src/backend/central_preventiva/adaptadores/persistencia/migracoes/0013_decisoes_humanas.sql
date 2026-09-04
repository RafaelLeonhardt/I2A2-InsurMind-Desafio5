-- Migração 13: decisão humana sobre cada mensagem do lote (História 3.5). Uma tabela nova.
--
-- SPEC_DEVIATION: o `design.md` da 3.5 nomeia esta migração `0011_decisoes_humanas.sql`.
-- Motivo: `0009`, `0010`, `0011` e `0012` já foram consumidos pelas Histórias 3.1, 3.2, 3.3 e
-- 3.4, implementadas antes desta. Mesma renumeração já registrada desde a 2.4 — o conteúdo é o
-- do design.
--
-- `decisoes_humanas`: uma linha por decisão que Marina toma sobre uma versão de mensagem, com o
-- perfil sintético responsável, o resultado, a justificativa (quando aplicável), a versão
-- decidida e o instante (REVISAO-07). A decisão humana é registrada aqui, e nunca em
-- `avaliacoes_criticas`: a aprovação do agente crítico (3.3) e a decisão de Marina são fatos
-- distintos, de origens distintas, e o lote só é simulável quando as duas concordam (REVISAO-14).
--
-- `justificativa` é obrigatória em `rejeitar`, `excluir` e `regenerar` e opcional em `aprovar`
-- (REVISAO-06). A regra é cobrada pelo próprio banco (`CHECK (resultado = 'aprovar' OR
-- justificativa IS NOT NULL)`), e não apenas pela validação de aplicação, para que nenhum
-- caminho de escrita futuro possa gravar uma rejeição sem motivo.
--
-- Nenhuma restrição `UNIQUE` é declarada, deliberadamente. Uma mensagem recebe legitimamente
-- mais de uma decisão ao longo da vida — regenerar a tentativa 1 e aprovar a tentativa 2 são
-- duas decisões auditáveis da mesma mensagem (REVISAO-11) — então `mensagem_id` não é chave
-- natural. E `versao_mensagem_id` também não vira `UNIQUE`: a dedução do AD-010 existe para
-- fatos que dois comandos independentes podem produzir de novo, com semântica de insert-or-noop;
-- uma segunda decisão sobre a mesma versão não é isso. Ela é impedida pela máquina de estados da
-- mensagem (só `aguardando_revisao` é decidível, REVISAO-12) e o replay do mesmo comando é
-- coberto por `chaves_idempotencia` (AD-002); silenciá-la como no-op esconderia um erro real.
--
-- Nenhuma coluna declara `REFERENCES` (AD-005); as relações com `mensagens(id)` e
-- `versoes_mensagem(id)` são chaves estrangeiras lógicas, documentadas aqui e no `README.md` da
-- persistência. A tabela é nova, então o recreate-and-copy do AD-015 (constraint acrescentada a
-- tabela existente) não se aplica.

CREATE TABLE decisoes_humanas (
    id                  UUID PRIMARY KEY,
    mensagem_id         UUID NOT NULL,  -- relaciona-se a mensagens(id)
    versao_mensagem_id  UUID NOT NULL,  -- relaciona-se a versoes_mensagem(id)
    perfil_responsavel  VARCHAR NOT NULL,
    resultado           VARCHAR NOT NULL
                        CHECK (resultado IN ('aprovar', 'rejeitar', 'excluir', 'regenerar')),
    justificativa       VARCHAR,
    criado_em           TIMESTAMP NOT NULL DEFAULT now(),
    CHECK (resultado = 'aprovar' OR justificativa IS NOT NULL)
);
