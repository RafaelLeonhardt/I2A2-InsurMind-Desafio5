"""Testes do `ColetorComRetry`: retry limitado, backoff exato e registro por tentativa."""

import asyncio
from uuid import UUID

import httpx
import pytest

from central_preventiva.aplicacao.coleta_meteorologica import (
    ColetorComRetry,
    RetentativasEsgotadas,
)
from central_preventiva.aplicacao.portas_meteorologia import (
    AreaMonitorada,
    CodigoResultadoTentativa,
    RespostaColetaInmet,
    TentativaColeta,
)

AREA = AreaMonitorada(
    id=UUID("33333333-3333-3333-3333-333333333333"),
    codigo_estacao_inmet="A701",
    nome_estacao="Estação de Teste",
    codigo_ibge_area="9990001",
    ativa=True,
)
RESPOSTA_VALIDA = RespostaColetaInmet(status_code=200, corpo={"ok": True})
RESPOSTA_ERRO = RespostaColetaInmet(status_code=500, corpo={"erro": True})


class ColetorFalso:
    """Coletor dublê: devolve/lança, em ordem, os resultados programados por chamada."""

    def __init__(self, resultados: list[BaseException | RespostaColetaInmet]) -> None:
        self._resultados = list(resultados)
        self.chamadas = 0

    async def coletar(self, area: AreaMonitorada) -> RespostaColetaInmet:
        self.chamadas += 1
        resultado = self._resultados.pop(0)
        if isinstance(resultado, BaseException):
            raise resultado
        return resultado


class TentativasEspias:
    """Repositório de tentativas dublê: registra cada chamada para inspeção do teste."""

    def __init__(self) -> None:
        self.registradas: list[tuple[UUID, int, CodigoResultadoTentativa]] = []

    def registrar_tentativa(
        self,
        sincronizacao_id: UUID,
        numero_tentativa: int,
        codigo_resultado: CodigoResultadoTentativa,
        iniciado_em: object,
        finalizado_em: object,
    ) -> None:
        assert iniciado_em is not None
        assert finalizado_em is not None
        self.registradas.append((sincronizacao_id, numero_tentativa, codigo_resultado))

    def listar_tentativas(self, sincronizacao_id: UUID) -> tuple[TentativaColeta, ...]:
        return ()


class EsperaEspia:
    """Relógio dublê: registra os intervalos aguardados, sem nenhuma espera real."""

    def __init__(self) -> None:
        self.esperas: list[float] = []

    async def __call__(self, segundos: float) -> None:
        self.esperas.append(segundos)


SINCRONIZACAO_ID = UUID("44444444-4444-4444-4444-444444444444")


def test_sucesso_na_primeira_tentativa_nao_aguarda_nem_tenta_de_novo() -> None:
    coletor = ColetorFalso([RESPOSTA_VALIDA])
    tentativas = TentativasEspias()
    espera = EsperaEspia()
    retry = ColetorComRetry(coletor, tentativas, SINCRONIZACAO_ID, esperar=espera)

    resultado = asyncio.run(retry.coletar(AREA))

    assert resultado == RESPOSTA_VALIDA
    assert coletor.chamadas == 1
    assert tentativas.registradas == [
        (SINCRONIZACAO_ID, 1, CodigoResultadoTentativa.SUCESSO)
    ]
    assert espera.esperas == []


def test_falha_falha_sucesso_registra_tres_tentativas_com_backoff_1s_depois_2s() -> None:
    coletor = ColetorFalso([httpx.TimeoutException("t"), httpx.ConnectError("c"), RESPOSTA_VALIDA])
    tentativas = TentativasEspias()
    espera = EsperaEspia()
    retry = ColetorComRetry(coletor, tentativas, SINCRONIZACAO_ID, esperar=espera)

    resultado = asyncio.run(retry.coletar(AREA))

    assert resultado == RESPOSTA_VALIDA
    assert coletor.chamadas == 3
    assert tentativas.registradas == [
        (SINCRONIZACAO_ID, 1, CodigoResultadoTentativa.TIMEOUT),
        (SINCRONIZACAO_ID, 2, CodigoResultadoTentativa.ERRO_TRANSPORTE),
        (SINCRONIZACAO_ID, 3, CodigoResultadoTentativa.SUCESSO),
    ]
    assert espera.esperas == [1.0, 2.0]


def test_tres_falhas_consecutivas_propaga_retentativas_esgotadas() -> None:
    coletor = ColetorFalso(
        [httpx.TimeoutException("t"), httpx.TimeoutException("t"), RESPOSTA_ERRO]
    )
    tentativas = TentativasEspias()
    espera = EsperaEspia()
    retry = ColetorComRetry(coletor, tentativas, SINCRONIZACAO_ID, esperar=espera)

    with pytest.raises(RetentativasEsgotadas) as excecao:
        asyncio.run(retry.coletar(AREA))

    assert coletor.chamadas == 3
    assert excecao.value.tentativas == 3
    assert excecao.value.ultima_resposta == RESPOSTA_ERRO
    assert excecao.value.ultimo_erro is None
    assert tentativas.registradas == [
        (SINCRONIZACAO_ID, 1, CodigoResultadoTentativa.TIMEOUT),
        (SINCRONIZACAO_ID, 2, CodigoResultadoTentativa.TIMEOUT),
        (SINCRONIZACAO_ID, 3, CodigoResultadoTentativa.STATUS_ERRO),
    ]
    assert espera.esperas == [1.0, 2.0]


def test_esgotamento_por_erro_de_transporte_carrega_o_ultimo_erro() -> None:
    erro_final = httpx.ConnectError("c")
    coletor = ColetorFalso([httpx.TimeoutException("t"), httpx.TimeoutException("t"), erro_final])
    retry = ColetorComRetry(coletor, TentativasEspias(), SINCRONIZACAO_ID, esperar=EsperaEspia())

    with pytest.raises(RetentativasEsgotadas) as excecao:
        asyncio.run(retry.coletar(AREA))

    assert excecao.value.ultimo_erro is erro_final
    assert excecao.value.ultima_resposta is None
