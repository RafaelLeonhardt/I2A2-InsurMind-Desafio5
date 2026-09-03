"""Repositório do contexto mínimo e da sua proveniência por item (PREFL-13, PREFL-14).

O conteúdo persistido é exatamente o `ContextoAgente` serializado — os cinco campos
permitidos, nada além. A proveniência guarda nomes de categoria, nunca conteúdo: consultar
a proveniência nunca expõe dado sensível, porque dado sensível nunca é copiado para cá.

SPEC_DEVIATION: o design declara `obter_por_elegibilidade -> ContextoAgente | None`. A
implementação devolve `RegistroContextoAgente`, que traz o contexto e as duas listas de
categorias. PREFL-14 exige consultar a proveniência antes ou depois da geração, e o tipo do
design não a expõe; devolver as três coisas em uma leitura também evita recalcular qualquer
uma delas (T6: "obter recupera sem recalcular").
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.dominio.montador_contexto_agente import ContextoAgente


@dataclass(frozen=True, slots=True)
class RegistroContextoAgente:
    """Um contexto mínimo persistido, com a proveniência registrada junto dele."""

    id: UUID
    execucao_id: UUID
    elegibilidade_id: UUID
    contexto: ContextoAgente
    categorias_usadas: tuple[str, ...]
    categorias_nao_usadas: tuple[str, ...]


def serializar_contexto(contexto: ContextoAgente) -> str:
    """Serializa os cinco campos do contexto mínimo, sem nenhum campo derivado."""

    return json.dumps(
        {
            "evento": contexto.evento,
            "localizacao_aproximada": contexto.localizacao_aproximada,
            "coberturas_relevantes": list(contexto.coberturas_relevantes),
            "canal": contexto.canal,
            "orientacoes_seguranca": list(contexto.orientacoes_seguranca),
        },
        ensure_ascii=False,
    )


def desserializar_contexto(bruto: str) -> ContextoAgente:
    """Reconstrói o contexto mínimo a partir do JSON persistido, sem recalcular nada."""

    dados = cast(dict[str, object], json.loads(bruto))
    return ContextoAgente(
        evento=str(dados["evento"]),
        localizacao_aproximada=str(dados["localizacao_aproximada"]),
        coberturas_relevantes=tuple(
            str(item) for item in cast(list[object], dados["coberturas_relevantes"])
        ),
        canal=str(dados["canal"]),
        orientacoes_seguranca=tuple(
            str(item) for item in cast(list[object], dados["orientacoes_seguranca"])
        ),
    )


class RepositorioContextosAgente:
    """Persiste e recupera o contexto minimizado de cada item do público elegível."""

    def __init__(self, caminho: Path) -> None:
        """Vincula o repositório ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    def salvar(
        self,
        execucao_id: UUID,
        elegibilidade_id: UUID,
        contexto: ContextoAgente,
        categorias_usadas: tuple[str, ...],
        categorias_nao_usadas: tuple[str, ...],
    ) -> UUID:
        """Persiste o contexto e sua proveniência, devolvendo o id do registro criado.

        `UNIQUE (elegibilidade_id)` (migração `0009`) garante um contexto por item: um
        segundo `salvar` para a mesma elegibilidade levanta erro do próprio banco, em vez de
        sobrescrever silenciosamente um contexto já usado por uma geração.
        """

        id_registro = uuid4()
        with abrir_conexao(self._caminho) as conexao:
            conexao.execute(
                "INSERT INTO contextos_agente "
                "(id, execucao_id, elegibilidade_id, conteudo, categorias_usadas, "
                "categorias_nao_usadas) VALUES (?, ?, ?, ?, ?, ?)",
                [
                    id_registro,
                    execucao_id,
                    elegibilidade_id,
                    serializar_contexto(contexto),
                    list(categorias_usadas),
                    list(categorias_nao_usadas),
                ],
            )
        return id_registro

    def obter_por_elegibilidade(self, elegibilidade_id: UUID) -> RegistroContextoAgente | None:
        """Lê o contexto e a proveniência do item, ou `None` se ainda não houver contexto."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                f"{_SELECT_REGISTRO} WHERE elegibilidade_id = ?",
                [elegibilidade_id],
            ).fetchone()
        if linha is None:
            return None
        return _registro_de_linha(linha)

    def listar_por_execucao(self, execucao_id: UUID) -> list[RegistroContextoAgente]:
        """Lista os contextos já montados da execução, na ordem em que foram criados.

        É a leitura que a consulta de proveniência usa (PREFL-14): a lista devolve as
        categorias usadas e não usadas de cada item já preparado, sem recalcular nada.
        """

        with abrir_conexao(self._caminho) as conexao:
            linhas = conexao.execute(
                f"{_SELECT_REGISTRO} WHERE execucao_id = ? ORDER BY criado_em",
                [execucao_id],
            ).fetchall()
        return [_registro_de_linha(linha) for linha in linhas]


_SELECT_REGISTRO = (
    "SELECT id, execucao_id, elegibilidade_id, conteudo, categorias_usadas, "
    "categorias_nao_usadas FROM contextos_agente"
)


def _registro_de_linha(linha: tuple[object, ...]) -> RegistroContextoAgente:
    """Traduz uma linha de `_SELECT_REGISTRO` para `RegistroContextoAgente`."""

    return RegistroContextoAgente(
        id=UUID(str(linha[0])),
        execucao_id=UUID(str(linha[1])),
        elegibilidade_id=UUID(str(linha[2])),
        contexto=desserializar_contexto(str(linha[3])),
        categorias_usadas=tuple(str(item) for item in cast(list[object], linha[4])),
        categorias_nao_usadas=tuple(str(item) for item in cast(list[object], linha[5])),
    )
