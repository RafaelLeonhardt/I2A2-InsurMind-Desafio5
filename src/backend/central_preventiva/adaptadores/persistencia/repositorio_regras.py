"""Repositório de leitura da regra ativa por tipo de evento.

A escrita e o versionamento de `regras` pertencem à História 2.4 — esta história só lê.
"""

from pathlib import Path
from uuid import UUID

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.dominio.avaliador_risco import RegraSnapshot
from central_preventiva.dominio.evento_meteorologico import TipoEventoMeteorologico


class RepositorioRegras:
    """Consulta a regra ativa da tabela `regras` (schema do Épico 1) por tipo de evento."""

    def __init__(self, caminho: Path) -> None:
        """Vincula o repositório ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    def obter_ativa(self, evento_tipo: TipoEventoMeteorologico) -> RegraSnapshot | None:
        """Resolve a regra `ativa` para o tipo de evento informado, ou `None` se não houver."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                "SELECT id, evento_tipo, limiar_meteorologico, area_aplicavel, apolice_tipo, "
                "versao FROM regras WHERE evento_tipo = ? AND estado = 'ativa' "
                "ORDER BY versao DESC LIMIT 1",
                [evento_tipo.value],
            ).fetchone()
        if linha is None:
            return None
        return RegraSnapshot(
            id=UUID(str(linha[0])),
            evento_tipo=TipoEventoMeteorologico(str(linha[1])),
            limiar_meteorologico=float(linha[2]),
            area_aplicavel=str(linha[3]),
            apolice_tipo=str(linha[4]),
            versao=int(linha[5]),
        )
