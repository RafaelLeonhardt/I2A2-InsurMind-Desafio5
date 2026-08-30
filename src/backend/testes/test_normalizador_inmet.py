"""Testes determinísticos de parsing do `NormalizadorInmet`, sem nenhuma chamada de rede."""

import json
from pathlib import Path
from uuid import uuid4

from central_preventiva.adaptadores.meteorologia.normalizador_inmet import (
    MotivoRejeicao,
    NormalizadorInmet,
)
from central_preventiva.aplicacao.portas_meteorologia import AreaMonitorada, RespostaColetaInmet
from central_preventiva.dominio.evento_meteorologico import (
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)

DIRETORIO_FIXTURES = Path(__file__).parent / "fixtures" / "inmet"

AREA_MONITORADA = AreaMonitorada(
    id=uuid4(),
    codigo_estacao_inmet="A701",
    nome_estacao="Estação Sintética Demo",
    codigo_ibge_area="9990001",
    ativa=True,
)


def carregar_fixture(nome: str) -> dict[str, object]:
    """Carrega uma amostra congelada de `testes/fixtures/inmet/` como dicionário."""

    return json.loads((DIRETORIO_FIXTURES / nome).read_text(encoding="utf-8"))


def test_leitura_real_valida_normaliza_para_chuva_intensa_real_inmet() -> None:
    bruta = RespostaColetaInmet(status_code=200, corpo=carregar_fixture("leitura_chuva_valida.json"))

    resultado = NormalizadorInmet().normalizar(bruta, AREA_MONITORADA)

    assert resultado.motivo_rejeicao is None
    assert resultado.evento is not None
    assert resultado.evento.tipo == TipoEventoMeteorologico.CHUVA_INTENSA
    assert resultado.evento.proveniencia == ProvenienciaEvento.REAL_INMET
    assert resultado.evento.area == AREA_MONITORADA.codigo_ibge_area
    assert resultado.evento.intensidade == 55.4


def test_cenario_sintetico_granizo_normaliza_para_tipo_granizo() -> None:
    bruta = RespostaColetaInmet(
        status_code=200, corpo=carregar_fixture("cenario_sintetico_granizo.json")
    )

    resultado = NormalizadorInmet().normalizar(bruta, AREA_MONITORADA)

    assert resultado.motivo_rejeicao is None
    assert resultado.evento is not None
    assert resultado.evento.tipo == TipoEventoMeteorologico.GRANIZO


def test_leitura_com_campo_obrigatorio_ausente_e_rejeitada_sem_criar_evento() -> None:
    bruta = RespostaColetaInmet(
        status_code=200, corpo=carregar_fixture("leitura_campo_ausente.json")
    )

    resultado = NormalizadorInmet().normalizar(bruta, AREA_MONITORADA)

    assert resultado.evento is None
    assert resultado.motivo_rejeicao == MotivoRejeicao.CAMPO_AUSENTE


def test_medida_fora_de_faixa_plausivel_e_rejeitada_sem_criar_evento() -> None:
    corpo = carregar_fixture("leitura_chuva_valida.json") | {"CHUVA": "9999"}
    bruta = RespostaColetaInmet(status_code=200, corpo=corpo)

    resultado = NormalizadorInmet().normalizar(bruta, AREA_MONITORADA)

    assert resultado.evento is None
    assert resultado.motivo_rejeicao == MotivoRejeicao.MEDIDA_INVALIDA


def test_medida_nao_numerica_e_rejeitada_como_medida_invalida() -> None:
    corpo = carregar_fixture("leitura_chuva_valida.json") | {"CHUVA": "nao-numerico"}
    bruta = RespostaColetaInmet(status_code=200, corpo=corpo)

    resultado = NormalizadorInmet().normalizar(bruta, AREA_MONITORADA)

    assert resultado.evento is None
    assert resultado.motivo_rejeicao == MotivoRejeicao.MEDIDA_INVALIDA


def test_geografia_nao_reconhecida_e_rejeitada_sem_criar_evento() -> None:
    bruta = RespostaColetaInmet(status_code=200, corpo=carregar_fixture("leitura_chuva_valida.json"))

    resultado = NormalizadorInmet().normalizar(bruta, None)

    assert resultado.evento is None
    assert resultado.motivo_rejeicao == MotivoRejeicao.GEOGRAFIA_NAO_RECONHECIDA


def test_corpo_malformado_nao_lanca_excecao_e_e_rejeitado() -> None:
    bruta = RespostaColetaInmet(status_code=200, corpo="corpo-nao-e-um-dicionario")

    resultado = NormalizadorInmet().normalizar(bruta, AREA_MONITORADA)

    assert resultado.evento is None
    assert resultado.motivo_rejeicao == MotivoRejeicao.CAMPO_AUSENTE
