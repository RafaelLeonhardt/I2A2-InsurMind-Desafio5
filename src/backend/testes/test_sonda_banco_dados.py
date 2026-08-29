"""Testes da sonda de prontidão do banco de dados operacional."""

import asyncio
from pathlib import Path

from central_preventiva.adaptadores.prontidao.sonda_banco_dados import SondaBancoDados
from central_preventiva.dominio.estados_prontidao import EstadoProntidao


def test_banco_valido_resulta_em_disponivel(tmp_path: Path) -> None:
    caminho = tmp_path / "central_preventiva.duckdb"

    resultado = asyncio.run(SondaBancoDados(caminho).verificar())

    assert resultado.estado == EstadoProntidao.DISPONIVEL
    assert resultado.causa is None


def test_banco_inacessivel_resulta_em_indisponivel_sem_expor_o_caminho(tmp_path: Path) -> None:
    caminho_invalido = tmp_path / "banco_que_e_um_diretorio"
    caminho_invalido.mkdir()

    resultado = asyncio.run(SondaBancoDados(caminho_invalido).verificar())

    assert resultado.estado == EstadoProntidao.INDISPONIVEL
    assert resultado.causa is not None
    assert str(caminho_invalido) not in resultado.causa
    assert str(tmp_path) not in resultado.causa
