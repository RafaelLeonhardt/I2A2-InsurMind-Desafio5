-- Migração 8: cria `marcos_execucao`, o histórico de transições correlacionadas de uma
-- execução preventiva (RUNNER-02, AD-10). O `GerenciadorExecucoes` (2.6) grava um marco a
-- cada transição de estado — coleta concluída, avaliação de risco concluída, público
-- elegível formado, ou o próprio nome do estado terminal alcançado — para que a
-- reidratação (RUNNER-07) reconstrua exatamente o que aconteceu, sem recalcular nada.

CREATE TABLE marcos_execucao (
    id            UUID PRIMARY KEY,
    execucao_id   UUID NOT NULL,  -- relaciona-se a execucao_preventiva(id)
    marco         VARCHAR NOT NULL,
    causa         VARCHAR,        -- nulo quando não aplicável (marco de sucesso, não de falha)
    criado_em     TIMESTAMP NOT NULL DEFAULT now()
);
