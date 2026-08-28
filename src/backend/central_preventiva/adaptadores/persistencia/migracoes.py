"""Executor das migrações versionadas do banco operacional DuckDB."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

import duckdb

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.aplicacao.portas_persistencia import (
    MigracaoFalhou,
    RegistroMigracoesInvalido,
    ResultadoMigracao,
    VersaoSchemaFutura,
)

TABELA_REGISTRO = "schema_migracoes"
COLUNAS_REGISTRO = frozenset({"versao", "descricao", "aplicada_em"})
PADRAO_ARQUIVO = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")


@dataclass(frozen=True, slots=True)
class Migracao:
    """Representa uma migração versionada carregada do repositório."""

    versao: int
    descricao: str
    sql: str


def carregar_migracoes() -> tuple[Migracao, ...]:
    """Carrega, em ordem crescente de versão, as migrações `.sql` versionadas."""

    diretorio = files("central_preventiva.adaptadores.persistencia").joinpath("migracoes")
    encontradas: list[Migracao] = []
    for recurso in diretorio.iterdir():
        correspondencia = PADRAO_ARQUIVO.match(recurso.name)
        if correspondencia is None:
            continue
        encontradas.append(
            Migracao(
                versao=int(correspondencia.group(1)),
                descricao=correspondencia.group(2).replace("_", " "),
                sql=recurso.read_text(encoding="utf-8"),
            )
        )
    return tuple(sorted(encontradas, key=lambda migracao: migracao.versao))


MIGRACOES = carregar_migracoes()


class ExecutorMigracoes:
    """Aplica as migrações versionadas pendentes, cada uma em sua própria transação."""

    def __init__(self, caminho: Path, migracoes: Sequence[Migracao] | None = None) -> None:
        """Vincula o executor ao arquivo operacional e à lista de migrações conhecidas."""

        self._caminho = caminho
        self._migracoes = tuple(MIGRACOES if migracoes is None else migracoes)

    def versao_conhecida(self) -> int:
        """Retorna a maior versão de migração conhecida por este código."""

        return max((migracao.versao for migracao in self._migracoes), default=0)

    def versao_registrada(self) -> int | None:
        """Retorna a maior versão registrada no banco, ou `None` se ainda não houver banco."""

        with abrir_conexao(self._caminho) as conexao:
            return self._ler_versao_registrada(conexao)

    def aplicar_pendentes(self) -> ResultadoMigracao:
        """Aplica em ordem as migrações pendentes, recusando um banco em versão futura."""

        with abrir_conexao(self._caminho) as conexao:
            registrada = self._ler_versao_registrada(conexao)
            conhecida = self.versao_conhecida()
            if registrada is not None and registrada > conhecida:
                raise VersaoSchemaFutura(versao_registrada=registrada, versao_conhecida=conhecida)

            aplicadas: list[int] = []
            for migracao in self._migracoes:
                if migracao.versao <= (registrada or 0):
                    continue
                self._aplicar(conexao, migracao)
                aplicadas.append(migracao.versao)

        return ResultadoMigracao(
            versoes_aplicadas=tuple(aplicadas),
            versao_final=max(aplicadas, default=registrada or 0),
        )

    def _ler_versao_registrada(self, conexao: duckdb.DuckDBPyConnection) -> int | None:
        """Lê o registro de migrações e recusa um banco existente sem registro íntegro."""

        tabelas = {
            nome
            for (nome,) in conexao.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()
        }
        if TABELA_REGISTRO not in tabelas:
            if tabelas:
                raise RegistroMigracoesInvalido(
                    f"o banco possui tabelas ({', '.join(sorted(tabelas))}) mas não possui "
                    f"a tabela {TABELA_REGISTRO}"
                )
            return None

        colunas = {
            nome
            for (nome,) in conexao.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'main' AND table_name = ?",
                [TABELA_REGISTRO],
            ).fetchall()
        }
        if not COLUNAS_REGISTRO.issubset(colunas):
            faltantes = ", ".join(sorted(COLUNAS_REGISTRO - colunas))
            raise RegistroMigracoesInvalido(
                f"a tabela {TABELA_REGISTRO} não possui as colunas esperadas ({faltantes})"
            )

        linha = conexao.execute(f"SELECT max(versao) FROM {TABELA_REGISTRO}").fetchone()
        return None if linha is None or linha[0] is None else int(linha[0])

    def _aplicar(self, conexao: duckdb.DuckDBPyConnection, migracao: Migracao) -> None:
        """Executa uma migração e registra sua versão dentro da mesma transação."""

        conexao.execute("BEGIN TRANSACTION")
        try:
            conexao.execute(migracao.sql)
            conexao.execute(
                f"INSERT INTO {TABELA_REGISTRO} (versao, descricao) VALUES (?, ?)",
                [migracao.versao, migracao.descricao],
            )
            conexao.execute("COMMIT")
        except duckdb.Error as erro:
            conexao.execute("ROLLBACK")
            raise MigracaoFalhou(
                versao=migracao.versao,
                descricao=migracao.descricao,
                causa=str(erro),
            ) from erro
