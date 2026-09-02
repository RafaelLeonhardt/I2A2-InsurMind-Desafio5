"""Repositório do snapshot imutável da avaliação de relevância meteorológica (AD-11)."""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.dominio.avaliador_risco import Criterio, ResultadoAvaliacaoRisco


@dataclass(frozen=True, slots=True)
class AvaliacaoRisco:
    """Snapshot persistido de uma avaliação de risco, pronto para consulta (RISCO-11).

    `regra_id`/`regra_versao` são nulos quando não havia regra ativa para o tipo do
    evento (RISCO-09) — não há regra real a referenciar, mas a decisão terminal ainda
    fica persistida e explicável.
    """

    id: UUID
    execucao_id: UUID
    evento_id: UUID
    regra_id: UUID | None
    regra_versao: int | None
    relevante: bool
    criterios: tuple[Criterio, ...]
    motivo: str
    criado_em: datetime


def _serializar_criterios(criterios: tuple[Criterio, ...]) -> str:
    """Serializa os critérios avaliados em JSON, na ordem em que foram produzidos."""

    return json.dumps(
        [
            {
                "operando": criterio.operando,
                "valor_observado": criterio.valor_observado,
                "atende": criterio.atende,
                "justificativa": criterio.justificativa,
            }
            for criterio in criterios
        ]
    )


def _desserializar_criterios(bruto: str) -> tuple[Criterio, ...]:
    """Reconstrói os critérios avaliados a partir do JSON persistido."""

    return tuple(
        Criterio(
            operando=item["operando"],
            valor_observado=item["valor_observado"],
            atende=item["atende"],
            justificativa=item["justificativa"],
        )
        for item in json.loads(bruto)
    )


class RepositorioAvaliacoesRisco:
    """Persiste e consulta o snapshot imutável de uma avaliação de risco."""

    def __init__(self, caminho: Path) -> None:
        """Vincula o repositório ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    def salvar(
        self,
        execucao_id: UUID,
        evento_id: UUID,
        regra_id: UUID | None,
        regra_versao: int | None,
        resultado: ResultadoAvaliacaoRisco,
    ) -> UUID:
        """Persiste o snapshot completo da avaliação: evento, regra, versão e critérios.

        `regra_id`/`regra_versao` são `None` quando não havia regra ativa para o tipo
        do evento — a decisão (`sem_risco`, motivo `sem_regra_ativa`) ainda é persistida.
        """

        id_avaliacao = uuid4()
        with abrir_conexao(self._caminho) as conexao:
            conexao.execute(
                "INSERT INTO avaliacoes_risco "
                "(id, execucao_id, evento_id, regra_id, regra_versao, relevante, criterios, "
                "motivo) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    id_avaliacao,
                    execucao_id,
                    evento_id,
                    regra_id,
                    regra_versao,
                    resultado.relevante,
                    _serializar_criterios(resultado.criterios),
                    resultado.motivo,
                ],
            )
        return id_avaliacao

    def obter_por_execucao(self, execucao_id: UUID) -> AvaliacaoRisco | None:
        """Recupera o snapshot já salvo para a execução, sem recalcular nada."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                "SELECT id, execucao_id, evento_id, regra_id, regra_versao, relevante, "
                "criterios, motivo, criado_em FROM avaliacoes_risco WHERE execucao_id = ?",
                [execucao_id],
            ).fetchone()
        if linha is None:
            return None
        return AvaliacaoRisco(
            id=UUID(str(linha[0])),
            execucao_id=UUID(str(linha[1])),
            evento_id=UUID(str(linha[2])),
            regra_id=None if linha[3] is None else UUID(str(linha[3])),
            regra_versao=None if linha[4] is None else int(linha[4]),
            relevante=bool(linha[5]),
            criterios=_desserializar_criterios(str(linha[6])),
            motivo=str(linha[7]),
            criado_em=linha[8],
        )
