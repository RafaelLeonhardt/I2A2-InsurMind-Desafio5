"""Sonda de prontidão do banco de dados operacional (DuckDB)."""

from pathlib import Path

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.aplicacao.portas_prontidao import ResultadoSonda
from central_preventiva.dominio.estados_prontidao import EstadoProntidao

CAUSA_BANCO_INACESSIVEL = "Não foi possível abrir o banco de dados operacional."
"""Causa saneada exposta quando a conexão com o banco falha, sem o caminho do arquivo."""


class SondaBancoDados:
    """Verifica a prontidão do banco de dados operacional com um `SELECT 1`."""

    def __init__(self, caminho: Path) -> None:
        """Guarda o caminho do arquivo DuckDB a ser sondado."""

        self._caminho = caminho

    async def verificar(self) -> ResultadoSonda:
        """Confirma a disponibilidade do banco, saneando qualquer causa de falha."""

        try:
            with abrir_conexao(self._caminho) as conexao:
                conexao.execute("SELECT 1")
        except Exception:
            return ResultadoSonda(
                estado=EstadoProntidao.INDISPONIVEL,
                causa=CAUSA_BANCO_INACESSIVEL,
                latencia_ms=None,
            )

        return ResultadoSonda(estado=EstadoProntidao.DISPONIVEL, causa=None, latencia_ms=None)
