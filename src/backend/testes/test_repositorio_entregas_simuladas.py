"""Testes do repositório de entregas simuladas (SIMUL-05, SIMUL-06, SIMUL-07).

O banco é o real, temporário e migrado: a `UNIQUE (mensagem_id)` e a atomicidade dentro da
transação do chamador são garantias do próprio DuckDB — testá-las com dublê provaria pouco.
"""

from dataclasses import fields
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    ROTULO_SIMULADA,
    EntregaSimuladaJaExiste,
    MensagemAprovada,
    RepositorioEntregasSimuladas,
)
from central_preventiva.adaptadores.persistencia.transacao import TransacaoDuckDB
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

EXECUCAO_ID = UUID("11111111-1111-1111-1111-111111111111")
OUTRA_EXECUCAO_ID = UUID("99999999-9999-9999-9999-999999999999")
CORPO_SMS = "Chuva forte hoje na sua região. Evite áreas alagadas."
CORPO_EMAIL = "Prezada, previsão de chuva intensa na sua região nas próximas horas."
ASSUNTO_EMAIL = "Aviso preventivo da sua seguradora"


def preparar(tmp_path: Path) -> Path:
    """Aplica as migrações versionadas em um banco temporário do teste."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def contar(caminho: Path) -> int:
    """Conta todas as entregas simuladas persistidas no banco do teste."""

    with abrir_conexao(caminho) as conexao:
        linha = conexao.execute("SELECT count(*) FROM entregas_simuladas").fetchone()
    assert linha is not None
    return int(linha[0])


def test_criar_lote_cria_uma_entrega_por_mensagem_com_o_conteudo_aprovado(
    tmp_path: Path,
) -> None:
    """SIMUL-05: uma entrega por mensagem e canal, com a apresentação copiada do conteúdo já
    aprovado — corpo no SMS, assunto e corpo no e-mail, sem transformação."""

    caminho = preparar(tmp_path)
    repositorio = RepositorioEntregasSimuladas(caminho)
    mensagem_sms = uuid4()
    mensagem_email = uuid4()

    criadas = repositorio.criar_lote(
        EXECUCAO_ID,
        [
            MensagemAprovada(mensagem_sms, Canal.SMS, SaidaCanal(corpo=CORPO_SMS)),
            MensagemAprovada(
                mensagem_email,
                Canal.EMAIL,
                SaidaCanal(corpo=CORPO_EMAIL, assunto=ASSUNTO_EMAIL),
            ),
        ],
    )

    entregas = repositorio.listar_por_execucao(EXECUCAO_ID)
    assert len(criadas) == 2
    assert [entrega.id for entrega in entregas] == criadas
    assert [entrega.mensagem_id for entrega in entregas] == [mensagem_sms, mensagem_email]
    assert [entrega.canal for entrega in entregas] == [Canal.SMS, Canal.EMAIL]
    assert [entrega.execucao_id for entrega in entregas] == [EXECUCAO_ID, EXECUCAO_ID]
    assert entregas[0].apresentacao.corpo == CORPO_SMS
    assert entregas[0].apresentacao.assunto is None
    assert entregas[1].apresentacao.corpo == CORPO_EMAIL
    assert entregas[1].apresentacao.assunto == ASSUNTO_EMAIL


def test_toda_entrega_e_rotulada_como_simulada(tmp_path: Path) -> None:
    """SIMUL-06: a entrega é rotulada como simulada e não carrega confirmação nem falha de
    provedor externo — não existe campo onde inventá-las."""

    caminho = preparar(tmp_path)
    repositorio = RepositorioEntregasSimuladas(caminho)
    repositorio.criar_lote(
        EXECUCAO_ID,
        [MensagemAprovada(uuid4(), Canal.WHATSAPP, SaidaCanal(corpo=CORPO_SMS))],
    )

    entrega = repositorio.listar_por_execucao(EXECUCAO_ID)[0]

    assert entrega.apresentacao.rotulo == ROTULO_SIMULADA == "simulada"
    assert {campo.name for campo in fields(entrega.apresentacao)} == {
        "canal",
        "corpo",
        "assunto",
        "rotulo",
    }


def test_criar_lote_participa_da_transacao_do_chamador(tmp_path: Path) -> None:
    """SIMUL-05: as entregas entram na transação já aberta pelo chamador — uma falha depois
    da inserção desfaz o lote inteiro, sem entrega parcial."""

    caminho = preparar(tmp_path)
    repositorio = RepositorioEntregasSimuladas(caminho)
    transacao = TransacaoDuckDB(caminho)

    def inserir_e_falhar(conexao: object) -> None:
        repositorio.criar_lote(
            EXECUCAO_ID,
            [
                MensagemAprovada(uuid4(), Canal.SMS, SaidaCanal(corpo=CORPO_SMS)),
                MensagemAprovada(uuid4(), Canal.SMS, SaidaCanal(corpo=CORPO_SMS)),
            ],
            conexao,  # pyright: ignore[reportArgumentType]
        )
        raise RuntimeError("falha local durante a simulação")

    with pytest.raises(RuntimeError):
        transacao.executar(inserir_e_falhar)

    assert contar(caminho) == 0
    assert repositorio.listar_por_execucao(EXECUCAO_ID) == []


def test_criar_lote_commitado_na_transacao_do_chamador_persiste_o_lote(
    tmp_path: Path,
) -> None:
    """A contraprova do teste anterior: sem falha, a mesma transação confirma as entregas."""

    caminho = preparar(tmp_path)
    repositorio = RepositorioEntregasSimuladas(caminho)

    TransacaoDuckDB(caminho).executar(
        lambda conexao: repositorio.criar_lote(
            EXECUCAO_ID,
            [MensagemAprovada(uuid4(), Canal.SMS, SaidaCanal(corpo=CORPO_SMS))],
            conexao,
        )
    )

    assert contar(caminho) == 1


def test_listar_por_execucao_nao_mistura_entregas_de_outra_execucao(
    tmp_path: Path,
) -> None:
    """Cada simulação é independente da outra (terceiro Edge Case da spec)."""

    caminho = preparar(tmp_path)
    repositorio = RepositorioEntregasSimuladas(caminho)
    mensagem_da_execucao = uuid4()
    repositorio.criar_lote(
        EXECUCAO_ID,
        [MensagemAprovada(mensagem_da_execucao, Canal.SMS, SaidaCanal(corpo=CORPO_SMS))],
    )
    repositorio.criar_lote(
        OUTRA_EXECUCAO_ID,
        [MensagemAprovada(uuid4(), Canal.SMS, SaidaCanal(corpo=CORPO_SMS))],
    )

    entregas = repositorio.listar_por_execucao(EXECUCAO_ID)

    assert [entrega.mensagem_id for entrega in entregas] == [mensagem_da_execucao]
    assert contar(caminho) == 2


def test_segunda_entrega_da_mesma_mensagem_e_recusada_sem_duplicar(
    tmp_path: Path,
) -> None:
    """SIMUL-07: a `UNIQUE (mensagem_id)` (AD-010) impede uma segunda entrega da mesma
    mensagem, e a recusa chega ao chamador como erro próprio, não como falha genérica."""

    caminho = preparar(tmp_path)
    repositorio = RepositorioEntregasSimuladas(caminho)
    mensagem_id = uuid4()
    repositorio.criar_lote(
        EXECUCAO_ID, [MensagemAprovada(mensagem_id, Canal.SMS, SaidaCanal(corpo=CORPO_SMS))]
    )

    with pytest.raises(EntregaSimuladaJaExiste) as capturado:
        repositorio.criar_lote(
            EXECUCAO_ID,
            [MensagemAprovada(mensagem_id, Canal.SMS, SaidaCanal(corpo=CORPO_SMS))],
        )

    assert capturado.value.execucao_id == EXECUCAO_ID
    assert contar(caminho) == 1
