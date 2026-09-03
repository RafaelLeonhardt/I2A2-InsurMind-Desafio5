"""Repositório DuckDB de `execucao_preventiva`, com concorrência otimista (AD-008)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.dominio.estados_execucao import EstadoExecucao, eh_terminal


class ConflitoVersao(RuntimeError):
    """Indica que `versao_esperada` não corresponde à versão persistida da execução."""

    def __init__(self, execucao_id: UUID, versao_esperada: int) -> None:
        """Registra a execução e a versão esperada que não bateu."""

        super().__init__(
            f"A execução {execucao_id} não está na versão esperada {versao_esperada}."
        )
        self.execucao_id = execucao_id
        self.versao_esperada = versao_esperada


class TransicaoInvalida(RuntimeError):
    """Indica uma tentativa de transicionar uma execução já em estado terminal."""

    def __init__(self, execucao_id: UUID, estado_atual: EstadoExecucao) -> None:
        """Registra a execução e seu estado terminal atual."""

        super().__init__(
            f"A execução {execucao_id} está no estado terminal '{estado_atual}' e não "
            "pode ser transicionada."
        )
        self.execucao_id = execucao_id
        self.estado_atual = estado_atual


@dataclass(frozen=True, slots=True)
class SnapshotExecucao:
    """Estado e versão de uma execução preventiva, para leitura e checagem otimista.

    `execucao_origem_id` só é preenchido em execução correlacionada, criada por uma nova
    tentativa a partir de um terminal (AD-009, migração `0009`).
    """

    id: UUID
    estado: EstadoExecucao
    versao: int
    execucao_origem_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class Marco:
    """Um marco de transição persistido de uma execução (RUNNER-02)."""

    marco: str
    causa: str | None
    criado_em: datetime


class RepositorioExecucaoPreventiva:
    """Cria, lê e transiciona `execucao_preventiva` com versionamento otimista (AD-008)."""

    def __init__(self, caminho: Path) -> None:
        """Vincula o repositório ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    def criar(self, estado_inicial: EstadoExecucao) -> UUID:
        """Persiste uma nova execução preventiva na versão 1, no estado informado."""

        execucao_id = uuid4()
        with abrir_conexao(self._caminho) as conexao:
            conexao.execute(
                "INSERT INTO execucao_preventiva (id, estado, versao) VALUES (?, ?, 1)",
                [execucao_id, estado_inicial.value],
            )
        return execucao_id

    def obter(self, execucao_id: UUID) -> SnapshotExecucao:
        """Lê o estado e a versão atuais da execução informada.

        Assume que a execução existe (uso interno, apenas por chamadores que acabaram
        de criá-la ou já a leram de `listar_nao_terminais`). Para uma origem externa
        (ex.: um `execucao_id` de URL), use `buscar`, que devolve `None`.
        """

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                f"{_SELECT_SNAPSHOT} WHERE id = ?",
                [execucao_id],
            ).fetchone()
        assert linha is not None, f"execução {execucao_id} não encontrada"
        return _snapshot_de_linha(linha)

    def buscar(self, execucao_id: UUID) -> SnapshotExecucao | None:
        """Lê o estado e a versão da execução informada, ou `None` se não existir."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                f"{_SELECT_SNAPSHOT} WHERE id = ?",
                [execucao_id],
            ).fetchone()
        if linha is None:
            return None
        return _snapshot_de_linha(linha)

    def criar_correlacionada(
        self,
        estado_inicial: EstadoExecucao,
        execucao_origem_id: UUID,
        apos_criar: Callable[[Any, UUID], None] | None = None,
    ) -> UUID:
        """Cria a execução correlacionada a uma origem terminal, na versão 1 (AD-009).

        `apos_criar` roda dentro da mesma transação, depois do `INSERT` e antes do `COMMIT`,
        recebendo a conexão aberta e o id da execução recém-criada. É o que torna atômica a
        cópia das elegibilidades da origem exigida pelo AD-012: ou a execução nova existe
        com o público copiado, ou nada é gravado.
        """

        execucao_id = uuid4()
        with abrir_conexao(self._caminho) as conexao:
            conexao.execute("BEGIN TRANSACTION")
            try:
                conexao.execute(
                    "INSERT INTO execucao_preventiva "
                    "(id, estado, versao, execucao_origem_id) VALUES (?, ?, 1, ?)",
                    [execucao_id, estado_inicial.value, execucao_origem_id],
                )
                if apos_criar is not None:
                    apos_criar(conexao, execucao_id)
                conexao.execute("COMMIT")
            except BaseException:
                conexao.execute("ROLLBACK")
                raise
        return execucao_id

    def listar_correlacionadas(self, execucao_origem_id: UUID) -> list[SnapshotExecucao]:
        """Lista as execuções criadas como nova tentativa da origem informada (PREFL-10).

        Cada execução mantém seu próprio histórico: a lista apenas correlaciona os ids, sem
        mesclar marcos, exceções ou resultados de uma na outra.
        """

        with abrir_conexao(self._caminho) as conexao:
            linhas = conexao.execute(
                f"{_SELECT_SNAPSHOT} WHERE execucao_origem_id = ? ORDER BY criado_em",
                [execucao_origem_id],
            ).fetchall()
        return [_snapshot_de_linha(linha) for linha in linhas]

    def transicionar(
        self, execucao_id: UUID, versao_esperada: int, novo_estado: EstadoExecucao
    ) -> None:
        """Transiciona a execução, incrementando a versão sob checagem otimista (AD-008).

        Levanta `TransicaoInvalida` se o estado atual já for terminal (AD-7: estados
        terminais nunca reabrem) ou `ConflitoVersao` se `versao_esperada` não bater —
        em nenhum dos dois casos a linha é mutada.
        """

        with abrir_conexao(self._caminho) as conexao:
            atual = conexao.execute(
                "SELECT estado FROM execucao_preventiva WHERE id = ?", [execucao_id]
            ).fetchone()
            assert atual is not None, f"execução {execucao_id} não encontrada"
            estado_atual = EstadoExecucao(str(atual[0]))
            if eh_terminal(estado_atual):
                raise TransicaoInvalida(execucao_id, estado_atual)

            resultado = conexao.execute(
                "UPDATE execucao_preventiva SET estado = ?, versao = versao + 1, "
                "atualizado_em = now() WHERE id = ? AND versao = ? RETURNING versao",
                [novo_estado.value, execucao_id, versao_esperada],
            ).fetchone()
        if resultado is None:
            raise ConflitoVersao(execucao_id, versao_esperada)

    def listar_nao_terminais(self) -> list[UUID]:
        """Lista os ids de execuções ainda fora de `ESTADOS_TERMINAIS` (RUNNER-07).

        Usada por `GerenciadorExecucoes.retomar_pendentes` no boot do backend — filtra em
        Python, não em SQL, para que `ESTADOS_TERMINAIS` (AD-004) continue sendo a única
        fonte de verdade sobre quais estados encerram a execução.
        """

        with abrir_conexao(self._caminho) as conexao:
            linhas = conexao.execute("SELECT id, estado FROM execucao_preventiva").fetchall()
        return [
            UUID(str(id_))
            for id_, estado in linhas
            if not eh_terminal(EstadoExecucao(str(estado)))
        ]

    def registrar_marco(
        self, execucao_id: UUID, marco: str, causa: str | None = None
    ) -> None:
        """Persiste um marco de transição correlacionado à execução (RUNNER-02, AD-10)."""

        with abrir_conexao(self._caminho) as conexao:
            conexao.execute(
                "INSERT INTO marcos_execucao (id, execucao_id, marco, causa) "
                "VALUES (?, ?, ?, ?)",
                [uuid4(), execucao_id, marco, causa],
            )

    def listar_marcos(self, execucao_id: UUID) -> list[Marco]:
        """Lista os marcos da execução, em ordem cronológica (RUNNER-07, reidratação)."""

        with abrir_conexao(self._caminho) as conexao:
            linhas = conexao.execute(
                "SELECT marco, causa, criado_em FROM marcos_execucao "
                "WHERE execucao_id = ? ORDER BY criado_em",
                [execucao_id],
            ).fetchall()
        return [
            Marco(
                marco=str(marco),
                causa=None if causa is None else str(causa),
                criado_em=criado_em,
            )
            for marco, causa, criado_em in linhas
        ]


_SELECT_SNAPSHOT = "SELECT id, estado, versao, execucao_origem_id FROM execucao_preventiva"


def _snapshot_de_linha(linha: tuple[object, ...]) -> SnapshotExecucao:
    """Traduz uma linha de `_SELECT_SNAPSHOT` para `SnapshotExecucao`."""

    return SnapshotExecucao(
        id=UUID(str(linha[0])),
        estado=EstadoExecucao(str(linha[1])),
        versao=int(linha[2]),  # type: ignore[arg-type]
        execucao_origem_id=None if linha[3] is None else UUID(str(linha[3])),
    )


class RepositorioExcecoesOperacionais:
    """Registra a `Exceção` operacional quando uma execução alcança `falhou_coleta`."""

    def __init__(self, caminho: Path) -> None:
        """Vincula o repositório ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    def registrar(self, execucao_id: UUID, causa: str, tentativas: int, impacto: str) -> None:
        """Persiste a exceção operacional (causa, tentativas, impacto) da execução."""

        with abrir_conexao(self._caminho) as conexao:
            conexao.execute(
                "INSERT INTO excecoes_operacionais "
                "(id, execucao_id, causa, tentativas, impacto) VALUES (?, ?, ?, ?, ?)",
                [uuid4(), execucao_id, causa, tentativas, impacto],
            )
