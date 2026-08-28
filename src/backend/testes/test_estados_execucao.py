"""Testes do enum canônico de estados da execução preventiva."""

import pytest

from central_preventiva.dominio.estados_execucao import (
    ESTADOS_TERMINAIS,
    EstadoExecucao,
    eh_terminal,
)

NOMES_CANONICOS_AD4 = {
    "coletando",
    "falhou_coleta",
    "sem_risco",
    "avaliando_elegibilidade",
    "sem_elegiveis",
    "aguardando_geracao",
    "falhou_preparacao_ia",
    "processando_mensagens",
    "aguardando_revisao",
    "aguardando_confirmacao",
    "simulando",
    "falhou_simulacao",
    "concluida",
}

NOMES_TERMINAIS_AD4 = {
    "falhou_coleta",
    "sem_risco",
    "sem_elegiveis",
    "falhou_preparacao_ia",
    "falhou_simulacao",
    "concluida",
}


def test_enum_cobre_exatamente_os_estados_canonicos_do_ad4() -> None:
    assert {estado.value for estado in EstadoExecucao} == NOMES_CANONICOS_AD4
    assert {estado.name.lower() for estado in EstadoExecucao} == NOMES_CANONICOS_AD4


def test_estados_terminais_contem_exatamente_os_terminais_do_ad4() -> None:
    assert {estado.value for estado in ESTADOS_TERMINAIS} == NOMES_TERMINAIS_AD4


@pytest.mark.parametrize("estado", list(EstadoExecucao))
def test_eh_terminal_classifica_cada_estado(estado: EstadoExecucao) -> None:
    assert eh_terminal(estado) is (estado.value in NOMES_TERMINAIS_AD4)
