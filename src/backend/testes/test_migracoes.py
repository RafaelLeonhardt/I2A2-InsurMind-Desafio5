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
    "mensagens",
    "versoes_mensagem",
    "avaliacoes_criticas",
    "decisoes_humanas",
    "entregas_simuladas",
    "visualizacoes_comunicado",
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

    assert resultado.versoes_aplicadas == (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15)
    assert resultado.versao_final == 15
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
        (10, "mensagens"),
        (11, "avaliacoes criticas"),
        (12, "excecoes mensagem"),
        (13, "decisoes humanas"),
        (14, "entregas simuladas"),
        (15, "visualizacoes comunicado"),
    ]


def test_reexecucao_sobre_banco_atual_nao_aplica_nada(tmp_path: Path) -> None:
    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()

    resultado = ExecutorMigracoes(caminho).aplicar_pendentes()

    assert resultado.versoes_aplicadas == ()
    assert resultado.versao_final == 15
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
        (10, "mensagens"),
        (11, "avaliacoes criticas"),
        (12, "excecoes mensagem"),
        (13, "decisoes humanas"),
        (14, "entregas simuladas"),
        (15, "visualizacoes comunicado"),
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


def _inserir_mensagem(
    conexao: duckdb.DuckDBPyConnection,
    id_mensagem: str,
    elegibilidade_id: str,
    canal: str,
    *,
    ignorar_conflito: bool = False,
) -> None:
    """Insere uma mensagem em `gerando`, opcionalmente como insert-or-noop (AD-010)."""

    conexao.execute(
        "INSERT INTO mensagens "
        "(id, execucao_id, elegibilidade_id, canal, estado) VALUES (?, ?, ?, ?, 'gerando')"
        + (" ON CONFLICT DO NOTHING" if ignorar_conflito else ""),
        [id_mensagem, "55555555-5555-5555-5555-555555555555", elegibilidade_id, canal],
    )


def test_migracao_mensagens_impede_segunda_mensagem_para_mesma_elegibilidade_e_canal(
    tmp_path: Path,
) -> None:
    """A migração `0010` cria `mensagens` com `UNIQUE (elegibilidade_id, canal)` (GERAR-06):
    a mesma combinação não admite uma segunda mensagem, mas o mesmo item em outro canal e
    outro item no mesmo canal continuam permitidos."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    elegibilidade = "11111111-1111-1111-1111-111111111111"
    outra_elegibilidade = "22222222-2222-2222-2222-222222222222"

    with abrir_conexao(caminho) as conexao:
        _inserir_mensagem(conexao, "aaaaaaaa-0000-0000-0000-000000000001", elegibilidade, "sms")

        with pytest.raises(duckdb.ConstraintException):
            _inserir_mensagem(
                conexao, "aaaaaaaa-0000-0000-0000-000000000002", elegibilidade, "sms"
            )

        _inserir_mensagem(
            conexao, "aaaaaaaa-0000-0000-0000-000000000003", elegibilidade, "whatsapp"
        )
        _inserir_mensagem(
            conexao, "aaaaaaaa-0000-0000-0000-000000000004", outra_elegibilidade, "sms"
        )
        total = conexao.execute("SELECT count(*) FROM mensagens").fetchone()

    assert total == (3,)


def test_migracao_mensagens_torna_reinvocacao_do_lote_um_no_op(tmp_path: Path) -> None:
    """`INSERT ... ON CONFLICT DO NOTHING` sobre `UNIQUE (elegibilidade_id, canal)` é o que
    torna reinvocar `gerar_lote` para uma execução já processada um no-op, sem duplicar
    mensagem (GERAR-11, GERAR-12, AD-010)."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    elegibilidade = "33333333-3333-3333-3333-333333333333"

    with abrir_conexao(caminho) as conexao:
        _inserir_mensagem(
            conexao, "bbbbbbbb-0000-0000-0000-000000000001", elegibilidade, "email"
        )
        _inserir_mensagem(
            conexao,
            "bbbbbbbb-0000-0000-0000-000000000002",
            elegibilidade,
            "email",
            ignorar_conflito=True,
        )
        linhas = conexao.execute("SELECT id FROM mensagens WHERE elegibilidade_id = ?", [
            elegibilidade
        ]).fetchall()

    assert [str(id_) for (id_,) in linhas] == ["bbbbbbbb-0000-0000-0000-000000000001"]


def test_migracao_mensagens_cria_versoes_com_motivo_de_invalidez_e_tokens_opcionais(
    tmp_path: Path,
) -> None:
    """A migração `0010` cria `versoes_mensagem` com o veredito determinístico da versão:
    `motivo_invalidez` preenchido quando `valida = false` e nulo quando a versão é válida;
    `tokens_entrada`/`tokens_saida` são opcionais (GERAR-09, GERAR-10)."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    mensagem_id = "cccccccc-0000-0000-0000-000000000001"

    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO versoes_mensagem "
            "(id, mensagem_id, numero_tentativa, conteudo, valida, motivo_invalidez, "
            "duracao_ms, modelo, versao_prompt, tokens_entrada, tokens_saida) VALUES "
            "('dddddddd-0000-0000-0000-000000000001', ?, 1, '{\"corpo\": \"...\"}', false, "
            "'corpo acima do limite de 160 caracteres do canal sms', 12.5, 'gpt-4o-mini', "
            "'v1', NULL, NULL)",
            [mensagem_id],
        )
        conexao.execute(
            "INSERT INTO versoes_mensagem "
            "(id, mensagem_id, numero_tentativa, conteudo, valida, motivo_invalidez, "
            "duracao_ms, modelo, versao_prompt, tokens_entrada, tokens_saida) VALUES "
            "('dddddddd-0000-0000-0000-000000000002', ?, 1, '{\"corpo\": \"ok\"}', true, "
            "NULL, 34.0, 'gpt-4o-mini', 'v1', 120, 45)",
            [mensagem_id],
        )
        linhas = conexao.execute(
            "SELECT valida, motivo_invalidez, duracao_ms, modelo, versao_prompt, "
            "tokens_entrada, tokens_saida FROM versoes_mensagem WHERE mensagem_id = ? "
            "ORDER BY id",
            [mensagem_id],
        ).fetchall()

    assert linhas == [
        (
            False,
            "corpo acima do limite de 160 caracteres do canal sms",
            12.5,
            "gpt-4o-mini",
            "v1",
            None,
            None,
        ),
        (True, None, 34.0, "gpt-4o-mini", "v1", 120, 45),
    ]


def test_migracao_avaliacoes_criticas_admite_uma_unica_avaliacao_por_versao(
    tmp_path: Path,
) -> None:
    """A migração `0011` cria `avaliacoes_criticas` com `UNIQUE (versao_mensagem_id)`
    (CRIT-06): a mesma versão de mensagem não admite uma segunda avaliação, mas outra
    versão continua podendo ser avaliada."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    versao = "11111111-1111-1111-1111-111111111111"
    outra_versao = "22222222-2222-2222-2222-222222222222"

    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO avaliacoes_criticas "
            "(id, versao_mensagem_id, aprovada, motivos, modelo, duracao_ms) VALUES "
            "('aaaaaaaa-0000-0000-0000-000000000001', ?, true, '[]', 'gpt-4o-mini', 12.5)",
            [versao],
        )

        with pytest.raises(duckdb.ConstraintException):
            conexao.execute(
                "INSERT INTO avaliacoes_criticas "
                "(id, versao_mensagem_id, aprovada, motivos, modelo, duracao_ms) VALUES "
                "('aaaaaaaa-0000-0000-0000-000000000002', ?, false, '[]', 'gpt-4o-mini', 9.0)",
                [versao],
            )

        conexao.execute(
            "INSERT INTO avaliacoes_criticas "
            "(id, versao_mensagem_id, aprovada, motivos, modelo, duracao_ms) VALUES "
            "('aaaaaaaa-0000-0000-0000-000000000003', ?, false, '[]', 'gpt-4o-mini', 9.0)",
            [outra_versao],
        )
        total = conexao.execute("SELECT count(*) FROM avaliacoes_criticas").fetchone()

    assert total == (2,)


def test_migracao_avaliacoes_criticas_torna_reavaliacao_da_versao_um_no_op(
    tmp_path: Path,
) -> None:
    """Terceiro Edge Case da 3.3: `INSERT ... ON CONFLICT DO NOTHING` sobre
    `UNIQUE (versao_mensagem_id)` é o que faz um replay reaproveitar a avaliação já
    persistida, em vez de gravar uma segunda (AD-010)."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    versao = "33333333-3333-3333-3333-333333333333"

    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO avaliacoes_criticas "
            "(id, versao_mensagem_id, aprovada, motivos, modelo, duracao_ms) VALUES "
            "('bbbbbbbb-0000-0000-0000-000000000001', ?, false, "
            "'[{\"categoria\": \"tom\", \"justificativa\": \"Tom alarmista.\"}]', "
            "'gpt-4o-mini', 20.0)",
            [versao],
        )
        conexao.execute(
            "INSERT INTO avaliacoes_criticas "
            "(id, versao_mensagem_id, aprovada, motivos, modelo, duracao_ms) VALUES "
            "('bbbbbbbb-0000-0000-0000-000000000002', ?, true, '[]', 'gpt-4o-mini', 5.0) "
            "ON CONFLICT DO NOTHING",
            [versao],
        )
        linhas = conexao.execute(
            "SELECT id, aprovada, motivos, agente FROM avaliacoes_criticas "
            "WHERE versao_mensagem_id = ?",
            [versao],
        ).fetchall()

    assert [(str(id_), aprovada, motivos, agente) for id_, aprovada, motivos, agente in linhas] == [
        (
            "bbbbbbbb-0000-0000-0000-000000000001",
            False,
            '[{"categoria": "tom", "justificativa": "Tom alarmista."}]',
            "critico",
        )
    ]


def test_documentacao_versionada_descreve_a_tabela_de_avaliacao_critica() -> None:
    """A tabela de `0011` e a restrição que garante uma avaliação por versão são
    documentadas no `README.md` versionado, não só no `.sql` (T1)."""

    documento = Path("central_preventiva/adaptadores/persistencia/README.md").read_text(
        encoding="utf-8"
    )

    assert "avaliacoes_criticas" in documento
    assert "UNIQUE (versao_mensagem_id)" in documento
    assert "promessa_indevida" in documento
    assert "distincao_oficial" in documento


def test_documentacao_versionada_descreve_as_tabelas_de_mensagem() -> None:
    """As tabelas de `0010` e a restrição que garante a unicidade por item+canal são
    documentadas no `README.md` versionado, não só no `.sql` (T1)."""

    documento = Path("central_preventiva/adaptadores/persistencia/README.md").read_text(
        encoding="utf-8"
    )

    assert "UNIQUE (elegibilidade_id, canal)" in documento
    assert "motivo_invalidez" in documento
    assert "tentativa_atual" in documento


def test_migracao_excecoes_mensagem_acrescenta_mensagem_id_nula_as_excecoes_existentes(
    tmp_path: Path,
) -> None:
    """A migração `0012` acrescenta `mensagem_id` a `excecoes_operacionais` (REGEN-04):
    coluna nula, sem backfill — toda exceção de execução pré-existente permanece intacta com
    `NULL`, e uma exceção nova de uma mensagem específica correlaciona-se por `mensagem_id`."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho, list(MIGRACOES[:11])).aplicar_pendentes()
    execucao_id = "11111111-1111-1111-1111-111111111111"
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO excecoes_operacionais (id, execucao_id, causa, tentativas, impacto) "
            "VALUES ('22222222-2222-2222-2222-222222222222', ?, 'coleta esgotada', 3, "
            "'Nenhum evento foi coletado.')",
            [execucao_id],
        )

    ExecutorMigracoes(caminho).aplicar_pendentes()

    with abrir_conexao(caminho) as conexao:
        anterior = conexao.execute(
            "SELECT causa, tentativas, impacto, mensagem_id FROM excecoes_operacionais "
            "WHERE id = '22222222-2222-2222-2222-222222222222'"
        ).fetchone()
        assert anterior == ("coleta esgotada", 3, "Nenhum evento foi coletado.", None)

        mensagem_id = "33333333-3333-3333-3333-333333333333"
        conexao.execute(
            "INSERT INTO excecoes_operacionais "
            "(id, execucao_id, causa, tentativas, impacto, mensagem_id) VALUES "
            "('44444444-4444-4444-4444-444444444444', ?, 'falhou_conteudo', 3, "
            "'Este item não integra o lote simulável.', ?)",
            [execucao_id, mensagem_id],
        )
        de_mensagem = conexao.execute(
            "SELECT causa, tentativas, mensagem_id FROM excecoes_operacionais "
            "WHERE id = '44444444-4444-4444-4444-444444444444'"
        ).fetchone()

    assert de_mensagem is not None
    assert de_mensagem[0] == "falhou_conteudo"
    assert de_mensagem[1] == 3
    assert str(de_mensagem[2]) == mensagem_id


def test_migracao_excecoes_mensagem_distingue_excecao_de_execucao_e_de_mensagem(
    tmp_path: Path,
) -> None:
    """REGEN-04: com a coluna nova, a exceção de uma mensagem específica é filtrável à parte
    da exceção da execução inteira — o motivo de reusar `excecoes_operacionais` em vez de
    criar uma tabela paralela."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    execucao_id = "55555555-5555-5555-5555-555555555555"
    mensagem_id = "66666666-6666-6666-6666-666666666666"

    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO excecoes_operacionais (id, execucao_id, causa, tentativas, impacto) "
            "VALUES ('77777777-7777-7777-7777-777777777777', ?, 'falhou_coleta', 3, 'x')",
            [execucao_id],
        )
        conexao.execute(
            "INSERT INTO excecoes_operacionais "
            "(id, execucao_id, causa, tentativas, impacto, mensagem_id) VALUES "
            "('88888888-8888-8888-8888-888888888888', ?, 'falhou_conteudo', 3, 'y', ?)",
            [execucao_id, mensagem_id],
        )
        da_mensagem = conexao.execute(
            "SELECT causa FROM excecoes_operacionais WHERE mensagem_id = ?", [mensagem_id]
        ).fetchall()
        da_execucao = conexao.execute(
            "SELECT causa FROM excecoes_operacionais "
            "WHERE execucao_id = ? AND mensagem_id IS NULL",
            [execucao_id],
        ).fetchall()

    assert [causa for (causa,) in da_mensagem] == ["falhou_conteudo"]
    assert [causa for (causa,) in da_execucao] == ["falhou_coleta"]


def test_documentacao_versionada_descreve_a_coluna_de_excecao_de_mensagem() -> None:
    """A coluna nova de `0012` é documentada junto das tabelas (T1), não só no `.sql`."""

    documento = Path("central_preventiva/adaptadores/persistencia/README.md").read_text(
        encoding="utf-8"
    )

    assert "0012_excecoes_mensagem" in documento
    assert "`mensagem_id` | `UUID` | nulo, chave estrangeira lógica para `mensagens(id)`" in (
        documento
    )


def _inserir_decisao(
    conexao: duckdb.DuckDBPyConnection,
    id_decisao: str,
    resultado: str,
    justificativa: str | None,
    *,
    mensagem_id: str = "11111111-1111-1111-1111-111111111111",
    versao_mensagem_id: str = "22222222-2222-2222-2222-222222222222",
) -> None:
    """Insere uma decisão humana sobre uma versão de mensagem (REVISAO-07)."""

    conexao.execute(
        "INSERT INTO decisoes_humanas "
        "(id, mensagem_id, versao_mensagem_id, perfil_responsavel, resultado, justificativa) "
        "VALUES (?, ?, ?, 'Administrador', ?, ?)",
        [id_decisao, mensagem_id, versao_mensagem_id, resultado, justificativa],
    )


def test_migracao_decisoes_humanas_persiste_perfil_resultado_e_versao_decidida(
    tmp_path: Path,
) -> None:
    """A migração `0013` cria `decisoes_humanas` com perfil sintético responsável, data,
    resultado, justificativa e versão da mensagem decidida (REVISAO-07)."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()

    with abrir_conexao(caminho) as conexao:
        _inserir_decisao(
            conexao,
            "aaaaaaaa-0000-0000-0000-000000000001",
            "rejeitar",
            "O texto não deixa claro que o aviso é da seguradora.",
        )
        linha = conexao.execute(
            "SELECT mensagem_id, versao_mensagem_id, perfil_responsavel, resultado, "
            "justificativa, criado_em FROM decisoes_humanas "
            "WHERE id = 'aaaaaaaa-0000-0000-0000-000000000001'"
        ).fetchone()

    assert linha is not None
    assert str(linha[0]) == "11111111-1111-1111-1111-111111111111"
    assert str(linha[1]) == "22222222-2222-2222-2222-222222222222"
    assert linha[2] == "Administrador"
    assert linha[3] == "rejeitar"
    assert linha[4] == "O texto não deixa claro que o aviso é da seguradora."
    assert linha[5] is not None


def test_migracao_decisoes_humanas_recusa_resultado_fora_do_conjunto_fechado(
    tmp_path: Path,
) -> None:
    """REVISAO-05: os quatro resultados possíveis são fechados no schema — nenhuma decisão
    de "editar o texto" tem sequer como ser gravada."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()

    with abrir_conexao(caminho) as conexao:
        for indice, resultado in enumerate(("aprovar", "rejeitar", "excluir", "regenerar")):
            _inserir_decisao(
                conexao,
                f"bbbbbbbb-0000-0000-0000-00000000000{indice}",
                resultado,
                "Motivo suficiente para a decisão.",
            )

        with pytest.raises(duckdb.ConstraintException):
            _inserir_decisao(
                conexao,
                "bbbbbbbb-0000-0000-0000-000000000009",
                "editar",
                "Reescrevi o texto na mão.",
            )
        total = conexao.execute("SELECT count(*) FROM decisoes_humanas").fetchone()

    assert total == (4,)


def test_migracao_decisoes_humanas_exige_justificativa_exceto_na_aprovacao(
    tmp_path: Path,
) -> None:
    """REVISAO-06: rejeitar, excluir e regenerar sem justificativa são recusados pelo próprio
    banco; só `aprovar` admite justificativa nula."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()

    with abrir_conexao(caminho) as conexao:
        for indice, resultado in enumerate(("rejeitar", "excluir", "regenerar")):
            with pytest.raises(duckdb.ConstraintException):
                _inserir_decisao(
                    conexao,
                    f"cccccccc-0000-0000-0000-00000000000{indice}",
                    resultado,
                    None,
                )

        _inserir_decisao(
            conexao, "cccccccc-0000-0000-0000-000000000009", "aprovar", None
        )
        linhas = conexao.execute(
            "SELECT resultado, justificativa FROM decisoes_humanas"
        ).fetchall()

    assert linhas == [("aprovar", None)]


def test_migracao_decisoes_humanas_admite_varias_decisoes_da_mesma_mensagem(
    tmp_path: Path,
) -> None:
    """REVISAO-11: a solicitação humana de regeneração e a decisão sobre a versão seguinte
    coexistem como histórico auditável da mesma mensagem — nenhuma `UNIQUE` as impede."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    mensagem_id = "33333333-3333-3333-3333-333333333333"

    with abrir_conexao(caminho) as conexao:
        _inserir_decisao(
            conexao,
            "dddddddd-0000-0000-0000-000000000001",
            "regenerar",
            "O texto está longo demais para SMS.",
            mensagem_id=mensagem_id,
            versao_mensagem_id="44444444-4444-4444-4444-444444444444",
        )
        _inserir_decisao(
            conexao,
            "dddddddd-0000-0000-0000-000000000002",
            "aprovar",
            None,
            mensagem_id=mensagem_id,
            versao_mensagem_id="55555555-5555-5555-5555-555555555555",
        )
        linhas = conexao.execute(
            "SELECT resultado, versao_mensagem_id FROM decisoes_humanas "
            "WHERE mensagem_id = ? ORDER BY id",
            [mensagem_id],
        ).fetchall()

    assert [
        (resultado, str(versao_id)) for resultado, versao_id in linhas
    ] == [
        ("regenerar", "44444444-4444-4444-4444-444444444444"),
        ("aprovar", "55555555-5555-5555-5555-555555555555"),
    ]


def test_documentacao_versionada_descreve_a_tabela_de_decisao_humana() -> None:
    """A tabela de `0013` é documentada no `README.md` versionado, não só no `.sql` (T1)."""

    documento = Path("central_preventiva/adaptadores/persistencia/README.md").read_text(
        encoding="utf-8"
    )

    assert "0013_decisoes_humanas" in documento
    assert "decisoes_humanas" in documento
    assert "CHECK (resultado = 'aprovar' OR justificativa IS NOT NULL)" in documento
    assert "perfil_responsavel" in documento


APRESENTACAO_SMS = '{"corpo": "Chuva forte hoje na sua regiao. Evite areas alagadas."}'
MENSAGEM_SIMULADA_ID = "66666666-6666-6666-6666-666666666666"
EXECUCAO_SIMULADA_ID = "77777777-7777-7777-7777-777777777777"


def _inserir_entrega_simulada(
    conexao: duckdb.DuckDBPyConnection,
    id_entrega: str,
    canal: str = "sms",
    *,
    mensagem_id: str = MENSAGEM_SIMULADA_ID,
    apresentacao: str = APRESENTACAO_SMS,
) -> None:
    """Insere uma entrega simulada de uma mensagem aprovada (SIMUL-05)."""

    conexao.execute(
        "INSERT INTO entregas_simuladas "
        "(id, execucao_id, mensagem_id, canal, apresentacao) VALUES (?, ?, ?, ?, ?)",
        [id_entrega, EXECUCAO_SIMULADA_ID, mensagem_id, canal, apresentacao],
    )


def test_migracao_entregas_simuladas_persiste_execucao_mensagem_canal_e_apresentacao(
    tmp_path: Path,
) -> None:
    """A migração `0014` cria `entregas_simuladas` com a execução, a mensagem, o canal e a
    apresentação copiada do conteúdo já aprovado (SIMUL-05)."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()

    with abrir_conexao(caminho) as conexao:
        _inserir_entrega_simulada(conexao, "eeeeeeee-0000-0000-0000-000000000001")
        linha = conexao.execute(
            "SELECT execucao_id, mensagem_id, canal, apresentacao, criado_em "
            "FROM entregas_simuladas WHERE id = 'eeeeeeee-0000-0000-0000-000000000001'"
        ).fetchone()

    assert linha is not None
    assert str(linha[0]) == EXECUCAO_SIMULADA_ID
    assert str(linha[1]) == MENSAGEM_SIMULADA_ID
    assert linha[2] == "sms"
    assert linha[3] == APRESENTACAO_SMS
    assert linha[4] is not None


def test_migracao_entregas_simuladas_recusa_segunda_entrega_da_mesma_mensagem(
    tmp_path: Path,
) -> None:
    """SIMUL-07/SIMUL-08: a `UNIQUE (mensagem_id)` (AD-010) impede que uma segunda confirmação
    crie uma segunda entrega para a mesma mensagem."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()

    with abrir_conexao(caminho) as conexao:
        _inserir_entrega_simulada(conexao, "eeeeeeee-0000-0000-0000-000000000002")

        with pytest.raises(duckdb.ConstraintException):
            _inserir_entrega_simulada(conexao, "eeeeeeee-0000-0000-0000-000000000003")
        total = conexao.execute(
            "SELECT count(*) FROM entregas_simuladas WHERE mensagem_id = ?",
            [MENSAGEM_SIMULADA_ID],
        ).fetchone()

    assert total == (1,)


def test_migracao_entregas_simuladas_recusa_canal_fora_do_conjunto_fechado(
    tmp_path: Path,
) -> None:
    """SIMUL-05: os três canais são fechados no schema; nenhum canal inventado tem como ser
    gravado como entrega simulada."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()

    with abrir_conexao(caminho) as conexao:
        for indice, canal in enumerate(("whatsapp", "email", "sms")):
            _inserir_entrega_simulada(
                conexao,
                f"ffffffff-0000-0000-0000-00000000000{indice}",
                canal,
                mensagem_id=f"88888888-8888-8888-8888-88888888800{indice}",
            )

        with pytest.raises(duckdb.ConstraintException):
            _inserir_entrega_simulada(
                conexao,
                "ffffffff-0000-0000-0000-000000000009",
                "pombo_correio",
                mensagem_id="88888888-8888-8888-8888-888888888009",
            )
        canais = conexao.execute(
            "SELECT canal FROM entregas_simuladas ORDER BY canal"
        ).fetchall()

    assert canais == [("email",), ("sms",), ("whatsapp",)]


def test_migracao_entregas_simuladas_nao_tem_coluna_de_desfecho_de_provedor(
    tmp_path: Path,
) -> None:
    """SIMUL-06: a tabela não guarda confirmação nem falha de provedor externo — não existe
    coluna onde inventá-las, porque nenhum conector real é invocado."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()

    with abrir_conexao(caminho) as conexao:
        colunas = {
            nome
            for (nome,) in conexao.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'main' AND table_name = 'entregas_simuladas'"
            ).fetchall()
        }

    assert colunas == {
        "id",
        "execucao_id",
        "mensagem_id",
        "canal",
        "apresentacao",
        "criado_em",
    }


def test_documentacao_versionada_descreve_a_tabela_de_entrega_simulada() -> None:
    """A tabela de `0014` é documentada no `README.md` versionado, não só no `.sql` (T1)."""

    documento = Path("central_preventiva/adaptadores/persistencia/README.md").read_text(
        encoding="utf-8"
    )

    assert "0014_entregas_simuladas" in documento
    assert "entregas_simuladas" in documento
    assert "`NOT NULL`, `UNIQUE`, chave estrangeira lógica para `mensagens(id)`" in documento
    assert "`CHECK` em `whatsapp`, `email`, `sms`" in documento


ENTREGA_SIMULADA_VISUALIZAVEL_ID = "99999999-0000-0000-0000-000000000001"
SEGURADO_VISUALIZADOR_ID = "aaaaaaaa-0000-0000-0000-000000000001"


def _inserir_visualizacao(
    conexao: duckdb.DuckDBPyConnection,
    id_visualizacao: str,
    *,
    entrega_simulada_id: str = ENTREGA_SIMULADA_VISUALIZAVEL_ID,
    segurado_id: str = SEGURADO_VISUALIZADOR_ID,
) -> None:
    """Insere a primeira visualização de um comunicado (VISU-01)."""

    conexao.execute(
        "INSERT INTO visualizacoes_comunicado (id, entrega_simulada_id, segurado_id) "
        "VALUES (?, ?, ?)",
        [id_visualizacao, entrega_simulada_id, segurado_id],
    )


def test_migracao_visualizacoes_persiste_entrega_segurado_e_data_hora(tmp_path: Path) -> None:
    """A migração `0015` cria `visualizacoes_comunicado` com a entrega, o segurado e a
    data/hora UTC da primeira visualização (VISU-01)."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()

    with abrir_conexao(caminho) as conexao:
        _inserir_visualizacao(conexao, "bbbbbbbb-0000-0000-0000-000000000001")
        linha = conexao.execute(
            "SELECT entrega_simulada_id, segurado_id, visualizada_em "
            "FROM visualizacoes_comunicado WHERE id = 'bbbbbbbb-0000-0000-0000-000000000001'"
        ).fetchone()

    assert linha is not None
    assert str(linha[0]) == ENTREGA_SIMULADA_VISUALIZAVEL_ID
    assert str(linha[1]) == SEGURADO_VISUALIZADOR_ID
    assert linha[2] is not None


def test_migracao_visualizacoes_recusa_segunda_visualizacao_da_mesma_entrega(
    tmp_path: Path,
) -> None:
    """VISU-02/VISU-03: a `UNIQUE (entrega_simulada_id)` (AD-010) impede uma segunda linha de
    visualização para a mesma entrega, mesmo com um segurado diferente."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()

    with abrir_conexao(caminho) as conexao:
        _inserir_visualizacao(conexao, "bbbbbbbb-0000-0000-0000-000000000002")

        with pytest.raises(duckdb.ConstraintException):
            _inserir_visualizacao(
                conexao,
                "bbbbbbbb-0000-0000-0000-000000000003",
                segurado_id="aaaaaaaa-0000-0000-0000-000000000002",
            )
        total = conexao.execute(
            "SELECT count(*) FROM visualizacoes_comunicado WHERE entrega_simulada_id = ?",
            [ENTREGA_SIMULADA_VISUALIZAVEL_ID],
        ).fetchone()

    assert total == (1,)


def test_documentacao_versionada_descreve_a_tabela_de_visualizacao_comunicado() -> None:
    """A tabela de `0015` é documentada no `README.md` versionado, não só no `.sql` (T1)."""

    documento = Path("central_preventiva/adaptadores/persistencia/README.md").read_text(
        encoding="utf-8"
    )

    assert "0015_visualizacoes_comunicado" in documento
    assert "visualizacoes_comunicado" in documento
    assert (
        "`NOT NULL`, `UNIQUE`, chave estrangeira lógica para `entregas_simuladas(id)`"
        in documento
    )
