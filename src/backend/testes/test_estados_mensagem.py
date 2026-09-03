"""Testes do enum canônico de estados de uma mensagem preventiva."""

import pytest

from central_preventiva.dominio.estados_mensagem import (
    ESTADOS_TERMINAIS_MENSAGEM,
    EstadoMensagem,
    eh_terminal_mensagem,
)

NOMES_CANONICOS_AD4 = {
    "gerando",
    "criticando",
    "aguardando_revisao",
    "aprovada",
    "rejeitada",
    "excluida",
    "simulada_entregue",
    "falhou_conteudo",
    "falhou_integracao_ia",
}

NOMES_TERMINAIS_AD4 = {
    "rejeitada",
    "excluida",
    "simulada_entregue",
    "falhou_conteudo",
    "falhou_integracao_ia",
}


def test_enum_cobre_exatamente_os_nove_estados_de_mensagem_do_ad4() -> None:
    assert {estado.value for estado in EstadoMensagem} == NOMES_CANONICOS_AD4
    assert {estado.name.lower() for estado in EstadoMensagem} == NOMES_CANONICOS_AD4


def test_estados_terminais_contem_exatamente_os_terminais_de_mensagem_do_ad4() -> None:
    assert {estado.value for estado in ESTADOS_TERMINAIS_MENSAGEM} == NOMES_TERMINAIS_AD4


@pytest.mark.parametrize("estado", list(EstadoMensagem))
def test_eh_terminal_mensagem_classifica_cada_estado(estado: EstadoMensagem) -> None:
    assert eh_terminal_mensagem(estado) is (estado.value in NOMES_TERMINAIS_AD4)
