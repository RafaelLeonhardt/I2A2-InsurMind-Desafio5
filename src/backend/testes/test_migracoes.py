"""Testes do executor de migrações versionadas do DuckDB."""

from pathlib import Path

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

    assert resultado.versoes_aplicadas == (1,)
    assert resultado.versao_final == 1
    assert tabelas(caminho) == TABELAS_ESPERADAS
    assert registros(caminho) == [(1, "schema inicial")]


def test_reexecucao_sobre_banco_atual_nao_aplica_nada(tmp_path: Path) -> None:
    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()

    resultado = ExecutorMigracoes(caminho).aplicar_pendentes()

    assert resultado.versoes_aplicadas == ()
    assert resultado.versao_final == 1
    assert registros(caminho) == [(1, "schema inicial")]


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


def test_migracoes_versionadas_tem_versoes_unicas_e_ordenadas() -> None:
    versoes = [migracao.versao for migracao in MIGRACOES]

    assert versoes == sorted(set(versoes))
    assert versoes[0] == 1
