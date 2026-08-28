"""Testes do ponto de entrada seguro do servidor local."""

from typing import Any

import pytest

from central_preventiva.composicao import servidor
from central_preventiva.composicao.configuracao import Configuracao


def test_servidor_repassa_host_validado_e_porta_fixa(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configuracao = Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
    )
    chamada: dict[str, object] = {}

    def registrar_execucao(aplicacao: object, **argumentos: Any) -> None:
        chamada["aplicacao"] = aplicacao
        chamada.update(argumentos)

    monkeypatch.setattr(servidor, "obter_configuracao", lambda: configuracao)
    monkeypatch.setattr(servidor.uvicorn, "run", registrar_execucao)

    servidor.executar()

    assert chamada["aplicacao"] is not None
    assert chamada["host"] == "127.0.0.1"
    assert chamada["port"] == 8000
