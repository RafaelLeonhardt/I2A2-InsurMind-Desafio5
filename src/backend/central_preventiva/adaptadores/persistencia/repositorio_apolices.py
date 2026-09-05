"""Repositório da apólice sintética (5.3) — primeira leitura de produção de `apolices`."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from uuid import UUID

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao

_SELECT_APOLICE = (
    "SELECT id, segurado_id, numero, tipo, situacao, vigencia_inicio, vigencia_fim, "
    "coberturas, endereco_risco_sintetico, codigo_ibge_area FROM apolices"
)


@dataclass(frozen=True, slots=True)
class Apolice:
    """Uma apólice sintética, tal como persistida (schema do Épico 1)."""

    id: UUID
    segurado_id: UUID
    numero: str
    tipo: str
    situacao: str
    vigencia_inicio: date
    vigencia_fim: date
    coberturas: tuple[str, ...]
    endereco_risco_sintetico: str
    codigo_ibge_area: str


def _apolice_de_linha(linha: tuple[object, ...]) -> Apolice:
    """Traduz uma linha de `_SELECT_APOLICE` para `Apolice`."""

    return Apolice(
        id=UUID(str(linha[0])),
        segurado_id=UUID(str(linha[1])),
        numero=str(linha[2]),
        tipo=str(linha[3]),
        situacao=str(linha[4]),
        vigencia_inicio=linha[5],  # type: ignore[assignment]
        vigencia_fim=linha[6],  # type: ignore[assignment]
        coberturas=tuple(str(item) for item in linha[7]),  # type: ignore[union-attr]
        endereco_risco_sintetico=str(linha[8]),
        codigo_ibge_area=str(linha[9]),
    )


class RepositorioApolices:
    """Consulta somente leitura da apólice sintética de um segurado."""

    def __init__(self, caminho: Path) -> None:
        """Vincula o repositório ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    def buscar_por_segurado(self, segurado_id: UUID) -> Apolice | None:
        """Resolve a apólice do segurado, ou `None` se não houver nenhuma.

        Um segurado pode ter mais de uma apólice no schema (Épico 1 permite mais de uma
        combinação segurado+apólice por área) — `ORDER BY criado_em DESC LIMIT 1` resolve
        deterministicamente a mais recente, já que a spec (5.3) trata "a apólice" do
        segurado no singular, sem cobrir múltiplas apólices simultâneas.
        """

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                f"{_SELECT_APOLICE} WHERE segurado_id = ? ORDER BY criado_em DESC LIMIT 1",
                [segurado_id],
            ).fetchone()
        if linha is None:
            return None
        return _apolice_de_linha(linha)

    def buscar_por_id(self, apolice_id: UUID) -> Apolice | None:
        """Resolve a apólice pelo seu identificador, ou `None` se não existir."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                f"{_SELECT_APOLICE} WHERE id = ?", [apolice_id]
            ).fetchone()
        if linha is None:
            return None
        return _apolice_de_linha(linha)
