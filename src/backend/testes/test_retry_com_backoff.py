"""Testes do `RetryComBackoff`: política única de tentativas, backoff e registro (AD-8)."""

import asyncio

import pytest

from central_preventiva.aplicacao._retry import (
    BACKOFF_SEGUNDOS,
    MAXIMO_TENTATIVAS,
    RetryComBackoff,
    Tentativa,
    TentativasEsgotadas,
)

MENSAGEM = "Esgotadas as tentativas da operação de teste."


class OperacaoFalsa:
    """Operação dublê: devolve ou lança, em ordem, os resultados programados por chamada."""

    def __init__(self, resultados: list[BaseException | str]) -> None:
        self._resultados = list(resultados)
        self.chamadas = 0

    async def __call__(self) -> str:
        self.chamadas += 1
        resultado = self._resultados.pop(0)
        if isinstance(resultado, BaseException):
            raise resultado
        return resultado


class EsperaEspia:
    """Relógio dublê: registra os intervalos aguardados, sem nenhuma espera real."""

    def __init__(self) -> None:
        self.esperas: list[float] = []

    async def __call__(self, segundos: float) -> None:
        self.esperas.append(segundos)


def montar(
    resultados: list[BaseException | str],
    registradas: list[Tentativa[str]],
    espera: EsperaEspia,
    erros_reconhecidos: tuple[type[BaseException], ...] = (ValueError,),
) -> tuple[RetryComBackoff[str], OperacaoFalsa]:
    """Monta o wrapper sobre uma operação dublê que aceita apenas o valor 'ok'."""

    operacao = OperacaoFalsa(resultados)
    retry = RetryComBackoff(
        operacao=operacao,
        aceitar=lambda valor: valor == "ok",
        registrar=registradas.append,
        mensagem_esgotamento=MENSAGEM,
        erros_reconhecidos=erros_reconhecidos,
        esperar=espera,
    )
    return retry, operacao


def test_politica_unica_declara_tres_tentativas_e_backoff_de_um_e_dois_segundos() -> None:
    assert MAXIMO_TENTATIVAS == 3
    assert BACKOFF_SEGUNDOS == (1.0, 2.0, 4.0)


def test_sucesso_na_primeira_tentativa_nao_aguarda_nem_tenta_de_novo() -> None:
    registradas: list[Tentativa[str]] = []
    espera = EsperaEspia()
    retry, operacao = montar(["ok"], registradas, espera)

    resultado = asyncio.run(retry.executar())

    assert resultado == "ok"
    assert operacao.chamadas == 1
    assert [(t.numero, t.valor, t.erro) for t in registradas] == [(1, "ok", None)]
    assert espera.esperas == []


def test_sucesso_na_segunda_tentativa_aguarda_apenas_um_segundo() -> None:
    registradas: list[Tentativa[str]] = []
    espera = EsperaEspia()
    retry, operacao = montar([ValueError("falha"), "ok"], registradas, espera)

    resultado = asyncio.run(retry.executar())

    assert resultado == "ok"
    assert operacao.chamadas == 2
    assert [(t.numero, t.valor) for t in registradas] == [(1, None), (2, "ok")]
    assert isinstance(registradas[0].erro, ValueError)
    assert espera.esperas == [1.0]


def test_sucesso_na_terceira_tentativa_aguarda_um_e_depois_dois_segundos() -> None:
    registradas: list[Tentativa[str]] = []
    espera = EsperaEspia()
    retry, operacao = montar([ValueError("falha"), "recusado", "ok"], registradas, espera)

    resultado = asyncio.run(retry.executar())

    assert resultado == "ok"
    assert operacao.chamadas == 3
    assert [(t.numero, t.valor) for t in registradas] == [(1, None), (2, "recusado"), (3, "ok")]
    assert espera.esperas == [1.0, 2.0]


def test_esgotamento_registra_tres_tentativas_e_carrega_o_ultimo_valor_recusado() -> None:
    registradas: list[Tentativa[str]] = []
    espera = EsperaEspia()
    retry, operacao = montar(
        [ValueError("falha"), ValueError("falha"), "recusado"], registradas, espera
    )

    with pytest.raises(TentativasEsgotadas) as excecao:
        asyncio.run(retry.executar())

    assert operacao.chamadas == 3
    assert str(excecao.value) == MENSAGEM
    assert excecao.value.tentativas == 3
    assert excecao.value.ultimo_valor == "recusado"
    assert excecao.value.ultimo_erro is None
    assert [t.numero for t in registradas] == [1, 2, 3]
    assert espera.esperas == [1.0, 2.0]


def test_esgotamento_por_erro_reconhecido_carrega_o_ultimo_erro_e_nenhum_valor() -> None:
    erro_final = ValueError("última falha")
    registradas: list[Tentativa[str]] = []
    retry, _ = montar(
        [ValueError("falha"), "recusado", erro_final], registradas, EsperaEspia()
    )

    with pytest.raises(TentativasEsgotadas) as excecao:
        asyncio.run(retry.executar())

    assert excecao.value.ultimo_erro is erro_final
    assert excecao.value.ultimo_valor is None


def test_erro_fora_de_erros_reconhecidos_propaga_sem_consumir_tentativas() -> None:
    registradas: list[Tentativa[str]] = []
    espera = EsperaEspia()
    retry, operacao = montar([TypeError("inesperado"), "ok"], registradas, espera)

    with pytest.raises(TypeError):
        asyncio.run(retry.executar())

    assert operacao.chamadas == 1
    assert registradas == []
    assert espera.esperas == []


def test_cada_tentativa_registrada_carrega_a_janela_de_tempo_da_propria_tentativa() -> None:
    registradas: list[Tentativa[str]] = []
    retry, _ = montar([ValueError("falha"), "ok"], registradas, EsperaEspia())

    asyncio.run(retry.executar())

    assert len(registradas) == 2
    for tentativa in registradas:
        assert tentativa.iniciado_em <= tentativa.finalizado_em
    assert registradas[0].iniciado_em <= registradas[1].iniciado_em
