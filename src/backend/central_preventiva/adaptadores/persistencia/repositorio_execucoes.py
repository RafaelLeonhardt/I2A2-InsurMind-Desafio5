"""Consulta de execuções preventivas em estado não terminal."""

from pathlib import Path

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.dominio.estados_execucao import ESTADOS_TERMINAIS

_TERMINAIS = tuple(sorted(estado.value for estado in ESTADOS_TERMINAIS))
_MARCADORES = ", ".join("?" for _ in _TERMINAIS)
CONSULTA_NAO_TERMINAL = (
    "SELECT EXISTS("
    f"SELECT 1 FROM execucao_preventiva WHERE estado NOT IN ({_MARCADORES})"
    ")"
)


class RepositorioExecucoes:
    """Implementa a guarda que impede restaurar com uma execução em andamento."""

    def __init__(self, caminho: Path) -> None:
        """Vincula o repositório ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    def existe_execucao_nao_terminal(self) -> bool:
        """Informa se há ao menos uma execução preventiva fora dos estados terminais."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(CONSULTA_NAO_TERMINAL, list(_TERMINAIS)).fetchone()
        return bool(linha is not None and linha[0])
