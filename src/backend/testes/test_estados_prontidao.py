"""Testes do enum canônico de estados de prontidão de uma dependência."""

import pytest

from central_preventiva.dominio.estados_prontidao import (
    ESTADOS_TERMINAIS,
    EstadoProntidao,
    eh_terminal,
)

NOMES_CANONICOS = {
    "verificando",
    "disponivel",
    "degradada",
    "indisponivel",
}

NOMES_TERMINAIS = {
    "disponivel",
    "degradada",
    "indisponivel",
}


def test_enum_cobre_exatamente_os_quatro_estados_do_spec() -> None:
    assert {estado.value for estado in EstadoProntidao} == NOMES_CANONICOS
    assert {estado.name.lower() for estado in EstadoProntidao} == NOMES_CANONICOS


def test_estados_terminais_contem_exatamente_os_tres_estados_terminais() -> None:
    assert {estado.value for estado in ESTADOS_TERMINAIS} == NOMES_TERMINAIS


def test_verificando_nao_e_terminal() -> None:
    assert eh_terminal(EstadoProntidao.VERIFICANDO) is False


@pytest.mark.parametrize(
    "estado",
    [EstadoProntidao.DISPONIVEL, EstadoProntidao.DEGRADADA, EstadoProntidao.INDISPONIVEL],
)
def test_estados_terminais_sao_classificados_como_terminais(estado: EstadoProntidao) -> None:
    assert eh_terminal(estado) is True
