"""Motor determinístico de avaliação de relevância meteorológica (AD-5: sem LLM)."""

from dataclasses import dataclass
from uuid import UUID

from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    TipoEventoMeteorologico,
)

MOTIVO_TIPO_NAO_SUPORTADO = "tipo_nao_suportado"
MOTIVO_AREA_NAO_APLICAVEL = "area_nao_aplicavel"
MOTIVO_ABAIXO_DO_LIMIAR = "abaixo_do_limiar"
MOTIVO_RELEVANTE = "relevante"
MOTIVO_SEM_REGRA_ATIVA = "sem_regra_ativa"
"""Motivo de `sem_risco` quando não há regra ativa para o tipo do evento (ServicoAvaliacaoRisco)."""


@dataclass(frozen=True, slots=True)
class RegraSnapshot:
    """Regra ativa consumida pelos avaliadores de risco (2.3) e elegibilidade (2.5).

    `cobertura_exigida` não é lida por `avaliar()` (relevância meteorológica não depende
    de cobertura de apólice) — existe aqui porque é a mesma regra ativa consumida por
    `AvaliadorElegibilidade` (2.5), que precisa dela para o critério de cobertura.
    """

    id: UUID
    evento_tipo: TipoEventoMeteorologico
    limiar_meteorologico: float
    area_aplicavel: str
    apolice_tipo: str
    cobertura_exigida: str
    versao: int


@dataclass(frozen=True, slots=True)
class Criterio:
    """Um critério avaliado: o que foi comparado, o valor observado e o resultado."""

    operando: str
    valor_observado: str
    atende: bool
    justificativa: str


@dataclass(frozen=True, slots=True)
class ResultadoAvaliacaoRisco:
    """Resultado determinístico da avaliação: relevância, critérios e motivo."""

    relevante: bool
    criterios: tuple[Criterio, ...]
    motivo: str


def _rejeitar_tipo_nao_suportado(evento: EventoMeteorologico) -> ResultadoAvaliacaoRisco:
    """Constrói o resultado para um tipo de evento fora dos suportados (RISCO-04)."""

    return ResultadoAvaliacaoRisco(
        relevante=False,
        criterios=(
            Criterio(
                operando="tipo de evento",
                valor_observado=str(evento.tipo),
                atende=False,
                justificativa="Somente chuva_intensa e granizo são tipos suportados.",
            ),
        ),
        motivo=MOTIVO_TIPO_NAO_SUPORTADO,
    )


def _avaliar_area(evento: EventoMeteorologico, regra: RegraSnapshot) -> Criterio:
    """Compara a área do evento com a área aplicável da regra (edge case: área não reconhecida)."""

    atende = evento.area == regra.area_aplicavel
    justificativa = (
        f"Área do evento corresponde à área aplicável da regra ({regra.area_aplicavel})."
        if atende
        else f"Área do evento não corresponde à área aplicável da regra "
        f"({regra.area_aplicavel})."
    )
    return Criterio(
        operando="área aplicável",
        valor_observado=evento.area,
        atende=atende,
        justificativa=justificativa,
    )


def avaliar(evento: EventoMeteorologico, regra: RegraSnapshot) -> ResultadoAvaliacaoRisco:
    """Compara o evento à regra ativa e devolve relevância determinística (RISCO-01..08).

    Função pura, sem I/O e sem estado: a mesma entrada sempre produz a mesma saída
    (RISCO-06/07), e nenhum caminho consulta IA ou heurística probabilística (RISCO-08).
    """

    if evento.tipo not in (TipoEventoMeteorologico.CHUVA_INTENSA, TipoEventoMeteorologico.GRANIZO):
        return _rejeitar_tipo_nao_suportado(evento)

    criterio_area = _avaliar_area(evento, regra)

    if evento.tipo == TipoEventoMeteorologico.CHUVA_INTENSA:
        atende_intensidade = evento.intensidade >= regra.limiar_meteorologico
        criterio_intensidade = Criterio(
            operando="intensidade (mm acumulados no período)",
            valor_observado=f"{evento.intensidade} mm",
            atende=atende_intensidade,
            justificativa=(
                f"Intensidade observada atinge o limiar de {regra.limiar_meteorologico} mm "
                "(fronteira inclusiva)."
                if atende_intensidade
                else f"Intensidade observada fica abaixo do limiar de "
                f"{regra.limiar_meteorologico} mm."
            ),
        )
        criterios = (criterio_area, criterio_intensidade)
        relevante = criterio_area.atende and criterio_intensidade.atende
        if not relevante:
            motivo = (
                MOTIVO_AREA_NAO_APLICAVEL if not criterio_area.atende else MOTIVO_ABAIXO_DO_LIMIAR
            )
        else:
            motivo = MOTIVO_RELEVANTE
        return ResultadoAvaliacaoRisco(relevante=relevante, criterios=criterios, motivo=motivo)

    criterio_ocorrencia = Criterio(
        operando="ocorrência de granizo",
        valor_observado=str(evento.tipo),
        atende=True,
        justificativa="Granizo é relevante por ocorrência, sem limiar de intensidade adicional.",
    )
    criterios = (criterio_area, criterio_ocorrencia)
    relevante = criterio_area.atende
    motivo = MOTIVO_RELEVANTE if relevante else MOTIVO_AREA_NAO_APLICAVEL
    return ResultadoAvaliacaoRisco(relevante=relevante, criterios=criterios, motivo=motivo)
