"""Testes do executor de migrações versionadas do DuckDB."""

from pathlib import Path

import duckdb
import pytest

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import (
    MIGRACOES,
    ExecutorMigracoes,
    Migracao,
)
from central_preventiva.aplicacao.portas_persistencia import (
    MigracaoFalhou,
    RegistroMigracoesInvalido,
    VersaoSchemaFutura,
)

TABELAS_ESPERADAS = {
    "schema_migracoes",
    "segurados",
    "apolices",
    "regras",
    "eventos_meteorologicos",
    "elegibilidades_historicas",
    "execucao_preventiva",
    "chaves_idempotencia",
    "areas_monitoradas_inmet",
    "sincronizacoes_meteorologicas",
    "tentativas_coleta_meteorologica",
    "excecoes_operacionais",
    "cenarios_sinteticos_ativados",
    "avaliacoes_risco",
    "marcos_execucao",
    "contextos_agente",
}

REGISTRO_MINIMO = (
    "CREATE TABLE schema_migracoes ("
    "versao INTEGER PRIMARY KEY, descricao VARCHAR NOT NULL, "
    "aplicada_em TIMESTAMP NOT NULL DEFAULT now());"
)
MIGRACAO_UM = Migracao(
    versao=1, descricao="base", sql=REGISTRO_MINIMO + "CREATE TABLE base (valor INTEGER);"
)
MIGRACAO_DOIS_VALIDA = Migracao(
    versao=2, descricao="extra", sql="CREATE TABLE extra (valor INTEGER);"
)
MIGRACAO_DOIS_INVALIDA = Migracao(
    versao=2, descricao="extra", sql="CREATE TABLE extra (valor TIPO_INEXISTENTE);"
)


def tabelas(caminho: Path) -> set[str]:
    """Lê os nomes das tabelas presentes no banco indicado."""

    with abrir_conexao(caminho) as conexao:
        return {
            nome
            for (nome,) in conexao.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()
        }


def registros(caminho: Path) -> list[tuple[int, str]]:
    """Lê o par versão/descrição de cada migração registrada."""

    with abrir_conexao(caminho) as conexao:
        return [
            (int(versao), str(descricao))
            for versao, descricao in conexao.execute(
                "SELECT versao, descricao FROM schema_migracoes ORDER BY versao"
            ).fetchall()
        ]


def test_aplica_migracao_inicial_criando_todas_as_tabelas(tmp_path: Path) -> None:
    caminho = tmp_path / "central_preventiva.duckdb"

    resultado = ExecutorMigracoes(caminho).aplicar_pendentes()

    assert resultado.versoes_aplicadas == (1, 2, 3, 4, 5, 6, 7, 8, 9)
    assert resultado.versao_final == 9
    assert tabelas(caminho) == TABELAS_ESPERADAS
    assert registros(caminho) == [
        (1, "schema inicial"),
        (2, "meteorologia"),
        (3, "resiliencia meteorologica"),
        (4, "avaliacao risco"),
        (5, "avaliacao risco sem regra"),
        (6, "elegibilidade"),
        (7, "elegibilidade correcoes"),
        (8, "marcos execucao"),
        (9, "preflight ia"),
    ]


def test_reexecucao_sobre_banco_atual_nao_aplica_nada(tmp_path: Path) -> None:
    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()

    resultado = ExecutorMigracoes(caminho).aplicar_pendentes()

    assert resultado.versoes_aplicadas == ()
    assert resultado.versao_final == 9
    assert registros(caminho) == [
        (1, "schema inicial"),
        (2, "meteorologia"),
        (3, "resiliencia meteorologica"),
        (4, "avaliacao risco"),
        (5, "avaliacao risco sem regra"),
        (6, "elegibilidade"),
        (7, "elegibilidade correcoes"),
        (8, "marcos execucao"),
        (9, "preflight ia"),
    ]


def test_migracao_meteorologia_e_idempotente_sobre_banco_ja_migrado(tmp_path: Path) -> None:
    """AD-007: `areas_monitoradas_inmet`/`sincronizacoes_meteorologicas` aplicam com segurança
    mesmo quando já estão presentes de uma execução anterior (nenhuma mutação duplicada)."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()

    resultado = ExecutorMigracoes(caminho).aplicar_pendentes()

    assert resultado.versoes_aplicadas == ()
    assert {"areas_monitoradas_inmet", "sincronizacoes_meteorologicas"} <= tabelas(caminho)


def test_migracao_resiliencia_preserva_eventos_existentes_e_aplica_unique(
    tmp_path: Path,
) -> None:
    """A migração `0003` recria `eventos_meteorologicos` (AD-015) preservando linhas semeadas
    por migrações anteriores e habilita o insert-or-noop de deduplicação (AD-010)."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho, [MIGRACOES[0], MIGRACOES[1]]).aplicar_pendentes()
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO eventos_meteorologicos "
            "(id, tipo, area, periodo_inicio, periodo_fim, intensidade, proveniencia, "
            "instante_observado) VALUES "
            "('11111111-1111-1111-1111-111111111111', 'chuva_intensa', '9990001', "
            "'2026-08-30 17:00:00', '2026-08-30 18:00:00', 55.4, 'real_inmet', "
            "'2026-08-30 18:00:00')"
        )

    ExecutorMigracoes(caminho).aplicar_pendentes()

    with abrir_conexao(caminho) as conexao:
        linhas = conexao.execute(
            "SELECT id, tipo FROM eventos_meteorologicos"
        ).fetchall()
        assert [(str(id_), tipo) for id_, tipo in linhas] == [
            ("11111111-1111-1111-1111-111111111111", "chuva_intensa")
        ]

        conexao.execute(
            "INSERT INTO eventos_meteorologicos "
            "(id, tipo, area, periodo_inicio, periodo_fim, intensidade, proveniencia, "
            "instante_observado) VALUES "
            "('22222222-2222-2222-2222-222222222222', 'chuva_intensa', '9990001', "
            "'2026-08-30 17:00:00', '2026-08-30 18:00:00', 99.9, 'real_inmet', "
            "'2026-08-30 18:00:00') ON CONFLICT DO NOTHING"
        )
        apos_conflito = conexao.execute(
            "SELECT count(*) FROM eventos_meteorologicos"
        ).fetchone()

    assert apos_conflito == (1,)


def test_migracao_sem_regra_preserva_avaliacoes_e_aceita_regra_nula(tmp_path: Path) -> None:
    """A migração `0005` recria `avaliacoes_risco` (AD-015) preservando linhas existentes
    e relaxa `regra_id`/`regra_versao` para `NULL` (RISCO-09: terminal sem regra ativa)."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho, list(MIGRACOES[:4])).aplicar_pendentes()
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO avaliacoes_risco "
            "(id, execucao_id, evento_id, regra_id, regra_versao, relevante, criterios, "
            "motivo) VALUES "
            "('11111111-1111-1111-1111-111111111111', "
            "'22222222-2222-2222-2222-222222222222', "
            "'33333333-3333-3333-3333-333333333333', "
            "'44444444-4444-4444-4444-444444444444', 1, true, '[]', 'relevante')"
        )

    ExecutorMigracoes(caminho).aplicar_pendentes()

    with abrir_conexao(caminho) as conexao:
        linha = conexao.execute(
            "SELECT id, regra_id, motivo FROM avaliacoes_risco"
        ).fetchone()
        assert linha is not None
        assert str(linha[0]) == "11111111-1111-1111-1111-111111111111"
        assert str(linha[1]) == "44444444-4444-4444-4444-444444444444"
        assert linha[2] == "relevante"

        conexao.execute(
            "INSERT INTO avaliacoes_risco "
            "(id, execucao_id, evento_id, regra_id, regra_versao, relevante, criterios, "
            "motivo) VALUES "
            "('55555555-5555-5555-5555-555555555555', "
            "'66666666-6666-6666-6666-666666666666', "
            "'77777777-7777-7777-7777-777777777777', "
            "NULL, NULL, false, '[]', 'sem_regra_ativa')"
        )
        linha_sem_regra = conexao.execute(
            "SELECT regra_id, regra_versao, motivo FROM avaliacoes_risco "
            "WHERE id = '55555555-5555-5555-5555-555555555555'"
        ).fetchone()

    assert linha_sem_regra == (None, None, "sem_regra_ativa")


def test_migracao_elegibilidade_preserva_linha_semeada_com_backfill_correto(
    tmp_path: Path,
) -> None:
    """A migração `0006` recria `elegibilidades_historicas` (AD-015): a linha semeada
    existente ganha `execucao_id NULL`, `criterios` vazio e `canal` vindo de
    `segurados.canal_preferido` via JOIN (ELEG-04, ELEG-07). A migração `0007` corrige o
    backfill de `criterios` (era um objeto JSON inválido para o parser de critérios,
    achado do Verificador) e acrescenta `nome_segurado` como snapshot (AD-11)."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho, list(MIGRACOES[:5])).aplicar_pendentes()
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO segurados (id, nome, codigo_ibge_area, canal_preferido, "
            "participa_de_alertas) VALUES "
            "('99999999-9999-9999-9999-999999999999', 'Teste', '9990001', 'sms', true)"
        )
        conexao.execute(
            "INSERT INTO elegibilidades_historicas "
            "(id, evento_id, regra_id, segurado_id, apolice_id, elegivel, justificativa) "
            "VALUES ("
            "'11111111-1111-1111-1111-111111111111', "
            "'22222222-2222-2222-2222-222222222222', "
            "'33333333-3333-3333-3333-333333333333', "
            "'99999999-9999-9999-9999-999999999999', "
            "'44444444-4444-4444-4444-444444444444', true, 'seed pré-migração')"
        )

    ExecutorMigracoes(caminho).aplicar_pendentes()

    with abrir_conexao(caminho) as conexao:
        linha = conexao.execute(
            "SELECT execucao_id, criterios, canal, nome_segurado, justificativa "
            "FROM elegibilidades_historicas WHERE id = '11111111-1111-1111-1111-111111111111'"
        ).fetchone()
    assert linha is not None
    assert linha[0] is None
    assert linha[1] == "[]"
    assert linha[2] == "sms"
    assert linha[3] == "Teste"
    assert linha[4] == "seed pré-migração"


def test_migracao_elegibilidade_unique_permite_multiplas_linhas_semeadas_nulas(
    tmp_path: Path,
) -> None:
    """`UNIQUE(execucao_id, ...)` com `execucao_id IS NULL` nunca colide entre linhas
    semeadas (`NULL` é sempre distinto de `NULL`), mas dedup real (`execucao_id`
    preenchido) continua funcionando via `INSERT ... ON CONFLICT DO NOTHING`."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()

    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO segurados (id, nome, codigo_ibge_area, canal_preferido, "
            "participa_de_alertas) VALUES "
            "('99999999-9999-9999-9999-999999999999', 'Teste', '9990001', 'sms', true)"
        )
        # Duas linhas com execucao_id NULL e todos os demais campos idênticos: não colidem.
        for id_linha in (
            "55555555-5555-5555-5555-555555555555",
            "66666666-6666-6666-6666-666666666666",
        ):
            conexao.execute(
                "INSERT INTO elegibilidades_historicas "
                "(id, evento_id, regra_id, segurado_id, apolice_id, elegivel, "
                "criterios, canal, nome_segurado, justificativa) VALUES "
                f"('{id_linha}', "
                "'22222222-2222-2222-2222-222222222222', "
                "'33333333-3333-3333-3333-333333333333', "
                "'99999999-9999-9999-9999-999999999999', "
                "'44444444-4444-4444-4444-444444444444', true, "
                "'[]', 'sms', 'Teste', 'linha nula de teste')"
            )
        total_nulas = conexao.execute(
            "SELECT count(*) FROM elegibilidades_historicas WHERE execucao_id IS NULL "
            "AND evento_id = '22222222-2222-2222-2222-222222222222' "
            "AND segurado_id = '99999999-9999-9999-9999-999999999999'"
        ).fetchone()
        assert total_nulas is not None
        assert total_nulas[0] == 2

        # Mesma combinação real (execucao_id preenchido) duas vezes: a segunda é no-op.
        execucao_id = "77777777-7777-7777-7777-777777777777"
        for id_linha in (
            "88888888-8888-8888-8888-888888888888",
            "89898989-8989-8989-8989-898989898989",
        ):
            conexao.execute(
                "INSERT INTO elegibilidades_historicas "
                "(id, execucao_id, evento_id, regra_id, segurado_id, apolice_id, "
                "elegivel, criterios, canal, nome_segurado, justificativa) VALUES "
                f"('{id_linha}', '{execucao_id}', "
                "'22222222-2222-2222-2222-222222222222', "
                "'33333333-3333-3333-3333-333333333333', "
                "'99999999-9999-9999-9999-999999999999', "
                "'44444444-4444-4444-4444-444444444444', true, "
                "'[]', 'sms', 'Teste', 'linha real de teste') "
                "ON CONFLICT DO NOTHING"
            )
        total_reais = conexao.execute(
            "SELECT count(*) FROM elegibilidades_historicas WHERE execucao_id = ?",
            [execucao_id],
        ).fetchone()
        assert total_reais is not None
        assert total_reais[0] == 1


def test_recusa_versao_registrada_futura_sem_aplicar_mutacao(tmp_path: Path) -> None:
    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho, [MIGRACAO_UM]).aplicar_pendentes()
    with abrir_conexao(caminho) as conexao:
        conexao.execute("INSERT INTO schema_migracoes VALUES (99, 'futura', now())")

    executor = ExecutorMigracoes(caminho, [MIGRACAO_UM, MIGRACAO_DOIS_VALIDA])
    with pytest.raises(VersaoSchemaFutura) as captura:
        executor.aplicar_pendentes()

    assert captura.value.versao_registrada == 99
    assert captura.value.versao_conhecida == 2
    assert "extra" not in tabelas(caminho)
    assert registros(caminho) == [(1, "base"), (99, "futura")]


def test_falha_em_migracao_intermediaria_preserva_as_anteriores(tmp_path: Path) -> None:
    caminho = tmp_path / "central_preventiva.duckdb"
    executor = ExecutorMigracoes(caminho, [MIGRACAO_UM, MIGRACAO_DOIS_INVALIDA])

    with pytest.raises(MigracaoFalhou) as captura:
        executor.aplicar_pendentes()

    assert captura.value.versao == 2
    assert "base" in tabelas(caminho)
    assert "extra" not in tabelas(caminho)
    assert registros(caminho) == [(1, "base")]


def test_retoma_da_primeira_migracao_pendente_apos_correcao(tmp_path: Path) -> None:
    caminho = tmp_path / "central_preventiva.duckdb"
    with pytest.raises(MigracaoFalhou):
        ExecutorMigracoes(caminho, [MIGRACAO_UM, MIGRACAO_DOIS_INVALIDA]).aplicar_pendentes()
    with abrir_conexao(caminho) as conexao:
        conexao.execute("INSERT INTO base VALUES (42)")

    resultado = ExecutorMigracoes(caminho, [MIGRACAO_UM, MIGRACAO_DOIS_VALIDA]).aplicar_pendentes()

    assert resultado.versoes_aplicadas == (2,)
    assert registros(caminho) == [(1, "base"), (2, "extra")]
    with abrir_conexao(caminho) as conexao:
        assert conexao.execute("SELECT valor FROM base").fetchall() == [(42,)]


def test_versao_registrada_e_none_em_banco_ainda_inexistente(tmp_path: Path) -> None:
    assert ExecutorMigracoes(tmp_path / "central_preventiva.duckdb").versao_registrada() is None


def test_recusa_banco_existente_sem_registro_de_migracoes(tmp_path: Path) -> None:
    caminho = tmp_path / "central_preventiva.duckdb"
    with abrir_conexao(caminho) as conexao:
        conexao.execute("CREATE TABLE segurados (id UUID PRIMARY KEY)")

    with pytest.raises(RegistroMigracoesInvalido):
        ExecutorMigracoes(caminho).aplicar_pendentes()

    assert tabelas(caminho) == {"segurados"}


def test_recusa_registro_de_migracoes_corrompido(tmp_path: Path) -> None:
    caminho = tmp_path / "central_preventiva.duckdb"
    with abrir_conexao(caminho) as conexao:
        conexao.execute("CREATE TABLE schema_migracoes (identificador INTEGER)")

    with pytest.raises(RegistroMigracoesInvalido):
        ExecutorMigracoes(caminho).aplicar_pendentes()

    assert tabelas(caminho) == {"schema_migracoes"}


def test_documentacao_versionada_descreve_todas_as_tabelas_criadas() -> None:
    documento = (
        Path("central_preventiva/adaptadores/persistencia/README.md")
        .read_text(encoding="utf-8")
        .lower()
    )

    for tabela in TABELAS_ESPERADAS:
        assert tabela in documento
    for termo in ("chave primária", "chave estrangeira", "restriç", "timestamp", "migraç"):
        assert termo in documento


def test_documentacao_registra_fronteiras_e_exemplos_limitrofes_dos_limiares() -> None:
    """RISCO-02: a documentação explicita, para cada limiar, qual fronteira é inclusiva/
    exclusiva, com exemplos no valor-limite — não só nos testes do motor."""

    documento = Path("central_preventiva/adaptadores/persistencia/README.md").read_text(
        encoding="utf-8"
    )

    assert "inclusiva" in documento.lower()
    assert "nenhuma fronteira exclusiva está configurada" in documento
    for exemplo in ("49.9", "50.0", "50.1"):
        assert exemplo in documento


def test_migracao_marcos_execucao_aceita_causa_nula_e_correlaciona_por_execucao(
    tmp_path: Path,
) -> None:
    """A migração `0008` cria `marcos_execucao`: `causa` é opcional (marco de sucesso não
    tem causa) e vários marcos se correlacionam pelo mesmo `execucao_id` (RUNNER-02)."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    execucao_id = "11111111-1111-1111-1111-111111111111"

    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO execucao_preventiva (id, estado, versao) VALUES (?, 'coletando', 1)",
            [execucao_id],
        )
        conexao.execute(
            "INSERT INTO marcos_execucao (id, execucao_id, marco, causa) VALUES "
            "('22222222-2222-2222-2222-222222222222', ?, 'coleta_concluida', NULL)",
            [execucao_id],
        )
        conexao.execute(
            "INSERT INTO marcos_execucao (id, execucao_id, marco, causa) VALUES "
            "('33333333-3333-3333-3333-333333333333', ?, 'falhou_processamento', "
            "'ValueError: motivo sintético')",
            [execucao_id],
        )
        marcos = conexao.execute(
            "SELECT marco, causa FROM marcos_execucao WHERE execucao_id = ? ORDER BY criado_em",
            [execucao_id],
        ).fetchall()

    assert marcos == [
        ("coleta_concluida", None),
        ("falhou_processamento", "ValueError: motivo sintético"),
    ]


def test_migracoes_versionadas_tem_versoes_unicas_e_ordenadas() -> None:
    versoes = [migracao.versao for migracao in MIGRACOES]

    assert versoes == sorted(set(versoes))
    assert versoes[0] == 1


def test_migracao_preflight_ia_acrescenta_execucao_origem_id_nula_as_execucoes_existentes(
    tmp_path: Path,
) -> None:
    """A migração `0009` acrescenta `execucao_origem_id` a `execucao_preventiva` (PREFL-07):
    coluna nula, sem backfill — toda execução pré-existente permanece intacta com `NULL`, e
    uma execução correlacionada nova aponta para a execução terminal que a originou (AD-009)."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho, list(MIGRACOES[:8])).aplicar_pendentes()
    origem_id = "11111111-1111-1111-1111-111111111111"
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO execucao_preventiva (id, estado, versao) VALUES (?, ?, 1)",
            [origem_id, "falhou_preparacao_ia"],
        )

    ExecutorMigracoes(caminho).aplicar_pendentes()

    with abrir_conexao(caminho) as conexao:
        anterior = conexao.execute(
            "SELECT estado, execucao_origem_id FROM execucao_preventiva WHERE id = ?",
            [origem_id],
        ).fetchone()
        assert anterior == ("falhou_preparacao_ia", None)

        nova_id = "22222222-2222-2222-2222-222222222222"
        conexao.execute(
            "INSERT INTO execucao_preventiva (id, estado, versao, execucao_origem_id) "
            "VALUES (?, ?, 1, ?)",
            [nova_id, "aguardando_geracao", origem_id],
        )
        correlacionada = conexao.execute(
            "SELECT estado, execucao_origem_id FROM execucao_preventiva WHERE id = ?",
            [nova_id],
        ).fetchone()

    assert correlacionada is not None
    assert correlacionada[0] == "aguardando_geracao"
    assert str(correlacionada[1]) == origem_id


def test_migracao_preflight_ia_cria_contextos_agente_com_um_contexto_por_elegibilidade(
    tmp_path: Path,
) -> None:
    """A migração `0009` cria `contextos_agente` com as duas listas de categorias de
    proveniência (PREFL-13) e `UNIQUE (elegibilidade_id)`: um contexto por item elegível —
    a restrição que obriga a nova tentativa a copiar as elegibilidades da origem (AD-012)."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    elegibilidade_id = "33333333-3333-3333-3333-333333333333"

    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO contextos_agente "
            "(id, execucao_id, elegibilidade_id, conteudo, categorias_usadas, "
            "categorias_nao_usadas) VALUES "
            "('44444444-4444-4444-4444-444444444444', "
            "'55555555-5555-5555-5555-555555555555', ?, '{\"canal\": \"sms\"}', "
            "['evento', 'canal'], ['documentos', 'dados_financeiros'])",
            [elegibilidade_id],
        )
        linha = conexao.execute(
            "SELECT conteudo, categorias_usadas, categorias_nao_usadas "
            "FROM contextos_agente WHERE elegibilidade_id = ?",
            [elegibilidade_id],
        ).fetchone()
        assert linha is not None
        assert linha[0] == '{"canal": "sms"}'
        assert list(linha[1]) == ["evento", "canal"]
        assert list(linha[2]) == ["documentos", "dados_financeiros"]

        with pytest.raises(duckdb.ConstraintException):
            conexao.execute(
                "INSERT INTO contextos_agente "
                "(id, execucao_id, elegibilidade_id, conteudo, categorias_usadas, "
                "categorias_nao_usadas) VALUES "
                "('66666666-6666-6666-6666-666666666666', "
                "'77777777-7777-7777-7777-777777777777', ?, '{}', [], [])",
                [elegibilidade_id],
            )


def test_documentacao_versionada_descreve_a_coluna_de_execucao_correlacionada() -> None:
    """A coluna nova de `0009` é documentada junto das tabelas (T2), não só no `.sql`."""

    documento = Path("central_preventiva/adaptadores/persistencia/README.md").read_text(
        encoding="utf-8"
    )

    assert "execucao_origem_id" in documento
    assert "categorias_nao_usadas" in documento
