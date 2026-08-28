"""Testes do ponto de entrada seguro do servidor local."""

from pathlib import Path
from typing import Any

import pytest

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.semeador import SemeadorDadosSinteticos
from central_preventiva.aplicacao.portas_persistencia import (
    MigracoesPendentes,
    VersaoSchemaFutura,
)
from central_preventiva.composicao import servidor
from central_preventiva.composicao.configuracao import Configuracao


def configuracao_para(caminho: Path) -> Configuracao:
    """Monta a configuração local apontada ao banco temporário do teste."""

    return Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        caminho_banco=caminho,
    )


def preparar_banco_atual(tmp_path: Path) -> Path:
    """Deixa o banco temporário na versão de schema conhecida pelo código."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    SemeadorDadosSinteticos(caminho).semear()
    return caminho


def registrar_uvicorn(
    monkeypatch: pytest.MonkeyPatch, caminho: Path
) -> dict[str, object]:
    """Substitui `uvicorn.run` e a configuração, devolvendo o registro das chamadas."""

    chamada: dict[str, object] = {}

    def registrar_execucao(aplicacao: object, **argumentos: Any) -> None:
        chamada["aplicacao"] = aplicacao
        chamada.update(argumentos)

    monkeypatch.setattr(servidor, "obter_configuracao", lambda: configuracao_para(caminho))
    monkeypatch.setattr(servidor.uvicorn, "run", registrar_execucao)
    return chamada


def tabelas_do_banco(caminho: Path) -> set[str]:
    """Lê os nomes das tabelas presentes no banco indicado."""

    with abrir_conexao(caminho) as conexao:
        return {
            nome
            for (nome,) in conexao.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()
        }


def estado_do_banco(caminho: Path) -> tuple[set[str], list[tuple[int, str]]]:
    """Lê as tabelas e o registro de migrações, para comprovar ausência de mutação."""

    with abrir_conexao(caminho) as conexao:
        registros = [
            (int(versao), str(descricao))
            for versao, descricao in conexao.execute(
                "SELECT versao, descricao FROM schema_migracoes ORDER BY versao"
            ).fetchall()
        ]
    return tabelas_do_banco(caminho), registros


def test_servidor_repassa_host_validado_e_porta_fixa(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    caminho = preparar_banco_atual(tmp_path)
    chamada = registrar_uvicorn(monkeypatch, caminho)

    servidor.executar()

    assert chamada["aplicacao"] is not None
    assert chamada["host"] == "127.0.0.1"
    assert chamada["port"] == 8000


def test_servidor_recusa_schema_em_versao_futura_sem_mutacao(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    caminho = preparar_banco_atual(tmp_path)
    with abrir_conexao(caminho) as conexao:
        conexao.execute("INSERT INTO schema_migracoes VALUES (99, 'futura', now())")
    estado_anterior = estado_do_banco(caminho)
    chamada = registrar_uvicorn(monkeypatch, caminho)

    with pytest.raises(VersaoSchemaFutura) as captura:
        servidor.executar()

    assert captura.value.versao_registrada == 99
    assert "mais nova que a versão" in str(captura.value)
    assert chamada == {}
    assert estado_do_banco(caminho) == estado_anterior


def test_servidor_recusa_schema_com_migracoes_pendentes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    caminho = tmp_path / "central_preventiva.duckdb"
    chamada = registrar_uvicorn(monkeypatch, caminho)

    with pytest.raises(MigracoesPendentes) as captura:
        servidor.executar()

    assert captura.value.versao_registrada is None
    assert "Execute o comando de inicialização" in str(captura.value)
    assert chamada == {}
    assert tabelas_do_banco(caminho) == set()
