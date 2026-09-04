"""Testes do repositório DuckDB de `decisoes_humanas` (REVISAO-06, REVISAO-07, REVISAO-11).

O banco é o real, temporário, com as migrações aplicadas: a obrigatoriedade da justificativa e
o conjunto fechado de resultados são `CHECK` do próprio banco (migração `0013`), então testá-los
só com dublê provaria pouco.
"""

from pathlib import Path
from uuid import UUID, uuid4

import duckdb
import pytest

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_criticas import (
    RepositorioAvaliacoesCriticas,
)
from central_preventiva.adaptadores.persistencia.repositorio_decisoes_humanas import (
    RepositorioDecisoesHumanas,
)
from central_preventiva.dominio.decisao_humana import ResultadoDecisaoHumana

PERFIL = "Administrador"


def caminho_migrado(tmp_path: Path) -> Path:
    """Devolve o caminho de um banco temporário já migrado."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def repositorio(tmp_path: Path) -> RepositorioDecisoesHumanas:
    """Monta o repositório sobre um banco temporário já migrado."""

    return RepositorioDecisoesHumanas(caminho_migrado(tmp_path))


def test_decisao_persiste_perfil_resultado_justificativa_e_versao_decidida(
    tmp_path: Path,
) -> None:
    """REVISAO-07: a decisão registra perfil sintético responsável, data, resultado,
    justificativa e a versão da mensagem sobre a qual ela foi tomada."""

    repo = repositorio(tmp_path)
    mensagem_id, versao_id = uuid4(), uuid4()

    id_decisao = repo.salvar(
        mensagem_id=mensagem_id,
        versao_mensagem_id=versao_id,
        perfil=PERFIL,
        resultado=ResultadoDecisaoHumana.REJEITAR,
        justificativa="O texto não distingue o aviso da seguradora de um alerta oficial.",
    )

    decisoes = repo.obter_por_mensagem(mensagem_id)
    assert len(decisoes) == 1
    decisao = decisoes[0]
    assert decisao.id == id_decisao
    assert isinstance(id_decisao, UUID)
    assert decisao.mensagem_id == mensagem_id
    assert decisao.versao_mensagem_id == versao_id
    assert decisao.perfil_responsavel == PERFIL
    assert decisao.resultado is ResultadoDecisaoHumana.REJEITAR
    assert (
        decisao.justificativa
        == "O texto não distingue o aviso da seguradora de um alerta oficial."
    )
    assert decisao.criado_em is not None


@pytest.mark.parametrize("resultado", list(ResultadoDecisaoHumana))
def test_cada_um_dos_quatro_resultados_percorre_a_ida_e_a_volta_do_banco(
    resultado: ResultadoDecisaoHumana, tmp_path: Path
) -> None:
    """REVISAO-05: aprovar, rejeitar, excluir e regenerar são os quatro resultados possíveis,
    e todos persistem e voltam sem perda."""

    repo = repositorio(tmp_path)
    mensagem_id = uuid4()

    repo.salvar(
        mensagem_id=mensagem_id,
        versao_mensagem_id=uuid4(),
        perfil=PERFIL,
        resultado=resultado,
        justificativa="Justificativa suficiente para a decisão.",
    )

    assert [item.resultado for item in repo.obter_por_mensagem(mensagem_id)] == [resultado]


def test_aprovacao_pode_ser_persistida_sem_justificativa(tmp_path: Path) -> None:
    """REVISAO-06: a justificativa é obrigatória em rejeitar, excluir e regenerar — aprovar
    é a única decisão que dispensa motivo."""

    repo = repositorio(tmp_path)
    mensagem_id = uuid4()

    repo.salvar(
        mensagem_id=mensagem_id,
        versao_mensagem_id=uuid4(),
        perfil=PERFIL,
        resultado=ResultadoDecisaoHumana.APROVAR,
        justificativa=None,
    )

    decisoes = repo.obter_por_mensagem(mensagem_id)
    assert [(item.resultado, item.justificativa) for item in decisoes] == [
        (ResultadoDecisaoHumana.APROVAR, None)
    ]


@pytest.mark.parametrize(
    "resultado",
    [
        ResultadoDecisaoHumana.REJEITAR,
        ResultadoDecisaoHumana.EXCLUIR,
        ResultadoDecisaoHumana.REGENERAR,
    ],
)
def test_decisao_sem_justificativa_e_recusada_pelo_banco(
    resultado: ResultadoDecisaoHumana, tmp_path: Path
) -> None:
    """REVISAO-06: nenhum caminho de escrita consegue gravar rejeição, exclusão ou
    regeneração sem motivo — a regra é cobrada pelo próprio schema, e nada é persistido."""

    repo = repositorio(tmp_path)
    mensagem_id = uuid4()

    with pytest.raises(duckdb.ConstraintException):
        repo.salvar(
            mensagem_id=mensagem_id,
            versao_mensagem_id=uuid4(),
            perfil=PERFIL,
            resultado=resultado,
            justificativa=None,
        )

    assert repo.obter_por_mensagem(mensagem_id) == []


def test_mensagem_sem_decisao_devolve_lista_vazia(tmp_path: Path) -> None:
    """Uma mensagem ainda aguardando revisão não devolve decisão inventada."""

    assert repositorio(tmp_path).obter_por_mensagem(uuid4()) == []


def test_decisoes_de_mensagens_distintas_nao_se_misturam(tmp_path: Path) -> None:
    """A consulta é escopada pela mensagem, nunca por toda a tabela."""

    repo = repositorio(tmp_path)
    primeira, segunda = uuid4(), uuid4()
    repo.salvar(primeira, uuid4(), PERFIL, ResultadoDecisaoHumana.APROVAR, None)
    repo.salvar(
        segunda, uuid4(), PERFIL, ResultadoDecisaoHumana.EXCLUIR, "Fora do escopo do lote."
    )

    assert [item.resultado for item in repo.obter_por_mensagem(primeira)] == [
        ResultadoDecisaoHumana.APROVAR
    ]
    assert [item.resultado for item in repo.obter_por_mensagem(segunda)] == [
        ResultadoDecisaoHumana.EXCLUIR
    ]


def test_historico_da_mensagem_preserva_regeneracao_e_decisao_seguinte(
    tmp_path: Path,
) -> None:
    """REVISAO-11: a solicitação humana de regeneração e a decisão sobre a versão nova
    coexistem no histórico da mesma mensagem, em ordem, nenhuma sobrescrevendo a outra."""

    repo = repositorio(tmp_path)
    mensagem_id = uuid4()
    versao_antiga, versao_nova = uuid4(), uuid4()

    repo.salvar(
        mensagem_id,
        versao_antiga,
        PERFIL,
        ResultadoDecisaoHumana.REGENERAR,
        "O texto está longo demais para SMS.",
    )
    repo.salvar(mensagem_id, versao_nova, PERFIL, ResultadoDecisaoHumana.APROVAR, None)

    decisoes = repo.obter_por_mensagem(mensagem_id)
    assert [
        (item.resultado, item.versao_mensagem_id, item.justificativa) for item in decisoes
    ] == [
        (
            ResultadoDecisaoHumana.REGENERAR,
            versao_antiga,
            "O texto está longo demais para SMS.",
        ),
        (ResultadoDecisaoHumana.APROVAR, versao_nova, None),
    ]


def test_decisao_humana_e_avaliacao_critica_da_mesma_versao_permanecem_distintas(
    tmp_path: Path,
) -> None:
    """REVISAO-07: a decisão de Marina nunca se confunde com a aprovação do agente crítico —
    são duas linhas, em duas tabelas, com responsáveis diferentes sobre a mesma versão."""

    caminho = caminho_migrado(tmp_path)
    decisoes_repo = RepositorioDecisoesHumanas(caminho)
    criticas_repo = RepositorioAvaliacoesCriticas(caminho)
    mensagem_id, versao_id = uuid4(), uuid4()

    criticas_repo.salvar(
        versao_mensagem_id=versao_id,
        aprovada=True,
        motivos=(),
        modelo="gpt-4o-mini",
        duracao_ms=120.0,
    )
    decisoes_repo.salvar(
        mensagem_id=mensagem_id,
        versao_mensagem_id=versao_id,
        perfil=PERFIL,
        resultado=ResultadoDecisaoHumana.REJEITAR,
        justificativa="Aprovada pelo crítico, mas inadequada para este público.",
    )

    critica = criticas_repo.obter_por_versao(versao_id)
    decisoes = decisoes_repo.obter_por_mensagem(mensagem_id)
    assert critica is not None
    assert critica.avaliacao.aprovada is True
    assert critica.agente == "critico"
    assert [(item.resultado, item.perfil_responsavel) for item in decisoes] == [
        (ResultadoDecisaoHumana.REJEITAR, PERFIL)
    ]


def test_decisao_gravada_na_transacao_do_chamador_desaparece_no_rollback(
    tmp_path: Path,
) -> None:
    """REVISAO-12: `salvar` participa da transação já aberta pelo chamador — é o que permite
    à decisão em lote aplicar tudo ou nada."""

    caminho = caminho_migrado(tmp_path)
    repo = RepositorioDecisoesHumanas(caminho)
    mensagem_id = uuid4()

    with abrir_conexao(caminho) as conexao:
        conexao.execute("BEGIN TRANSACTION")
        repo.salvar(
            mensagem_id,
            uuid4(),
            PERFIL,
            ResultadoDecisaoHumana.APROVAR,
            None,
            conexao=conexao,
        )
        assert conexao.execute(
            "SELECT count(*) FROM decisoes_humanas WHERE mensagem_id = ?", [mensagem_id]
        ).fetchone() == (1,)
        conexao.execute("ROLLBACK")

    assert repo.obter_por_mensagem(mensagem_id) == []
