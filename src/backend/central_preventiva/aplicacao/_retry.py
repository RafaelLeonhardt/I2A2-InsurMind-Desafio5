"""Política única de retry com backoff das integrações externas (AD-8).

Um só lugar decide quantas tentativas uma integração externa tem e quanto se espera
entre elas. `ColetorComRetry` (2.2, INMET) e `ServicoPreflightIA` (3.1, OpenAI) usam
este wrapper em vez de reimplementar a mesma política.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

MAXIMO_TENTATIVAS = 3
"""Número total de tentativas de uma operação com retry, incluindo a primeira (AD-8)."""

BACKOFF_SEGUNDOS: tuple[float, ...] = (1.0, 2.0, 4.0)
"""Espera exponencial com jitter nulo entre tentativas: 1s após a 1ª falha, 2s após a 2ª."""


class TentativasEsgotadas(Exception):
    """Indica que as `MAXIMO_TENTATIVAS` tentativas de uma operação se esgotaram.

    Carrega a última causa observada: o erro reconhecido da última tentativa, ou o
    último valor recusado por `aceitar` — cabe ao chamador decidir o motivo de falha.
    """

    def __init__(
        self,
        mensagem: str,
        tentativas: int,
        ultimo_erro: BaseException | None,
        ultimo_valor: object | None,
    ) -> None:
        """Registra quantas tentativas ocorreram e a última causa de falha observada."""

        super().__init__(mensagem)
        self.tentativas = tentativas
        self.ultimo_erro = ultimo_erro
        self.ultimo_valor = ultimo_valor


@dataclass(frozen=True, slots=True)
class Tentativa[T]:
    """Desfecho de uma tentativa individual, entregue ao registro do chamador."""

    numero: int
    valor: T | None
    erro: BaseException | None
    iniciado_em: datetime
    finalizado_em: datetime


class RetryComBackoff[T]:
    """Repete uma operação assíncrona até `MAXIMO_TENTATIVAS`, com `BACKOFF_SEGUNDOS`.

    Parametrizada por quatro decisões do chamador: `operacao` (o que tentar),
    `aceitar` (se o valor devolvido conta como sucesso), `registrar` (o que persistir
    ao fim de cada tentativa) e `erros_reconhecidos` (quais exceções consomem uma
    tentativa em vez de propagar). Um erro fora dessa tupla propaga imediatamente,
    sem consumir tentativas nem registrar nada.
    """

    def __init__(
        self,
        operacao: Callable[[], Awaitable[T]],
        aceitar: Callable[[T], bool],
        registrar: Callable[[Tentativa[T]], None],
        mensagem_esgotamento: str,
        erros_reconhecidos: tuple[type[BaseException], ...] = (),
        esperar: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        """Guarda a operação, suas decisões de aceite/registro e o relógio injetável."""

        self._operacao = operacao
        self._aceitar = aceitar
        self._registrar = registrar
        self._mensagem_esgotamento = mensagem_esgotamento
        self._erros_reconhecidos = erros_reconhecidos
        self._esperar = esperar

    async def executar(self) -> T:
        """Tenta até `MAXIMO_TENTATIVAS` vezes e devolve o primeiro valor aceito.

        Levanta `TentativasEsgotadas` quando todas as tentativas falham, carregando a
        última causa observada. Não espera depois da última tentativa.
        """

        ultimo_erro: BaseException | None = None
        ultimo_valor: T | None = None

        for numero in range(1, MAXIMO_TENTATIVAS + 1):
            iniciado_em = datetime.now(UTC)
            try:
                valor = await self._operacao()
            except self._erros_reconhecidos as erro:
                self._registrar(
                    Tentativa(numero, None, erro, iniciado_em, datetime.now(UTC))
                )
                ultimo_erro, ultimo_valor = erro, None
            else:
                self._registrar(
                    Tentativa(numero, valor, None, iniciado_em, datetime.now(UTC))
                )
                if self._aceitar(valor):
                    return valor
                ultimo_erro, ultimo_valor = None, valor

            if numero < MAXIMO_TENTATIVAS:
                await self._esperar(BACKOFF_SEGUNDOS[numero - 1])

        raise TentativasEsgotadas(
            self._mensagem_esgotamento, MAXIMO_TENTATIVAS, ultimo_erro, ultimo_valor
        )
