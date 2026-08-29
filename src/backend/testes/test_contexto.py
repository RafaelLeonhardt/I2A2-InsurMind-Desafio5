"""Testes do caso de uso de consulta do segurado sintético padrão."""

import pytest

from central_preventiva.aplicacao.contexto import (
    PortasContexto,
    SeguradoPadraoAusente,
    consultar_segurado_padrao,
)
from central_preventiva.dominio.identificadores_demonstracao import SEGURADO_PADRAO
from central_preventiva.dominio.segurado import Segurado


class SegurosFalso:
    """Porta de segurados falsa que devolve um dublê fixo ou `None`."""

    def __init__(self, segurado: Segurado | None) -> None:
        self._segurado = segurado

    def buscar_por_id(self, id: object) -> Segurado | None:
        if self._segurado is not None and id == self._segurado.id:
            return self._segurado
        return None


def test_consultar_segurado_padrao_devolve_o_segurado_quando_encontrado() -> None:
    esperado = Segurado(id=SEGURADO_PADRAO, nome="Pessoa Segurada Sintética DEMO-001")
    portas = PortasContexto(segurados=SegurosFalso(esperado))

    resultado = consultar_segurado_padrao(portas)

    assert resultado == esperado


def test_consultar_segurado_padrao_levanta_ausente_quando_nao_encontrado() -> None:
    portas = PortasContexto(segurados=SegurosFalso(None))

    with pytest.raises(SeguradoPadraoAusente):
        consultar_segurado_padrao(portas)
