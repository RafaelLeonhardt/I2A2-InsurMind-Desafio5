"""Testes do `RepositorioAvaliacoesRisco`: snapshot imutável de evento+regra+critérios."""

from pathlib import Path
from uuid import uuid4

from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_risco import (
    RepositorioAvaliacoesRisco,
)
from central_preventiva.dominio.avaliador_risco import Criterio, ResultadoAvaliacaoRisco


def preparar_banco(tmp_path: Path) -> Path:
    """Aplica as migrações versionadas em um arquivo temporário."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


RESULTADO_RELEVANTE = ResultadoAvaliacaoRisco(
    relevante=True,
    criterios=(
        Criterio(
            operando="área aplicável",
            valor_observado="9990001",
            atende=True,
            justificativa="Área do evento corresponde à área aplicável da regra (9990001).",
        ),
        Criterio(
            operando="intensidade (mm acumulados no período)",
            valor_observado="72.5 mm",
            atende=True,
            justificativa="Intensidade observada atinge o limiar de 50.0 mm (fronteira inclusiva).",
        ),
    ),
    motivo="relevante",
)


def test_salvar_persiste_snapshot_completo_e_obter_por_execucao_recupera_sem_recalcular(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    execucao_id, evento_id, regra_id = uuid4(), uuid4(), uuid4()
    repositorio = RepositorioAvaliacoesRisco(caminho)

    id_avaliacao = repositorio.salvar(
        execucao_id, evento_id, regra_id, regra_versao=7, resultado=RESULTADO_RELEVANTE
    )
    avaliacao = repositorio.obter_por_execucao(execucao_id)

    assert avaliacao is not None
    assert avaliacao.id == id_avaliacao
    assert avaliacao.execucao_id == execucao_id
    assert avaliacao.evento_id == evento_id
    assert avaliacao.regra_id == regra_id
    assert avaliacao.regra_versao == 7
    assert avaliacao.relevante is True
    assert avaliacao.motivo == "relevante"
    assert avaliacao.criterios == RESULTADO_RELEVANTE.criterios
    assert avaliacao.criado_em is not None


def test_obter_por_execucao_sem_avaliacao_devolve_none(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    avaliacao = RepositorioAvaliacoesRisco(caminho).obter_por_execucao(uuid4())

    assert avaliacao is None


def test_salvar_com_regra_nula_persiste_e_recupera_sem_regra_ativa(tmp_path: Path) -> None:
    """RISCO-09: terminal `sem_risco` sem regra ativa fica persistido com `regra_id`/
    `regra_versao` nulos (migração 0005), não referências vivas nem valores inventados."""

    caminho = preparar_banco(tmp_path)
    execucao_id, evento_id = uuid4(), uuid4()
    resultado_sem_regra = ResultadoAvaliacaoRisco(
        relevante=False, criterios=(), motivo="sem_regra_ativa"
    )
    repositorio = RepositorioAvaliacoesRisco(caminho)

    repositorio.salvar(execucao_id, evento_id, None, None, resultado_sem_regra)
    avaliacao = repositorio.obter_por_execucao(execucao_id)

    assert avaliacao is not None
    assert avaliacao.regra_id is None
    assert avaliacao.regra_versao is None
    assert avaliacao.relevante is False
    assert avaliacao.motivo == "sem_regra_ativa"
    assert avaliacao.criterios == ()
