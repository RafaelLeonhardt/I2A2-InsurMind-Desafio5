"""Motor determinístico de avaliação de elegibilidade ao público preventivo (AD-5: sem LLM)."""

from dataclasses import dataclass
from uuid import UUID

from central_preventiva.dominio.avaliador_risco import Criterio, RegraSnapshot
from central_preventiva.dominio.evento_meteorologico import EventoMeteorologico

MOTIVO_AREA_NAO_APLICAVEL = "area_nao_aplicavel"
MOTIVO_APOLICE_INCOERENTE = "apolice_incoerente"
MOTIVO_APOLICE_INATIVA = "apolice_inativa"
MOTIVO_COBERTURA_AUSENTE = "cobertura_ausente"
MOTIVO_NAO_PARTICIPA_DE_ALERTAS = "nao_participa_de_alertas"
MOTIVO_INCLUIDO = "incluido"

OPERANDO_AREA_AFETADA = "área afetada"
"""Nome estável do critério de área — usado por `RepositorioElegibilidades` para derivar
`codigo_ibge_area` do próprio snapshot de critérios já persistido, por nome, nunca por
posição (a ordem dos critérios é um detalhe de `avaliar`, não um contrato)."""

OPERANDO_COBERTURA_EXIGIDA = "cobertura exigida"
"""Nome estável do critério de cobertura — usado por `montador_contexto_agente` para derivar
as coberturas relevantes do mesmo snapshot já persistido, pela mesma regra de busca por nome."""


@dataclass(frozen=True, slots=True)
class CandidatoElegibilidade:
    """Um segurado e uma de suas apólices, candidatos a uma combinação avaliável.

    Campos planos (não dois objetos `Segurado`/`Apolice` aninhados) porque o avaliador
    sempre decide sobre o par completo — nunca um sem o outro (cada combinação
    segurado+apólice é uma linha de resultado distinta, spec.md Edge Cases).
    """

    segurado_id: UUID
    apolice_id: UUID
    nome_segurado: str
    codigo_ibge_area: str
    canal_preferido: str
    participa_de_alertas: bool
    apolice_tipo: str
    apolice_situacao: str
    coberturas: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ResultadoElegibilidade:
    """Resultado determinístico da avaliação: elegibilidade, critérios, canal e motivo."""

    elegivel: bool
    criterios: tuple[Criterio, ...]
    canal: str
    motivo: str
    justificativa: str


def _criterio_area(candidato: CandidatoElegibilidade, evento: EventoMeteorologico) -> Criterio:
    atende = candidato.codigo_ibge_area == evento.area
    justificativa = (
        f"Área da apólice corresponde à área do evento ({evento.area})."
        if atende
        else f"Área da apólice não corresponde à área do evento ({evento.area})."
    )
    return Criterio(
        operando=OPERANDO_AREA_AFETADA,
        valor_observado=candidato.codigo_ibge_area,
        atende=atende,
        justificativa=justificativa,
    )


def _criterio_tipo_apolice(candidato: CandidatoElegibilidade, regra: RegraSnapshot) -> Criterio:
    atende = candidato.apolice_tipo == regra.apolice_tipo
    justificativa = (
        f"Tipo de apólice corresponde ao exigido pela regra ({regra.apolice_tipo})."
        if atende
        else f"Tipo de apólice ({candidato.apolice_tipo}) não corresponde ao exigido "
        f"pela regra ({regra.apolice_tipo})."
    )
    return Criterio(
        operando="tipo da apólice",
        valor_observado=candidato.apolice_tipo,
        atende=atende,
        justificativa=justificativa,
    )


def _criterio_situacao_apolice(candidato: CandidatoElegibilidade) -> Criterio:
    atende = candidato.apolice_situacao == "ativa"
    justificativa = (
        "Apólice está ativa."
        if atende
        else f"Apólice não está ativa (situação: {candidato.apolice_situacao})."
    )
    return Criterio(
        operando="situação da apólice",
        valor_observado=candidato.apolice_situacao,
        atende=atende,
        justificativa=justificativa,
    )


def _criterio_cobertura(candidato: CandidatoElegibilidade, regra: RegraSnapshot) -> Criterio:
    atende = regra.cobertura_exigida in candidato.coberturas
    justificativa = (
        f"Apólice possui a cobertura exigida ({regra.cobertura_exigida})."
        if atende
        else f"Apólice não possui a cobertura exigida pela regra ({regra.cobertura_exigida})."
    )
    return Criterio(
        operando=OPERANDO_COBERTURA_EXIGIDA,
        valor_observado=", ".join(candidato.coberturas) if candidato.coberturas else "nenhuma",
        atende=atende,
        justificativa=justificativa,
    )


def _criterio_participa_de_alertas(candidato: CandidatoElegibilidade) -> Criterio:
    atende = candidato.participa_de_alertas
    justificativa = (
        "Segurado participa de alertas preventivos."
        if atende
        else "Segurado optou por não participar de alertas preventivos."
    )
    return Criterio(
        operando="participação em alertas",
        valor_observado=str(candidato.participa_de_alertas),
        atende=atende,
        justificativa=justificativa,
    )


def _motivo_da_primeira_falha(criterios: tuple[Criterio, ...]) -> str:
    """Resolve o motivo tipado a partir do primeiro critério não atendido, em ordem fixa."""

    operando_para_motivo = {
        OPERANDO_AREA_AFETADA: MOTIVO_AREA_NAO_APLICAVEL,
        "tipo da apólice": MOTIVO_APOLICE_INCOERENTE,
        "situação da apólice": MOTIVO_APOLICE_INATIVA,
        OPERANDO_COBERTURA_EXIGIDA: MOTIVO_COBERTURA_AUSENTE,
        "participação em alertas": MOTIVO_NAO_PARTICIPA_DE_ALERTAS,
    }
    primeira_falha = next(criterio for criterio in criterios if not criterio.atende)
    return operando_para_motivo[primeira_falha.operando]


def avaliar(
    candidato: CandidatoElegibilidade, evento: EventoMeteorologico, regra: RegraSnapshot
) -> ResultadoElegibilidade:
    """Avalia a combinação segurado+apólice contra a regra ativa (ELEG-01..03).

    Função pura, sem I/O e sem estado: a mesma entrada sempre produz a mesma saída, e
    nenhum caminho consulta IA ou heurística probabilística (AD-5). Canal preferencial é
    preservado no resultado (`canal`), mas nunca participa da decisão de elegibilidade —
    é lido, nunca comparado.
    """

    criterios = (
        _criterio_area(candidato, evento),
        _criterio_tipo_apolice(candidato, regra),
        _criterio_situacao_apolice(candidato),
        _criterio_cobertura(candidato, regra),
        _criterio_participa_de_alertas(candidato),
    )
    elegivel = all(criterio.atende for criterio in criterios)
    if elegivel:
        motivo = MOTIVO_INCLUIDO
        justificativa = "Segurado e apólice atendem integralmente aos critérios da regra ativa."
    else:
        motivo = _motivo_da_primeira_falha(criterios)
        justificativa = next(
            criterio.justificativa for criterio in criterios if not criterio.atende
        )
    return ResultadoElegibilidade(
        elegivel=elegivel,
        criterios=criterios,
        canal=candidato.canal_preferido,
        motivo=motivo,
        justificativa=justificativa,
    )
