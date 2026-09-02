"""Testes do `AvaliadorRisco`: motor determinístico de relevância meteorológica (RISCO-01..08)."""

from datetime import datetime
from uuid import uuid4

from central_preventiva.dominio.avaliador_risco import (
    MOTIVO_ABAIXO_DO_LIMIAR,
    MOTIVO_AREA_NAO_APLICAVEL,
    MOTIVO_RELEVANTE,
    MOTIVO_TIPO_NAO_SUPORTADO,
    RegraSnapshot,
    avaliar,
)
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)

AREA = "9990001"
AREA_OUTRA = "9990099"

REGRA_CHUVA = RegraSnapshot(
    id=uuid4(),
    evento_tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
    limiar_meteorologico=50.0,
    area_aplicavel=AREA,
    apolice_tipo="residencial",
    cobertura_exigida="alagamento",
    versao=1,
)

REGRA_GRANIZO = RegraSnapshot(
    id=uuid4(),
    evento_tipo=TipoEventoMeteorologico.GRANIZO,
    limiar_meteorologico=20.0,
    area_aplicavel=AREA,
    apolice_tipo="automovel",
    cobertura_exigida="granizo",
    versao=1,
)


def evento_chuva(intensidade: float, area: str = AREA) -> EventoMeteorologico:
    return EventoMeteorologico(
        id=uuid4(),
        tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
        area=area,
        periodo_inicio=datetime(2026, 8, 30, 17, 0),
        periodo_fim=datetime(2026, 8, 30, 18, 0),
        intensidade=intensidade,
        proveniencia=ProvenienciaEvento.REAL_INMET,
        instante_observado=datetime(2026, 8, 30, 18, 0),
    )


def evento_granizo(area: str = AREA) -> EventoMeteorologico:
    return EventoMeteorologico(
        id=uuid4(),
        tipo=TipoEventoMeteorologico.GRANIZO,
        area=area,
        periodo_inicio=datetime(2026, 3, 12, 14, 0),
        periodo_fim=datetime(2026, 3, 12, 20, 0),
        intensidade=31.0,
        proveniencia=ProvenienciaEvento.SINTETICO,
        instante_observado=datetime(2026, 3, 12, 8, 0),
    )


def test_chuva_abaixo_do_limiar_nao_e_relevante() -> None:
    resultado = avaliar(evento_chuva(49.9), REGRA_CHUVA)

    assert resultado.relevante is False
    assert resultado.motivo == MOTIVO_ABAIXO_DO_LIMIAR
    criterio_intensidade = next(c for c in resultado.criterios if "intensidade" in c.operando)
    assert criterio_intensidade.atende is False
    assert criterio_intensidade.valor_observado == "49.9 mm"


def test_chuva_no_limiar_exato_e_relevante_fronteira_inclusiva() -> None:
    resultado = avaliar(evento_chuva(50.0), REGRA_CHUVA)

    assert resultado.relevante is True
    assert resultado.motivo == MOTIVO_RELEVANTE


def test_chuva_acima_do_limiar_e_relevante() -> None:
    resultado = avaliar(evento_chuva(50.1), REGRA_CHUVA)

    assert resultado.relevante is True
    assert resultado.motivo == MOTIVO_RELEVANTE


def test_chuva_fora_da_area_aplicavel_nao_e_relevante_sem_erro() -> None:
    resultado = avaliar(evento_chuva(99.0, area=AREA_OUTRA), REGRA_CHUVA)

    assert resultado.relevante is False
    assert resultado.motivo == MOTIVO_AREA_NAO_APLICAVEL
    criterio_area = next(c for c in resultado.criterios if c.operando == "área aplicável")
    assert criterio_area.atende is False
    assert criterio_area.valor_observado == AREA_OUTRA


def test_granizo_com_area_aplicavel_e_sempre_relevante_por_ocorrencia() -> None:
    resultado = avaliar(evento_granizo(), REGRA_GRANIZO)

    assert resultado.relevante is True
    assert resultado.motivo == MOTIVO_RELEVANTE
    criterio_ocorrencia = next(c for c in resultado.criterios if "ocorrência" in c.operando)
    assert criterio_ocorrencia.atende is True


def test_granizo_fora_da_area_aplicavel_nao_e_relevante() -> None:
    resultado = avaliar(evento_granizo(area=AREA_OUTRA), REGRA_GRANIZO)

    assert resultado.relevante is False
    assert resultado.motivo == MOTIVO_AREA_NAO_APLICAVEL


def test_tipo_nao_suportado_retorna_resultado_nao_suportado_sem_avaliar_limiar() -> None:
    evento_invalido = EventoMeteorologico(
        id=uuid4(),
        tipo="vendaval",  # type: ignore[arg-type]
        area=AREA,
        periodo_inicio=datetime(2026, 8, 30, 17, 0),
        periodo_fim=datetime(2026, 8, 30, 18, 0),
        intensidade=999.0,
        proveniencia=ProvenienciaEvento.REAL_INMET,
        instante_observado=datetime(2026, 8, 30, 18, 0),
    )

    resultado = avaliar(evento_invalido, REGRA_CHUVA)

    assert resultado.relevante is False
    assert resultado.motivo == MOTIVO_TIPO_NAO_SUPORTADO
    assert len(resultado.criterios) == 1


def test_mesma_entrada_avaliada_duas_vezes_produz_resultado_identico() -> None:
    evento = evento_chuva(72.5)

    primeira = avaliar(evento, REGRA_CHUVA)
    segunda = avaliar(evento, REGRA_CHUVA)

    assert primeira == segunda
