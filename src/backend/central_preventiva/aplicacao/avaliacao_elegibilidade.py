"""Caso de uso de formação e explicação do público elegível (ELEG-04, ELEG-08)."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from central_preventiva.dominio import avaliador_elegibilidade
from central_preventiva.dominio.avaliador_elegibilidade import (
    CandidatoElegibilidade,
    ResultadoElegibilidade,
)
from central_preventiva.dominio.avaliador_risco import RegraSnapshot
from central_preventiva.dominio.evento_meteorologico import EventoMeteorologico


class _ContagemElegibilidade(Protocol):
    """Forma mínima da contagem devolvida por `contar_por_execucao`."""

    @property
    def incluidos(self) -> int: ...
    @property
    def excluidos(self) -> int: ...


class _RepositorioCandidatosElegibilidade(Protocol):
    """Porta mínima de leitura de candidatos de que este caso de uso depende."""

    def listar_candidatos(self, area: str) -> list[CandidatoElegibilidade]:
        """Lista todo segurado+apólice com apólice na área informada."""
        ...


class _RepositorioElegibilidades(Protocol):
    """Porta mínima de persistência de resultados de que este caso de uso depende."""

    def salvar(
        self,
        execucao_id: UUID,
        evento_id: UUID,
        regra_id: UUID,
        segurado_id: UUID,
        apolice_id: UUID,
        nome_segurado: str,
        resultado: ResultadoElegibilidade,
    ) -> UUID | None:
        """Persiste o resultado da combinação, ou `None` se já existir."""
        ...

    def contar_por_execucao(self, execucao_id: UUID) -> _ContagemElegibilidade:
        """Conta incluídos/excluídos já persistidos para a execução informada."""
        ...


@dataclass(frozen=True, slots=True)
class PortasAvaliacaoElegibilidade:
    """Agrupa as portas de que o caso de uso de avaliação de elegibilidade depende."""

    candidatos: _RepositorioCandidatosElegibilidade
    elegibilidades: _RepositorioElegibilidades
    avaliar: Callable[
        [CandidatoElegibilidade, EventoMeteorologico, RegraSnapshot], ResultadoElegibilidade
    ] = avaliador_elegibilidade.avaliar


class ServicoAvaliacaoElegibilidade:
    """Orquestra candidatos → avaliação → persistência → contagem, por evento relevante."""

    def __init__(self, portas: PortasAvaliacaoElegibilidade) -> None:
        """Guarda as portas de que este caso de uso depende."""

        self._portas = portas

    def avaliar_publico(
        self, execucao_id: UUID, evento: EventoMeteorologico, regra: RegraSnapshot
    ) -> _ContagemElegibilidade:
        """Avalia todos os candidatos da área do evento e devolve a contagem final.

        Um evento sem nenhum candidato (ou sem nenhum elegível) termina em conjunto
        vazio válido — nenhuma porta de IA existe para ser chamada (AD-5). Reprocessar
        a mesma execução não duplica nenhum resultado: `salvar` deduz por `UNIQUE`
        (AD-10), então repetir esta chamada é sempre seguro (idempotente por natureza
        do schema, não por `Idempotency-Key`).
        """

        candidatos = self._portas.candidatos.listar_candidatos(evento.area)
        for candidato in candidatos:
            resultado = self._portas.avaliar(candidato, evento, regra)
            self._portas.elegibilidades.salvar(
                execucao_id,
                evento.id,
                regra.id,
                candidato.segurado_id,
                candidato.apolice_id,
                candidato.nome_segurado,
                resultado,
            )
        return self._portas.elegibilidades.contar_por_execucao(execucao_id)
