"""Caso de uso de avaliação de relevância meteorológica (RISCO-09, RISCO-10)."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from central_preventiva.dominio import avaliador_risco
from central_preventiva.dominio.avaliador_risco import (
    MOTIVO_SEM_REGRA_ATIVA,
    RegraSnapshot,
    ResultadoAvaliacaoRisco,
)
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    TipoEventoMeteorologico,
)


class _RepositorioRegras(Protocol):
    """Porta mínima de leitura de regras de que este caso de uso depende."""

    def obter_ativa(self, evento_tipo: TipoEventoMeteorologico) -> RegraSnapshot | None:
        """Resolve a regra ativa para o tipo de evento informado."""
        ...


class _RepositorioAvaliacoesRisco(Protocol):
    """Porta mínima de persistência do snapshot de avaliação de que este caso de uso depende."""

    def salvar(
        self,
        execucao_id: UUID,
        evento_id: UUID,
        regra_id: UUID,
        regra_versao: int,
        resultado: ResultadoAvaliacaoRisco,
    ) -> UUID:
        """Persiste o snapshot completo da avaliação."""
        ...


class _RepositorioExecucaoPreventiva(Protocol):
    """Porta mínima de `execucao_preventiva` de que este caso de uso depende (AD-008)."""

    def transicionar(
        self, execucao_id: UUID, versao_esperada: int, novo_estado: EstadoExecucao
    ) -> None:
        """Transiciona a execução sob checagem otimista de versão."""
        ...


@dataclass(frozen=True, slots=True)
class PortasAvaliacaoRisco:
    """Agrupa as portas de que o caso de uso de avaliação de risco depende."""

    regras: _RepositorioRegras
    avaliacoes: _RepositorioAvaliacoesRisco
    execucoes: _RepositorioExecucaoPreventiva
    avaliar: Callable[
        [EventoMeteorologico, RegraSnapshot], ResultadoAvaliacaoRisco
    ] = avaliador_risco.avaliar


class ServicoAvaliacaoRisco:
    """Orquestra a obtenção da regra ativa, a avaliação e a transição de estado."""

    def __init__(self, portas: PortasAvaliacaoRisco) -> None:
        """Guarda as portas de que este caso de uso depende."""

        self._portas = portas

    def avaliar_evento(
        self, execucao_id: UUID, versao_esperada: int, evento: EventoMeteorologico
    ) -> ResultadoAvaliacaoRisco:
        """Avalia o evento contra a regra ativa e transiciona a execução de acordo.

        Sem regra ativa para o tipo do evento, a execução termina em `sem_risco` com
        motivo específico, sem persistir snapshot (não há regra a referenciar) e sem
        criar elegibilidade, mensagem ou chamada de IA — mesmo efeito de um evento
        que não atinge os critérios.
        """

        regra = self._portas.regras.obter_ativa(evento.tipo)
        if regra is None:
            resultado = ResultadoAvaliacaoRisco(
                relevante=False, criterios=(), motivo=MOTIVO_SEM_REGRA_ATIVA
            )
            self._portas.execucoes.transicionar(
                execucao_id, versao_esperada, EstadoExecucao.SEM_RISCO
            )
            return resultado

        resultado = self._portas.avaliar(evento, regra)
        self._portas.avaliacoes.salvar(execucao_id, evento.id, regra.id, regra.versao, resultado)

        novo_estado = (
            EstadoExecucao.AVALIANDO_ELEGIBILIDADE
            if resultado.relevante
            else EstadoExecucao.SEM_RISCO
        )
        self._portas.execucoes.transicionar(execucao_id, versao_esperada, novo_estado)
        return resultado
