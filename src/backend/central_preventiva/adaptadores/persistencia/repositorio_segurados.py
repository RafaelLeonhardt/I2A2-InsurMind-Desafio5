"""Consulta somente leitura de um segurado sintético por id."""

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.dominio.segurado import Segurado


@dataclass(frozen=True, slots=True)
class PreferenciasSegurado:
    """As preferências de comunicação de um segurado (5.3, 5.6): canal e participação em
    alertas — separado de `Segurado` (id+nome) para não alargar o tipo mínimo já usado por
    `consultar_segurado_padrao` e pela barra de contexto."""

    canal_preferido: str
    participa_de_alertas: bool


class RepositorioSegurados:
    """Consulta um segurado sintético pelo seu identificador."""

    def __init__(self, caminho: Path) -> None:
        """Vincula o repositório ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    def buscar_por_id(self, id: UUID) -> Segurado | None:
        """Retorna o segurado com o id informado, ou `None` se não existir."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                "SELECT id, nome FROM segurados WHERE id = ?", [id]
            ).fetchone()
        if linha is None:
            return None
        return Segurado(id=UUID(str(linha[0])), nome=str(linha[1]))

    def buscar_preferencias_por_id(self, id: UUID) -> PreferenciasSegurado | None:
        """Retorna o canal preferencial e a participação em alertas do segurado, ou
        `None` se não existir (5.3, APOLICE-01: "canal preferencial e participação em
        alertas" fazem parte do registro do segurado, não da apólice)."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                "SELECT canal_preferido, participa_de_alertas FROM segurados WHERE id = ?",
                [id],
            ).fetchone()
        if linha is None:
            return None
        return PreferenciasSegurado(
            canal_preferido=str(linha[0]), participa_de_alertas=bool(linha[1])
        )
