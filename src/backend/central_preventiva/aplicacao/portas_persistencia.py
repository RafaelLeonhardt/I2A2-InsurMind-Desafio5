"""Portas de persistência e tipos compartilhados da inicialização e da restauração."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol


@dataclass(frozen=True, slots=True)
class ResultadoMigracao:
    """Descreve o que a aplicação de migrações pendentes efetivamente executou."""

    versoes_aplicadas: tuple[int, ...]
    versao_final: int


@dataclass(frozen=True, slots=True)
class ResultadoInicializacao:
    """Relata se a inicialização preparou o banco ou se ele já estava preparado."""

    estado: Literal["inicializado", "ja_preparado"]
    versoes_aplicadas: tuple[int, ...]
    semeado_agora: bool


@dataclass(frozen=True, slots=True)
class ResultadoRestauracao:
    """Resposta pública da restauração dos dados sintéticos."""

    status: Literal["restaurado"]
    restaurado_em: datetime


@dataclass(frozen=True, slots=True)
class RespostaRegistrada:
    """Resposta já registrada para uma chave de idempotência."""

    hash_requisicao: str
    status: int
    corpo: str


class VersaoSchemaFutura(RuntimeError):
    """Indica banco em versão mais nova do que o código em execução conhece."""

    def __init__(self, versao_registrada: int, versao_conhecida: int) -> None:
        """Registra as versões divergentes e monta a mensagem em português."""

        super().__init__(
            f"O banco está na versão de schema {versao_registrada}, mais nova que a versão "
            f"{versao_conhecida} conhecida por este código. Atualize a aplicação antes de "
            "executar a inicialização."
        )
        self.versao_registrada = versao_registrada
        self.versao_conhecida = versao_conhecida


class MigracoesPendentes(RuntimeError):
    """Indica migrações versionadas ainda não aplicadas ao banco operacional."""

    def __init__(self, versao_registrada: int | None, versao_conhecida: int) -> None:
        """Registra a defasagem de versões e monta a mensagem em português."""

        registrada = "nenhuma" if versao_registrada is None else str(versao_registrada)
        super().__init__(
            f"Há migrações pendentes: versão registrada {registrada}, versão conhecida "
            f"{versao_conhecida}. Execute o comando de inicialização antes de iniciar o servidor."
        )
        self.versao_registrada = versao_registrada
        self.versao_conhecida = versao_conhecida


class MigracaoFalhou(RuntimeError):
    """Indica a migração que falhou durante a aplicação em sequência."""

    def __init__(self, versao: int, descricao: str, causa: str) -> None:
        """Identifica a migração falha e preserva a causa original como texto."""

        super().__init__(
            f"A migração {versao} ({descricao}) falhou e não foi registrada: {causa}. "
            "As migrações anteriores permanecem aplicadas."
        )
        self.versao = versao
        self.descricao = descricao
        self.causa = causa


class RegistroMigracoesInvalido(RuntimeError):
    """Indica banco existente sem a tabela `schema_migracoes` íntegra."""

    def __init__(self, detalhe: str) -> None:
        """Recusa presumir o estado do schema e explica o motivo em português."""

        super().__init__(
            f"O registro de migrações do banco está ausente ou corrompido: {detalhe}. "
            "Recrie o banco a partir das migrações versionadas."
        )
        self.detalhe = detalhe


class ExecucaoAtivaImpedeRestauracao(RuntimeError):
    """Indica execução preventiva em estado não terminal no momento da restauração."""

    def __init__(self) -> None:
        """Monta a mensagem em português da recusa por execução ativa."""

        super().__init__(
            "Uma execução ativa impede a restauração. Aguarde a conclusão da execução em "
            "andamento e tente novamente."
        )


class ConflitoIdempotencia(RuntimeError):
    """Indica reuso da mesma chave de idempotência com conteúdo de requisição diferente."""

    def __init__(self, chave: str, operacao: str) -> None:
        """Registra a chave conflitante e monta a mensagem em português."""

        super().__init__(
            "A chave de idempotência já foi usada com um conteúdo de requisição diferente; "
            "nenhuma restauração foi executada."
        )
        self.chave = chave
        self.operacao = operacao


class NaoInicializado(RuntimeError):
    """Indica restauração solicitada antes de qualquer inicialização bem-sucedida."""

    def __init__(self) -> None:
        """Orienta a executar a inicialização antes da restauração."""

        super().__init__(
            "Os dados sintéticos ainda não foram inicializados. Execute o comando de "
            "inicialização antes de solicitar a restauração."
        )


class PortaMigracoes(Protocol):
    """Aplica e consulta as migrações versionadas do banco operacional."""

    def versao_registrada(self) -> int | None:
        """Retorna a maior versão registrada no banco, ou `None` se não houver registro."""
        ...

    def versao_conhecida(self) -> int:
        """Retorna a maior versão de migração conhecida pelo código em execução."""
        ...

    def aplicar_pendentes(self) -> ResultadoMigracao:
        """Aplica as migrações pendentes em ordem, cada uma em sua própria transação."""
        ...


class PortaDadosSinteticos(Protocol):
    """Semeia e restaura o conjunto sintético de referência da demonstração."""

    def esta_semeado(self) -> bool:
        """Informa se o conjunto sintético de referência já está presente."""
        ...

    def semear(self) -> None:
        """Insere o conjunto sintético de referência em uma única transação."""
        ...

    def restaurar(self) -> None:
        """Repõe o conjunto sintético de referência em uma única transação."""
        ...


class PortaExecucoes(Protocol):
    """Consulta o estado das execuções preventivas registradas."""

    def existe_execucao_nao_terminal(self) -> bool:
        """Informa se há ao menos uma execução preventiva em estado não terminal."""
        ...


class PortaIdempotencia(Protocol):
    """Guarda e recupera respostas associadas a uma chave de idempotência."""

    def buscar(self, chave: str, operacao: str) -> RespostaRegistrada | None:
        """Retorna a resposta registrada para o par chave/operação, se existir."""
        ...

    def registrar(
        self,
        chave: str,
        operacao: str,
        hash_requisicao: str,
        status: int,
        corpo: str,
    ) -> None:
        """Registra a resposta produzida para o par chave/operação."""
        ...
