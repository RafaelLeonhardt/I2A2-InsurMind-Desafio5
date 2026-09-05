"""Repositório DuckDB de `visualizacoes_comunicado` (VISU-01, VISU-02, VISU-03).

`registrar_primeira_visualizacao` respeita a `UNIQUE (entrega_simulada_id)` da migração `0015`
por insert-or-noop (AD-010), mesmo padrão de `RepositorioAvaliacoesCriticas.salvar` (3.3): a
primeira chamada que chega grava a linha; qualquer reabertura ou abertura concorrente da mesma
entrega recebe o conflito e o `SELECT` seguinte, na mesma conexão, lê a linha que já está lá —
própria ou de quem venceu a corrida — nunca uma segunda `INSERT`. Nenhuma checagem "consulta e
depois insere" em Python, que correria.

SPEC_DEVIATION: o `design.md` afirma que `ON CONFLICT DO NOTHING` sozinho basta, "sem exigir
lock explícito adicional". Verificado empiricamente (duas threads reais, duas conexões DuckDB
distintas, mesma `entrega_simulada_id`, sem `BEGIN` explícito): quando as duas chamadas
realmente correm ao mesmo tempo, DuckDB detecta o conflito de escrita concorrente na
transação perdedora e a rejeita com `ConstraintException` (achado no próprio `INSERT`) ou
`TransactionException` (achado só no commit implícito), dependendo do instante exato da
corrida — nunca absorvido silenciosamente pelo `ON CONFLICT DO NOTHING` como o texto do design
sugere. `registrar_primeira_visualizacao` captura as duas exceções ao redor do `INSERT` e
segue para o mesmo `SELECT` de leitura, que converge para a linha do vencedor em ambos os
casos — o requisito de convergência (VISU-03) é cumprido pelo repositório, não pela garantia
(inexistente) do `ON CONFLICT DO NOTHING` isolado.

SPEC_DEVIATION: o `design.md` declara `registrar_primeira_visualizacao(self,
entrega_simulada_id)`, sem `segurado_id`. A coluna `segurado_id` é `NOT NULL` (snapshot de quem
visualizou, Edge Case de isolamento por segurado) e não tem valor derivável de dentro do
repositório — o parâmetro é obrigatório aqui.
"""

from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import duckdb

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao


@dataclass(frozen=True, slots=True)
class VisualizacaoComunicado:
    """A primeira visualização persistida de um comunicado, por entrega simulada."""

    id: UUID
    entrega_simulada_id: UUID
    segurado_id: UUID
    visualizada_em: datetime


class RepositorioVisualizacoesComunicado:
    """Registra a primeira visualização de forma idempotente/concorrente-segura."""

    def __init__(self, caminho: Path) -> None:
        """Vincula o repositório ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    def registrar_primeira_visualizacao(
        self, entrega_simulada_id: UUID, segurado_id: UUID
    ) -> VisualizacaoComunicado:
        """Grava a primeira visualização, ou devolve a já persistida (VISU-01/02/03).

        Nunca lança em caso de conflito: a `UNIQUE (entrega_simulada_id)` absorve a
        corrida, e a leitura seguinte sempre devolve exatamente uma linha, com a mesma
        `visualizada_em` para toda chamada concorrente ou repetida.
        """

        id_registro = uuid4()
        with abrir_conexao(self._caminho) as conexao:
            with suppress(duckdb.ConstraintException, duckdb.TransactionException):
                conexao.execute(
                    "INSERT INTO visualizacoes_comunicado "
                    "(id, entrega_simulada_id, segurado_id) VALUES (?, ?, ?) "
                    "ON CONFLICT DO NOTHING",
                    [id_registro, entrega_simulada_id, segurado_id],
                )
            linha = conexao.execute(
                f"{_SELECT_VISUALIZACAO} WHERE entrega_simulada_id = ?",
                [entrega_simulada_id],
            ).fetchone()
        assert linha is not None, (
            f"visualização da entrega {entrega_simulada_id} não persistida"
        )
        return _visualizacao_de_linha(linha)

    def obter_por_entrega(self, entrega_simulada_id: UUID) -> VisualizacaoComunicado | None:
        """Lê a visualização da entrega, ou `None` se ainda não foi visualizada."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                f"{_SELECT_VISUALIZACAO} WHERE entrega_simulada_id = ?",
                [entrega_simulada_id],
            ).fetchone()
        if linha is None:
            return None
        return _visualizacao_de_linha(linha)


_SELECT_VISUALIZACAO = (
    "SELECT id, entrega_simulada_id, segurado_id, visualizada_em FROM visualizacoes_comunicado"
)


def _visualizacao_de_linha(linha: tuple[object, ...]) -> VisualizacaoComunicado:
    """Traduz uma linha de `_SELECT_VISUALIZACAO` para `VisualizacaoComunicado`."""

    return VisualizacaoComunicado(
        id=UUID(str(linha[0])),
        entrega_simulada_id=UUID(str(linha[1])),
        segurado_id=UUID(str(linha[2])),
        visualizada_em=cast(datetime, linha[3]),
    )
