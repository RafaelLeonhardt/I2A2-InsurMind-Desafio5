"""Portas e tipos compartilhados do caso de uso de prontidão das dependências."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

from central_preventiva.dominio.estados_prontidao import EstadoProntidao

NomeDependencia = Literal["backend", "banco_dados", "inmet", "openai"]
"""Nomes canônicos das 4 dependências cuja prontidão é verificada."""


@dataclass(frozen=True, slots=True)
class ResultadoSonda:
    """Resultado terminal produzido por uma sonda ao final de uma verificação."""

    estado: EstadoProntidao
    causa: str | None
    latencia_ms: float | None


@dataclass(frozen=True, slots=True)
class EstadoDependencia:
    """Estado de prontidão de uma dependência, pronto para exibição na superfície."""

    nome: NomeDependencia
    estado: EstadoProntidao
    verificado_em: datetime | None
    causa: str | None
    impacto: str
    acao_disponivel: str


class PortaSonda(Protocol):
    """Verifica a prontidão de uma dependência externa por meio de uma sonda."""

    async def verificar(self) -> ResultadoSonda:
        """Executa a verificação e retorna um resultado terminal (nunca `VERIFICANDO`)."""
        ...


class VerificacaoEmAndamento(RuntimeError):
    """Indica que uma verificação já está em voo para a dependência com outra chave."""

    def __init__(self, nome: NomeDependencia) -> None:
        """Identifica a dependência com verificação em andamento e monta a mensagem."""

        super().__init__(
            f"Já existe uma verificação em andamento para a dependência '{nome}'. "
            "Aguarde a conclusão antes de solicitar uma nova com outra chave de idempotência."
        )
        self.nome = nome


class DependenciaDesconhecida(RuntimeError):
    """Indica um nome de dependência fora do conjunto conhecido pelo sistema."""

    def __init__(self, nome: str) -> None:
        """Identifica o nome desconhecido recebido e monta a mensagem em português."""

        super().__init__(
            f"A dependência '{nome}' é desconhecida. As dependências válidas são: "
            "backend, banco_dados, inmet, openai."
        )
        self.nome = nome
