"""Testes do repositório de `visualizacoes_comunicado` (VISU-01, VISU-02, VISU-03)."""

import threading
from pathlib import Path
from uuid import UUID, uuid4

from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_visualizacoes_comunicado import (
    RepositorioVisualizacoesComunicado,
)


def repositorio(tmp_path: Path) -> RepositorioVisualizacoesComunicado:
    """Aplica as migrações versionadas em um banco temporário e devolve o repositório."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return RepositorioVisualizacoesComunicado(caminho)


def test_primeira_chamada_cria_a_linha_e_devolve_a_visualizada_em(tmp_path: Path) -> None:
    """VISU-01: a primeira abertura registra a visualização com data/hora persistida."""

    repo = repositorio(tmp_path)
    entrega_id = uuid4()
    segurado_id = uuid4()

    visualizacao = repo.registrar_primeira_visualizacao(entrega_id, segurado_id)

    assert visualizacao.entrega_simulada_id == entrega_id
    assert visualizacao.segurado_id == segurado_id
    assert visualizacao.visualizada_em is not None


def test_segunda_chamada_devolve_a_mesma_visualizada_em_sem_criar_segunda_linha(
    tmp_path: Path,
) -> None:
    """VISU-02: reabrir um comunicado já visualizado não cria nova data de primeira
    visualização nem uma segunda linha."""

    repo = repositorio(tmp_path)
    entrega_id = uuid4()
    primeiro_segurado_id = uuid4()
    segundo_segurado_id = uuid4()

    primeira = repo.registrar_primeira_visualizacao(entrega_id, primeiro_segurado_id)
    segunda = repo.registrar_primeira_visualizacao(entrega_id, segundo_segurado_id)

    assert segunda.id == primeira.id
    assert segunda.visualizada_em == primeira.visualizada_em
    assert segunda.segurado_id == primeiro_segurado_id


def test_obter_por_entrega_devolve_none_antes_da_primeira_visualizacao(
    tmp_path: Path,
) -> None:
    """`obter_por_entrega` reflete só o que está persistido, sem inventar visualização."""

    repo = repositorio(tmp_path)

    assert repo.obter_por_entrega(uuid4()) is None


def test_obter_por_entrega_le_a_visualizacao_ja_registrada(tmp_path: Path) -> None:
    """`obter_por_entrega` devolve exatamente a linha gravada por
    `registrar_primeira_visualizacao`."""

    repo = repositorio(tmp_path)
    entrega_id = uuid4()
    segurado_id = uuid4()
    registrada = repo.registrar_primeira_visualizacao(entrega_id, segurado_id)

    lida = repo.obter_por_entrega(entrega_id)

    assert lida == registrada


def test_duas_chamadas_concorrentes_convergem_para_a_mesma_visualizacao(
    tmp_path: Path,
) -> None:
    """VISU-03: duas aberturas concorrentes (threads reais, conexões distintas) registram a
    primeira visualização numa única linha; as duas respostas convergem para o mesmo estado
    persistido, nenhuma levanta exceção de conflito de escrita."""

    repo = repositorio(tmp_path)
    entrega_id = uuid4()
    segurado_a = uuid4()
    segurado_b = uuid4()
    resultados: dict[str, object] = {}
    erros: dict[str, BaseException] = {}

    def chamar(nome: str, segurado_id: UUID) -> None:
        try:
            resultados[nome] = repo.registrar_primeira_visualizacao(entrega_id, segurado_id)
        except Exception as erro:  # noqa: BLE001 - captura para asserir ausência abaixo
            erros[nome] = erro

    thread_a = threading.Thread(target=chamar, args=("a", segurado_a))
    thread_b = threading.Thread(target=chamar, args=("b", segurado_b))
    thread_a.start()
    thread_b.start()
    thread_a.join()
    thread_b.join()

    assert erros == {}
    visualizacao_a = resultados["a"]
    visualizacao_b = resultados["b"]
    assert visualizacao_a == visualizacao_b
