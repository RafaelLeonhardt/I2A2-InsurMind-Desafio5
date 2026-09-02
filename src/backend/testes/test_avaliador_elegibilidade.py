"""Testes do `AvaliadorElegibilidade`: motor puro determinístico (ELEG-01..03)."""

from dataclasses import replace
from datetime import datetime
from uuid import uuid4

from central_preventiva.dominio.avaliador_elegibilidade import (
    MOTIVO_APOLICE_INATIVA,
    MOTIVO_APOLICE_INCOERENTE,
    MOTIVO_AREA_NAO_APLICAVEL,
    MOTIVO_COBERTURA_AUSENTE,
    MOTIVO_INCLUIDO,
    MOTIVO_NAO_PARTICIPA_DE_ALERTAS,
    CandidatoElegibilidade,
    avaliar,
)
from central_preventiva.dominio.avaliador_risco import RegraSnapshot
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)

AREA = "9990001"

REGRA_CHUVA = RegraSnapshot(
    id=uuid4(),
    evento_tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
    limiar_meteorologico=50.0,
    area_aplicavel=AREA,
    apolice_tipo="residencial",
    cobertura_exigida="alagamento",
    versao=1,
)

EVENTO_CHUVA = EventoMeteorologico(
    id=uuid4(),
    tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
    area=AREA,
    periodo_inicio=datetime(2026, 3, 10, 6, 0),
    periodo_fim=datetime(2026, 3, 10, 18, 0),
    intensidade=72.5,
    proveniencia=ProvenienciaEvento.SINTETICO,
    instante_observado=datetime(2026, 3, 9, 18, 0),
)

CANDIDATO_ELEGIVEL = CandidatoElegibilidade(
    segurado_id=uuid4(),
    apolice_id=uuid4(),
    nome_segurado="Pessoa Segurada Sintética",
    codigo_ibge_area=AREA,
    canal_preferido="whatsapp",
    participa_de_alertas=True,
    apolice_tipo="residencial",
    apolice_situacao="ativa",
    coberturas=("alagamento", "incendio"),
)


def test_candidato_que_atende_todos_os_criterios_e_incluido() -> None:
    resultado = avaliar(CANDIDATO_ELEGIVEL, EVENTO_CHUVA, REGRA_CHUVA)

    assert resultado.elegivel is True
    assert resultado.motivo == MOTIVO_INCLUIDO
    assert all(criterio.atende for criterio in resultado.criterios)
    assert len(resultado.criterios) == 5


def test_area_diferente_da_area_do_evento_exclui_com_motivo_especifico() -> None:
    candidato = replace(CANDIDATO_ELEGIVEL, codigo_ibge_area="9990099")

    resultado = avaliar(candidato, EVENTO_CHUVA, REGRA_CHUVA)

    assert resultado.elegivel is False
    assert resultado.motivo == MOTIVO_AREA_NAO_APLICAVEL
    criterio_area = next(c for c in resultado.criterios if c.operando == "área afetada")
    assert criterio_area.atende is False
    assert len(resultado.criterios) == 5


def test_tipo_de_apolice_incoerente_com_a_regra_exclui_com_motivo_especifico() -> None:
    candidato = replace(CANDIDATO_ELEGIVEL, apolice_tipo="automovel")

    resultado = avaliar(candidato, EVENTO_CHUVA, REGRA_CHUVA)

    assert resultado.elegivel is False
    assert resultado.motivo == MOTIVO_APOLICE_INCOERENTE
    assert len(resultado.criterios) == 5


def test_apolice_cancelada_exclui_com_motivo_especifico() -> None:
    candidato = replace(CANDIDATO_ELEGIVEL, apolice_situacao="cancelada")

    resultado = avaliar(candidato, EVENTO_CHUVA, REGRA_CHUVA)

    assert resultado.elegivel is False
    assert resultado.motivo == MOTIVO_APOLICE_INATIVA
    assert "cancelada" in resultado.justificativa
    assert len(resultado.criterios) == 5


def test_apolice_suspensa_exclui_com_motivo_especifico() -> None:
    candidato = replace(CANDIDATO_ELEGIVEL, apolice_situacao="suspensa")

    resultado = avaliar(candidato, EVENTO_CHUVA, REGRA_CHUVA)

    assert resultado.elegivel is False
    assert resultado.motivo == MOTIVO_APOLICE_INATIVA
    assert len(resultado.criterios) == 5


def test_cobertura_ausente_exclui_com_motivo_especifico() -> None:
    candidato = replace(CANDIDATO_ELEGIVEL, coberturas=("incendio",))

    resultado = avaliar(candidato, EVENTO_CHUVA, REGRA_CHUVA)

    assert resultado.elegivel is False
    assert resultado.motivo == MOTIVO_COBERTURA_AUSENTE
    assert len(resultado.criterios) == 5


def test_sem_nenhuma_participacao_de_alertas_exclui_independente_do_canal() -> None:
    """Independent Test da spec: participa_de_alertas=False exclui por si só,
    independentemente do canal preferencial configurado."""

    candidato = replace(
        CANDIDATO_ELEGIVEL, participa_de_alertas=False, canal_preferido="sms"
    )

    resultado = avaliar(candidato, EVENTO_CHUVA, REGRA_CHUVA)

    assert resultado.elegivel is False
    assert resultado.motivo == MOTIVO_NAO_PARTICIPA_DE_ALERTAS
    assert resultado.canal == "sms"
    assert len(resultado.criterios) == 5


def test_canal_preferencial_nao_altera_o_resultado_de_elegibilidade() -> None:
    candidato_whatsapp = replace(CANDIDATO_ELEGIVEL, canal_preferido="whatsapp")
    candidato_email = replace(CANDIDATO_ELEGIVEL, canal_preferido="email")

    resultado_whatsapp = avaliar(candidato_whatsapp, EVENTO_CHUVA, REGRA_CHUVA)
    resultado_email = avaliar(candidato_email, EVENTO_CHUVA, REGRA_CHUVA)

    assert resultado_whatsapp.elegivel == resultado_email.elegivel == True  # noqa: E712
    assert resultado_whatsapp.canal == "whatsapp"
    assert resultado_email.canal == "email"


def test_canal_preferencial_e_preservado_no_resultado_como_snapshot() -> None:
    candidato = replace(CANDIDATO_ELEGIVEL, canal_preferido="sms")

    resultado = avaliar(candidato, EVENTO_CHUVA, REGRA_CHUVA)

    assert resultado.canal == "sms"


def test_mesma_entrada_produz_resultado_identico() -> None:
    primeira = avaliar(CANDIDATO_ELEGIVEL, EVENTO_CHUVA, REGRA_CHUVA)
    segunda = avaliar(CANDIDATO_ELEGIVEL, EVENTO_CHUVA, REGRA_CHUVA)

    assert primeira == segunda


def test_granizo_avalia_contra_apolice_automovel() -> None:
    regra_granizo = RegraSnapshot(
        id=uuid4(),
        evento_tipo=TipoEventoMeteorologico.GRANIZO,
        limiar_meteorologico=20.0,
        area_aplicavel="9990002",
        apolice_tipo="automovel",
        cobertura_exigida="granizo",
        versao=1,
    )
    evento_granizo = EventoMeteorologico(
        id=uuid4(),
        tipo=TipoEventoMeteorologico.GRANIZO,
        area="9990002",
        periodo_inicio=datetime(2026, 3, 12, 14, 0),
        periodo_fim=datetime(2026, 3, 12, 20, 0),
        intensidade=31.0,
        proveniencia=ProvenienciaEvento.SINTETICO,
        instante_observado=datetime(2026, 3, 12, 8, 0),
    )
    candidato = CandidatoElegibilidade(
        segurado_id=uuid4(),
        apolice_id=uuid4(),
        nome_segurado="Pessoa Segurada Sintética",
        codigo_ibge_area="9990002",
        canal_preferido="sms",
        participa_de_alertas=True,
        apolice_tipo="automovel",
        apolice_situacao="ativa",
        coberturas=("granizo", "colisao"),
    )

    resultado = avaliar(candidato, evento_granizo, regra_granizo)

    assert resultado.elegivel is True
    assert resultado.motivo == MOTIVO_INCLUIDO
