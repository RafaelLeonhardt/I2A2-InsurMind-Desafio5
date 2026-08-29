"""Testes da sonda de prontidão do processo backend."""

import asyncio

from central_preventiva.adaptadores.prontidao.sonda_backend import SondaBackend
from central_preventiva.dominio.estados_prontidao import EstadoProntidao


def test_sonda_backend_sempre_retorna_disponivel() -> None:
    resultado = asyncio.run(SondaBackend().verificar())

    assert resultado.estado == EstadoProntidao.DISPONIVEL
    assert resultado.causa is None
    assert resultado.latencia_ms is None
