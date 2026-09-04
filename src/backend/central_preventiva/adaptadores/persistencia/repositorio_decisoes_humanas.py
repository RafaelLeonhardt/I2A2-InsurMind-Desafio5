"""Repositório DuckDB de `decisoes_humanas` (REVISAO-07, REVISAO-11).

Uma linha por decisão que Marina toma sobre uma versão de mensagem. A decisão humana é um
fato distinto da aprovação do agente crítico (3.3): mora em outra tabela, tem outra origem e
outro responsável, e o lote só é simulável quando as duas concordam (REVISAO-14).

`salvar` aceita uma conexão já aberta pelo chamador. É o que permite à decisão em lote gravar
todas as decisões válidas dentro de uma única transação (REVISAO-12) — mesmo parâmetro
opcional já usado por `RepositorioElegibilidades.copiar_para_execucao` (3.1, AD-012), e pela
mesma razão: uma segunda conexão ao mesmo arquivo não enxerga a transação aberta da primeira e
sobrevive ao `ROLLBACK` dela.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import duckdb

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.dominio.decisao_humana import ResultadoDecisaoHumana


@dataclass(frozen=True, slots=True)
class DecisaoHumana:
    """Uma decisão humana persistida, com responsável, resultado e versão decidida."""

    id: UUID
    mensagem_id: UUID
    versao_mensagem_id: UUID
    perfil_responsavel: str
    resultado: ResultadoDecisaoHumana
    justificativa: str | None
    criado_em: datetime


class RepositorioDecisoesHumanas:
    """Persiste e recupera a decisão humana de cada versão de mensagem."""

    def __init__(self, caminho: Path) -> None:
        """Vincula o repositório ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    def salvar(
        self,
        mensagem_id: UUID,
        versao_mensagem_id: UUID,
        perfil: str,
        resultado: ResultadoDecisaoHumana,
        justificativa: str | None,
        conexao: duckdb.DuckDBPyConnection | None = None,
    ) -> UUID:
        """Persiste a decisão e devolve o identificador da linha gravada.

        `criado_em` vem do padrão `now()` da própria tabela: a data da decisão é registrada
        pelo banco, não por um relógio de aplicação (REVISAO-07). Quando `conexao` é
        informada, a gravação roda na transação já aberta pelo chamador.
        """

        id_decisao = uuid4()
        if conexao is not None:
            self._inserir(
                conexao, id_decisao, mensagem_id, versao_mensagem_id, perfil, resultado,
                justificativa,
            )
            return id_decisao
        with abrir_conexao(self._caminho) as propria:
            self._inserir(
                propria, id_decisao, mensagem_id, versao_mensagem_id, perfil, resultado,
                justificativa,
            )
        return id_decisao

    def obter_por_mensagem(self, mensagem_id: UUID) -> list[DecisaoHumana]:
        """Lista as decisões da mensagem, da mais antiga à mais recente (REVISAO-11).

        Uma mensagem regenerada por decisão humana acumula mais de uma decisão: a
        solicitação de nova geração e a decisão sobre a versão seguinte permanecem ambas
        auditáveis, nenhuma sobrescreve a outra.
        """

        with abrir_conexao(self._caminho) as conexao:
            linhas = conexao.execute(
                f"{_SELECT_DECISAO} WHERE mensagem_id = ? ORDER BY criado_em, id",
                [mensagem_id],
            ).fetchall()
        return [_decisao_de_linha(linha) for linha in linhas]

    def _inserir(
        self,
        conexao: duckdb.DuckDBPyConnection,
        id_decisao: UUID,
        mensagem_id: UUID,
        versao_mensagem_id: UUID,
        perfil: str,
        resultado: ResultadoDecisaoHumana,
        justificativa: str | None,
    ) -> None:
        """Executa a inserção da decisão na conexão informada."""

        conexao.execute(
            "INSERT INTO decisoes_humanas "
            "(id, mensagem_id, versao_mensagem_id, perfil_responsavel, resultado, "
            "justificativa) VALUES (?, ?, ?, ?, ?, ?)",
            [
                id_decisao,
                mensagem_id,
                versao_mensagem_id,
                perfil,
                resultado.value,
                justificativa,
            ],
        )


_SELECT_DECISAO = (
    "SELECT id, mensagem_id, versao_mensagem_id, perfil_responsavel, resultado, "
    "justificativa, criado_em FROM decisoes_humanas"
)


def _decisao_de_linha(linha: tuple[object, ...]) -> DecisaoHumana:
    """Traduz uma linha de `_SELECT_DECISAO` para `DecisaoHumana`."""

    return DecisaoHumana(
        id=UUID(str(linha[0])),
        mensagem_id=UUID(str(linha[1])),
        versao_mensagem_id=UUID(str(linha[2])),
        perfil_responsavel=str(linha[3]),
        resultado=ResultadoDecisaoHumana(str(linha[4])),
        justificativa=None if linha[5] is None else str(linha[5]),
        criado_em=cast(datetime, linha[6]),
    )
