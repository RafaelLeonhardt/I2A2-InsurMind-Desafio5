"""Testes do repositório DuckDB de `avaliacoes_criticas` (CRIT-05, CRIT-06, CRIT-08).

O banco é o real, temporário, com as migrações aplicadas: a garantia de uma avaliação por
versão é a `UNIQUE (versao_mensagem_id)` do próprio banco (AD-010), então testá-la só com
dublê provaria pouco.
"""

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_criticas import (
    AGENTE_CRITICO,
    RepositorioAvaliacoesCriticas,
)
from central_preventiva.dominio.avaliacao_critica import (
    AvaliacaoCritica,
    CategoriaCritica,
    MotivoCritica,
)


def repositorio(tmp_path: Path) -> RepositorioAvaliacoesCriticas:
    """Monta o repositório sobre um banco temporário já migrado."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return RepositorioAvaliacoesCriticas(caminho)


def test_avaliacao_aprovada_e_recuperada_sem_motivos(tmp_path: Path) -> None:
    """CRIT-05, CRIT-08: a aprovação persiste decisão, agente, modelo e duração."""

    repo = repositorio(tmp_path)
    versao_id = uuid4()

    id_registro = repo.salvar(
        versao_mensagem_id=versao_id,
        aprovada=True,
        motivos=(),
        modelo="gpt-4o-mini",
        duracao_ms=742.5,
    )

    registro = repo.obter_por_versao(versao_id)
    assert registro is not None
    assert registro.id == id_registro
    assert registro.versao_mensagem_id == versao_id
    assert registro.avaliacao == AvaliacaoCritica(aprovada=True, motivos=())
    assert registro.agente == AGENTE_CRITICO
    assert registro.modelo == "gpt-4o-mini"
    assert registro.duracao_ms == 742.5


def test_avaliacao_reprovada_preserva_categoria_e_justificativa_de_cada_motivo(
    tmp_path: Path,
) -> None:
    """CRIT-06: os motivos ficam estruturados e associados à versão avaliada."""

    repo = repositorio(tmp_path)
    versao_id = uuid4()
    motivos = (
        MotivoCritica(CategoriaCritica.TOM, "O texto usa tom alarmista, não preventivo."),
        MotivoCritica(CategoriaCritica.PROMESSA_INDEVIDA, "Promete indenização integral."),
    )

    repo.salvar(
        versao_mensagem_id=versao_id,
        aprovada=False,
        motivos=motivos,
        modelo="gpt-4o-mini",
        duracao_ms=91.25,
    )

    registro = repo.obter_por_versao(versao_id)
    assert registro is not None
    assert registro.avaliacao == AvaliacaoCritica(aprovada=False, motivos=motivos)
    assert registro.avaliacao.motivos[0].categoria is CategoriaCritica.TOM
    assert (
        registro.avaliacao.motivos[0].justificativa
        == "O texto usa tom alarmista, não preventivo."
    )


@pytest.mark.parametrize("categoria", list(CategoriaCritica))
def test_cada_uma_das_sete_categorias_percorre_a_ida_e_a_volta_do_banco(
    categoria: CategoriaCritica, tmp_path: Path
) -> None:
    """CRIT-03, CRIT-06: as sete categorias do AC persistem e voltam sem perda."""

    repo = repositorio(tmp_path)
    versao_id = uuid4()
    motivo = MotivoCritica(categoria, f"Justificativa de {categoria.value}.")

    repo.salvar(
        versao_mensagem_id=versao_id,
        aprovada=False,
        motivos=(motivo,),
        modelo="gpt-4o-mini",
        duracao_ms=10.0,
    )

    registro = repo.obter_por_versao(versao_id)
    assert registro is not None
    assert registro.avaliacao.motivos == (motivo,)


def test_versao_ainda_nao_avaliada_devolve_nulo(tmp_path: Path) -> None:
    """CRIT-08: uma versão sem avaliação não devolve avaliação inventada."""

    assert repositorio(tmp_path).obter_por_versao(uuid4()) is None


def test_reavaliar_a_mesma_versao_reaproveita_a_avaliacao_persistida(tmp_path: Path) -> None:
    """Terceiro Edge Case da 3.3: um replay reaproveita o resultado já persistido, sem
    gravar uma segunda avaliação nem sobrescrever a primeira."""

    repo = repositorio(tmp_path)
    versao_id = uuid4()
    motivos = (MotivoCritica(CategoriaCritica.CLAREZA, "A instrução é ambígua."),)
    primeiro_id = repo.salvar(
        versao_mensagem_id=versao_id,
        aprovada=False,
        motivos=motivos,
        modelo="gpt-4o-mini",
        duracao_ms=55.0,
    )

    segundo_id = repo.salvar(
        versao_mensagem_id=versao_id,
        aprovada=True,
        motivos=(),
        modelo="outro-modelo",
        duracao_ms=1.0,
    )

    assert segundo_id == primeiro_id
    registro = repo.obter_por_versao(versao_id)
    assert registro is not None
    assert registro.avaliacao == AvaliacaoCritica(aprovada=False, motivos=motivos)
    assert registro.modelo == "gpt-4o-mini"
    assert registro.duracao_ms == 55.0


def test_avaliacoes_de_versoes_distintas_nao_se_misturam(tmp_path: Path) -> None:
    """A avaliação é escopada pela versão consultada, nunca por toda a tabela."""

    repo = repositorio(tmp_path)
    aprovada_id, reprovada_id = uuid4(), uuid4()
    repo.salvar(aprovada_id, True, (), "gpt-4o-mini", 12.0)
    repo.salvar(
        reprovada_id,
        False,
        (MotivoCritica(CategoriaCritica.SEGURANCA, "Orientação insegura."),),
        "gpt-4o-mini",
        13.0,
    )

    aprovada = repo.obter_por_versao(aprovada_id)
    reprovada = repo.obter_por_versao(reprovada_id)

    assert aprovada is not None
    assert reprovada is not None
    assert aprovada.avaliacao.aprovada is True
    assert aprovada.avaliacao.motivos == ()
    assert reprovada.avaliacao.aprovada is False
    assert reprovada.avaliacao.motivos == (
        MotivoCritica(CategoriaCritica.SEGURANCA, "Orientação insegura."),
    )


def test_identificador_devolvido_e_o_da_linha_persistida(tmp_path: Path) -> None:
    """`salvar` devolve o identificador que ficou valendo, usado para correlacionar."""

    repo = repositorio(tmp_path)
    versao_id = uuid4()

    id_registro = repo.salvar(versao_id, True, (), "gpt-4o-mini", 5.0)

    registro = repo.obter_por_versao(versao_id)
    assert registro is not None
    assert isinstance(id_registro, UUID)
    assert registro.id == id_registro
