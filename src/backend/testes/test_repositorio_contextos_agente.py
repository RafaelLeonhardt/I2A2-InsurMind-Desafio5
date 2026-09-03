"""Testes do repositório de contextos mínimos e sua proveniência (PREFL-13, PREFL-14)."""

import logging
from pathlib import Path
from uuid import UUID, uuid4

import duckdb
import pytest

from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_contextos_agente import (
    RepositorioContextosAgente,
)
from central_preventiva.dominio.montador_contexto_agente import (
    CATEGORIAS_NAO_UTILIZADAS,
    CATEGORIAS_UTILIZADAS,
    ContextoAgente,
)

EXECUCAO_ID = UUID("11111111-1111-1111-1111-111111111111")
ELEGIBILIDADE_ID = UUID("22222222-2222-2222-2222-222222222222")

CONTEXTO = ContextoAgente(
    evento="chuva_intensa",
    localizacao_aproximada="9990001",
    coberturas_relevantes=("alagamento", "vendaval"),
    canal="whatsapp",
    orientacoes_seguranca=(
        "Evite áreas alagadas e não atravesse ruas com água corrente.",
        "Mantenha documentos e itens essenciais em local elevado.",
    ),
)


def preparar_banco(tmp_path: Path) -> Path:
    """Aplica as migrações versionadas em um banco temporário do teste."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def test_salvar_persiste_o_contexto_e_as_duas_listas_de_categorias(tmp_path: Path) -> None:
    repositorio = RepositorioContextosAgente(preparar_banco(tmp_path))

    id_registro = repositorio.salvar(
        EXECUCAO_ID, ELEGIBILIDADE_ID, CONTEXTO, CATEGORIAS_UTILIZADAS, CATEGORIAS_NAO_UTILIZADAS
    )

    registro = repositorio.obter_por_elegibilidade(ELEGIBILIDADE_ID)
    assert registro is not None
    assert registro.id == id_registro
    assert registro.execucao_id == EXECUCAO_ID
    assert registro.elegibilidade_id == ELEGIBILIDADE_ID
    assert registro.contexto == CONTEXTO
    assert registro.categorias_usadas == CATEGORIAS_UTILIZADAS
    assert registro.categorias_nao_usadas == CATEGORIAS_NAO_UTILIZADAS


def test_obter_de_elegibilidade_sem_contexto_devolve_nulo(tmp_path: Path) -> None:
    repositorio = RepositorioContextosAgente(preparar_banco(tmp_path))

    assert repositorio.obter_por_elegibilidade(uuid4()) is None


def test_listar_por_execucao_devolve_a_proveniencia_de_cada_item_preparado(
    tmp_path: Path,
) -> None:
    """PREFL-14: a consulta de proveniência lê as categorias já gravadas, sem recalcular."""

    repositorio = RepositorioContextosAgente(preparar_banco(tmp_path))
    primeira, segunda = uuid4(), uuid4()
    repositorio.salvar(
        EXECUCAO_ID, primeira, CONTEXTO, CATEGORIAS_UTILIZADAS, CATEGORIAS_NAO_UTILIZADAS
    )
    repositorio.salvar(
        EXECUCAO_ID, segunda, CONTEXTO, CATEGORIAS_UTILIZADAS, CATEGORIAS_NAO_UTILIZADAS
    )
    repositorio.salvar(
        uuid4(), uuid4(), CONTEXTO, CATEGORIAS_UTILIZADAS, CATEGORIAS_NAO_UTILIZADAS
    )

    registros = repositorio.listar_por_execucao(EXECUCAO_ID)

    assert {registro.elegibilidade_id for registro in registros} == {primeira, segunda}
    assert all(registro.categorias_usadas == CATEGORIAS_UTILIZADAS for registro in registros)
    assert all(
        registro.categorias_nao_usadas == CATEGORIAS_NAO_UTILIZADAS for registro in registros
    )


def test_segundo_contexto_para_a_mesma_elegibilidade_e_recusado_pelo_banco(
    tmp_path: Path,
) -> None:
    """`UNIQUE (elegibilidade_id)` (migração `0009`) impede sobrescrever um contexto já usado."""

    repositorio = RepositorioContextosAgente(preparar_banco(tmp_path))
    repositorio.salvar(
        EXECUCAO_ID, ELEGIBILIDADE_ID, CONTEXTO, CATEGORIAS_UTILIZADAS, CATEGORIAS_NAO_UTILIZADAS
    )

    with pytest.raises(duckdb.ConstraintException):
        repositorio.salvar(
            uuid4(),
            ELEGIBILIDADE_ID,
            CONTEXTO,
            CATEGORIAS_UTILIZADAS,
            CATEGORIAS_NAO_UTILIZADAS,
        )


def test_persistencia_nao_registra_o_conteudo_do_contexto_em_log(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """PREFL-13: registrar a proveniência não copia conteúdo sensível para log."""

    repositorio = RepositorioContextosAgente(preparar_banco(tmp_path))

    with caplog.at_level(logging.DEBUG):
        repositorio.salvar(
            EXECUCAO_ID,
            ELEGIBILIDADE_ID,
            CONTEXTO,
            CATEGORIAS_UTILIZADAS,
            CATEGORIAS_NAO_UTILIZADAS,
        )
        repositorio.obter_por_elegibilidade(ELEGIBILIDADE_ID)

    registrado = caplog.text
    assert CONTEXTO.localizacao_aproximada not in registrado
    assert CONTEXTO.canal not in registrado
    for cobertura in CONTEXTO.coberturas_relevantes:
        assert cobertura not in registrado
