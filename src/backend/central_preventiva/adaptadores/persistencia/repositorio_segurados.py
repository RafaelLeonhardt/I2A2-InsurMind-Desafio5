"""Consulta somente leitura de um segurado sintético por id."""

from pathlib import Path
from uuid import UUID

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.dominio.segurado import Segurado


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
