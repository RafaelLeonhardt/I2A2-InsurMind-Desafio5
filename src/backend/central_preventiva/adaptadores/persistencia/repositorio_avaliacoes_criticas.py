"""Repositório DuckDB de `avaliacoes_criticas` (CRIT-05, CRIT-06, CRIT-08).

Uma avaliação por versão de mensagem. `salvar` respeita a `UNIQUE (versao_mensagem_id)` da
migração `0011` por insert-or-noop (AD-010): reavaliar a mesma versão não grava uma segunda
linha nem sobrescreve a primeira — devolve o identificador da avaliação que já está lá. É o
que faz um replay idempotente reaproveitar o resultado persistido, sem nova chamada à OpenAI
(terceiro Edge Case da 3.3). Nenhuma checagem "consulta e depois insere" em Python, que
correria.

SPEC_DEVIATION: o design declara `obter_por_versao -> AvaliacaoCritica | None`. A
implementação devolve `RegistroAvaliacaoCritica`, que traz a decisão e também agente, modelo,
duração e instante. CRIT-08 exige exibir esses quatro no detalhe da avaliação, e o tipo do
design não os expõe. Mesma forma já adotada em 3.1 para `RegistroContextoAgente`.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.dominio.avaliacao_critica import (
    AvaliacaoCritica,
    CategoriaCritica,
    MotivoCritica,
)

AGENTE_CRITICO = "critico"
"""Nome do agente registrado em toda avaliação desta história (CRIT-08)."""


@dataclass(frozen=True, slots=True)
class RegistroAvaliacaoCritica:
    """Uma avaliação persistida, com a decisão e a proveniência da chamada."""

    id: UUID
    versao_mensagem_id: UUID
    avaliacao: AvaliacaoCritica
    agente: str
    modelo: str
    duracao_ms: float
    criado_em: datetime


def serializar_motivos(motivos: tuple[MotivoCritica, ...]) -> str:
    """Serializa os motivos como lista de `{categoria, justificativa}` (schema da migração)."""

    return json.dumps(
        [
            {"categoria": motivo.categoria.value, "justificativa": motivo.justificativa}
            for motivo in motivos
        ],
        ensure_ascii=False,
    )


def desserializar_motivos(bruto: str) -> tuple[MotivoCritica, ...]:
    """Reconstrói os motivos a partir do JSON persistido, sem reavaliar nada."""

    itens = cast(list[dict[str, str]], json.loads(bruto))
    return tuple(
        MotivoCritica(
            categoria=CategoriaCritica(item["categoria"]),
            justificativa=item["justificativa"],
        )
        for item in itens
    )


class RepositorioAvaliacoesCriticas:
    """Persiste e recupera a avaliação crítica de cada versão de mensagem."""

    def __init__(self, caminho: Path) -> None:
        """Vincula o repositório ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    def salvar(
        self,
        versao_mensagem_id: UUID,
        aprovada: bool,
        motivos: tuple[MotivoCritica, ...],
        modelo: str,
        duracao_ms: float,
    ) -> UUID:
        """Persiste a avaliação da versão e devolve o identificador que ficou valendo.

        Insert-or-noop sobre a `UNIQUE (versao_mensagem_id)`: se a versão já tem avaliação,
        a primeira permanece intacta e é o identificador dela que volta.
        """

        id_registro = uuid4()
        with abrir_conexao(self._caminho) as conexao:
            conexao.execute(
                "INSERT INTO avaliacoes_criticas "
                "(id, versao_mensagem_id, aprovada, motivos, agente, modelo, duracao_ms) "
                "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT DO NOTHING",
                [
                    id_registro,
                    versao_mensagem_id,
                    aprovada,
                    serializar_motivos(motivos),
                    AGENTE_CRITICO,
                    modelo,
                    duracao_ms,
                ],
            )
            linha = conexao.execute(
                "SELECT id FROM avaliacoes_criticas WHERE versao_mensagem_id = ?",
                [versao_mensagem_id],
            ).fetchone()
        assert linha is not None, f"avaliação da versão {versao_mensagem_id} não persistida"
        return UUID(str(linha[0]))

    def obter_por_versao(self, versao_mensagem_id: UUID) -> RegistroAvaliacaoCritica | None:
        """Lê a avaliação da versão, ou `None` se ela ainda não foi avaliada."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                f"{_SELECT_AVALIACAO} WHERE versao_mensagem_id = ?", [versao_mensagem_id]
            ).fetchone()
        if linha is None:
            return None
        return _avaliacao_de_linha(linha)


_SELECT_AVALIACAO = (
    "SELECT id, versao_mensagem_id, aprovada, motivos, agente, modelo, duracao_ms, "
    "criado_em FROM avaliacoes_criticas"
)


def _avaliacao_de_linha(linha: tuple[object, ...]) -> RegistroAvaliacaoCritica:
    """Traduz uma linha de `_SELECT_AVALIACAO` para `RegistroAvaliacaoCritica`."""

    return RegistroAvaliacaoCritica(
        id=UUID(str(linha[0])),
        versao_mensagem_id=UUID(str(linha[1])),
        avaliacao=AvaliacaoCritica(
            aprovada=bool(linha[2]),
            motivos=desserializar_motivos(str(linha[3])),
        ),
        agente=str(linha[4]),
        modelo=str(linha[5]),
        duracao_ms=float(linha[6]),  # type: ignore[arg-type]
        criado_em=cast(datetime, linha[7]),
    )
