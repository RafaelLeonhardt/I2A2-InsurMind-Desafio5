"""Transação única do DuckDB oferecida como porta ao caso de uso (REVISAO-12).

SPEC_DEVIATION (História 3.5): componente ausente da seção Components do `design.md` da 3.5,
que só descreve `RepositorioDecisoesHumanas` e `ServicoRevisaoLote`. `TransacaoDuckDB` foi
necessário porque design.md's "uma transação DuckDB por chamada de `decidir_lote`" não é
implementável sem um objeto que abra a conexão uma vez e a repasse a todos os repositórios
participantes — confirmado empiricamente nesta história: uma segunda conexão ao mesmo arquivo
não enxerga a transação aberta pela primeira e sobrevive ao `ROLLBACK` dela, então qualquer
repositório que abrisse sua própria conexão quebraria a atomicidade "tudo ou nada".

Mesma forma já usada por `RepositorioExecucaoPreventiva.criar_correlacionada` (AD-012): quem
abre a transação é a persistência, e o caso de uso só recebe a conexão para repassá-la aos
repositórios que participam dela. Assim a aplicação decide *o que* é atômico sem conhecer
DuckDB nem `abrir_conexao`.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao


class TransacaoDuckDB:
    """Executa uma operação inteira dentro de uma única transação do banco operacional."""

    def __init__(self, caminho: Path) -> None:
        """Vincula a transação ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    def executar[T](self, operacao: Callable[[Any], T]) -> T:
        """Roda `operacao` com a conexão da transação; qualquer exceção faz `ROLLBACK`."""

        with abrir_conexao(self._caminho) as conexao:
            conexao.execute("BEGIN TRANSACTION")
            try:
                resultado = operacao(conexao)
                conexao.execute("COMMIT")
            except BaseException:
                conexao.execute("ROLLBACK")
                raise
        return resultado
