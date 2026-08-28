"""Armazenamento genérico das respostas associadas a chaves de idempotência."""

from pathlib import Path

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.aplicacao.portas_persistencia import RespostaRegistrada


class RepositorioIdempotencia:
    """Guarda e recupera respostas por par chave/operação em `chaves_idempotencia`."""

    def __init__(self, caminho: Path) -> None:
        """Vincula o repositório ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    def buscar(self, chave: str, operacao: str) -> RespostaRegistrada | None:
        """Retorna a resposta registrada para o par chave/operação, se existir."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                "SELECT hash_requisicao, resposta_status, resposta_corpo "
                "FROM chaves_idempotencia WHERE chave = ? AND operacao = ?",
                [chave, operacao],
            ).fetchone()
        if linha is None:
            return None
        return RespostaRegistrada(
            hash_requisicao=str(linha[0]),
            status=int(linha[1]),
            corpo=str(linha[2]),
        )

    def registrar(
        self,
        chave: str,
        operacao: str,
        hash_requisicao: str,
        status: int,
        corpo: str,
    ) -> None:
        """Registra a resposta produzida para o par chave/operação."""

        with abrir_conexao(self._caminho) as conexao:
            conexao.execute(
                "INSERT INTO chaves_idempotencia "
                "(chave, operacao, hash_requisicao, resposta_status, resposta_corpo) "
                "VALUES (?, ?, ?, ?, ?)",
                [chave, operacao, hash_requisicao, status, corpo],
            )
