"""Testes do `AdaptadorCenarioSintetico`: payload determinístico normalizado como sintético."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

from central_preventiva.adaptadores.meteorologia.adaptador_cenario_sintetico import (
    AdaptadorCenarioSintetico,
)
from central_preventiva.adaptadores.meteorologia.normalizador_inmet import NormalizadorInmet
from central_preventiva.aplicacao.portas_meteorologia import AreaMonitorada
from central_preventiva.dominio.evento_meteorologico import (
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)

AREA = AreaMonitorada(
    id=uuid4(),
    codigo_estacao_inmet="A702",
    nome_estacao="Estação Sintética Demo",
    codigo_ibge_area="9990002",
    ativa=True,
)

RELOGIO_FIXO = datetime(2026, 9, 1, 20, 0, 0, tzinfo=UTC)


def test_coletar_devolve_payload_deterministico_do_cenario() -> None:
    adaptador = AdaptadorCenarioSintetico(agora=lambda: RELOGIO_FIXO)

    resposta = asyncio.run(adaptador.coletar(AREA))
    resposta_repetida = asyncio.run(adaptador.coletar(AREA))

    assert resposta.status_code == 200
    assert resposta == resposta_repetida


def test_payload_normalizado_pelo_normalizador_de_2_1_resulta_em_provenencia_sintetico() -> None:
    adaptador = AdaptadorCenarioSintetico(agora=lambda: RELOGIO_FIXO)

    bruta = asyncio.run(adaptador.coletar(AREA))
    resultado = NormalizadorInmet().normalizar(bruta, AREA)

    assert resultado.motivo_rejeicao is None
    assert resultado.evento is not None
    assert resultado.evento.tipo == TipoEventoMeteorologico.GRANIZO
    assert resultado.evento.proveniencia == ProvenienciaEvento.SINTETICO
    assert resultado.evento.area == AREA.codigo_ibge_area
