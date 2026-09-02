"""Testes do ponto de entrada seguro do servidor local."""

from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    RepositorioExecucaoPreventiva,
)
from central_preventiva.adaptadores.persistencia.semeador import SemeadorDadosSinteticos
from central_preventiva.aplicacao.portas_persistencia import (
    MigracoesPendentes,
    VersaoSchemaFutura,
)
from central_preventiva.composicao import servidor
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.estados_execucao import EstadoExecucao


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


AREA = "9990099"
"""Código IBGE dedicado a este teste, fora dos usados pelo `SemeadorDadosSinteticos`
(9990001/9990002), para que a contagem do público elegível não misture segurados
sintéticos já semeados com os desta história."""


def semear_execucao_pendente_em_avaliando_elegibilidade(caminho: Path) -> str:
    """Persiste uma execução presa em `avaliando_elegibilidade`, como se o processo
    tivesse sido reiniciado logo após a avaliação de risco (RUNNER-07)."""

    execucao_id = RepositorioExecucaoPreventiva(caminho).criar(
        EstadoExecucao.AVALIANDO_ELEGIBILIDADE
    )
    evento_id = str(uuid4())
    regra_id = str(uuid4())
    segurado_id = str(uuid4())
    apolice_id = str(uuid4())
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO eventos_meteorologicos (id, tipo, area, periodo_inicio, "
            "periodo_fim, intensidade, proveniencia, instante_observado) VALUES "
            "(?, 'chuva_intensa', ?, '2026-03-10 06:00:00', '2026-03-10 18:00:00', "
            "72.5, 'sintetico', '2026-03-09 18:00:00')",
            [evento_id, AREA],
        )
        conexao.execute(
            "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
            "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
            "VALUES (?, 'chuva_intensa', 50.0, ?, 'residencial', 'alagamento', 24, "
            "'whatsapp', 1, 'ativa')",
            [regra_id, AREA],
        )
        conexao.execute(
            "INSERT INTO avaliacoes_risco (id, execucao_id, evento_id, regra_id, "
            "regra_versao, relevante, criterios, motivo) VALUES "
            "(?, ?, ?, ?, 1, true, '[]', 'relevante')",
            [str(uuid4()), str(execucao_id), evento_id, regra_id],
        )
        conexao.execute(
            "INSERT INTO segurados (id, nome, codigo_ibge_area, canal_preferido, "
            "participa_de_alertas) VALUES (?, 'Pessoa Retomada de Teste', ?, "
            "'whatsapp', true)",
            [segurado_id, AREA],
        )
        conexao.execute(
            "INSERT INTO apolices (id, segurado_id, numero, tipo, situacao, "
            "vigencia_inicio, vigencia_fim, coberturas, endereco_risco_sintetico, "
            "codigo_ibge_area) VALUES (?, ?, 'NUM-RETOMADA', 'residencial', 'ativa', "
            "'2026-01-01', '2026-12-31', ['alagamento'], 'Rua Teste', ?)",
            [apolice_id, segurado_id, AREA],
        )
    return str(execucao_id)


def test_lifespan_retoma_execucao_nao_terminal_persistida_antes_do_boot(
    tmp_path: Path,
) -> None:
    """RUNNER-07: uma execução travada em `avaliando_elegibilidade` de antes do reinício
    é retomada automaticamente no boot, sem recriar o evento nem recalcular o risco."""

    caminho = preparar_banco_atual(tmp_path)
    execucao_id = semear_execucao_pendente_em_avaliando_elegibilidade(caminho)
    configuracao = configuracao_para(caminho)

    with TestClient(criar_aplicacao(configuracao)) as cliente:
        resposta = cliente.get(f"/api/v1/execucoes/{execucao_id}")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["estado"] == "aguardando_geracao"
    assert corpo["publico_elegivel_total"] == 1
    assert "publico_elegivel_formado" in [m["marco"] for m in corpo["marcos"]]
