"""Testes do repositório de mensagens e versões (GERAR-06, GERAR-09, GERAR-10)."""

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    ConflitoVersaoMensagem,
    MensagemJaExiste,
    RepositorioMensagens,
    TransicaoMensagemInvalida,
)
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

EXECUCAO_ID = UUID("11111111-1111-1111-1111-111111111111")
ELEGIBILIDADE_ID = UUID("22222222-2222-2222-2222-222222222222")

CONTEUDO_SMS = SaidaCanal(corpo="Chuva forte hoje. Evite áreas alagadas.")
CONTEUDO_EMAIL = SaidaCanal(corpo="Chuva forte hoje na sua região.", assunto="Alerta preventivo")


def repositorio(tmp_path: Path) -> RepositorioMensagens:
    """Aplica as migrações versionadas em um banco temporário e devolve o repositório."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return RepositorioMensagens(caminho)


def test_criar_persiste_a_mensagem_em_gerando_na_tentativa_um(tmp_path: Path) -> None:
    """GERAR-06: a mensagem nasce vinculada à execução, à elegibilidade e ao canal."""

    repo = repositorio(tmp_path)

    mensagem_id = repo.criar(EXECUCAO_ID, ELEGIBILIDADE_ID, Canal.SMS)

    registro = repo.obter(mensagem_id)
    assert registro is not None
    assert registro.execucao_id == EXECUCAO_ID
    assert registro.elegibilidade_id == ELEGIBILIDADE_ID
    assert registro.canal is Canal.SMS
    assert registro.estado is EstadoMensagem.GERANDO
    assert registro.tentativa_atual == 1
    assert registro.versao == 1


def test_segunda_mensagem_para_o_mesmo_par_e_recusada_com_erro_especifico(
    tmp_path: Path,
) -> None:
    """GERAR-06: a `UNIQUE (elegibilidade_id, canal)` impede a segunda mensagem do par."""

    repo = repositorio(tmp_path)
    repo.criar(EXECUCAO_ID, ELEGIBILIDADE_ID, Canal.WHATSAPP)

    with pytest.raises(MensagemJaExiste) as captura:
        repo.criar(uuid4(), ELEGIBILIDADE_ID, Canal.WHATSAPP)

    assert captura.value.elegibilidade_id == ELEGIBILIDADE_ID
    assert captura.value.canal is Canal.WHATSAPP
    assert len(repo.listar_por_execucao(EXECUCAO_ID)) == 1


def test_mesma_elegibilidade_em_canal_diferente_e_permitida(tmp_path: Path) -> None:
    """A unicidade é do par: o mesmo item em outro canal é outra mensagem legítima."""

    repo = repositorio(tmp_path)
    repo.criar(EXECUCAO_ID, ELEGIBILIDADE_ID, Canal.WHATSAPP)

    repo.criar(EXECUCAO_ID, ELEGIBILIDADE_ID, Canal.EMAIL)

    canais = {registro.canal for registro in repo.listar_por_execucao(EXECUCAO_ID)}
    assert canais == {Canal.WHATSAPP, Canal.EMAIL}


def test_salvar_versao_persiste_conteudo_validade_metricas_e_prompt(tmp_path: Path) -> None:
    """GERAR-10: a versão registra conteúdo, duração, modelo, prompt e métricas de uso."""

    repo = repositorio(tmp_path)
    mensagem_id = repo.criar(EXECUCAO_ID, ELEGIBILIDADE_ID, Canal.EMAIL)

    repo.salvar_versao(
        mensagem_id=mensagem_id,
        numero_tentativa=1,
        conteudo=CONTEUDO_EMAIL,
        duracao_ms=812.5,
        modelo="gpt-4o-mini",
        versao_prompt="v1",
        tokens_entrada=310,
        tokens_saida=95,
        valida=True,
        motivo_invalidez=None,
    )

    versao = repo.obter_versao_atual(mensagem_id)
    assert versao is not None
    assert versao.mensagem_id == mensagem_id
    assert versao.numero_tentativa == 1
    assert versao.conteudo == CONTEUDO_EMAIL
    assert versao.valida is True
    assert versao.motivo_invalidez is None
    assert versao.duracao_ms == 812.5
    assert versao.modelo == "gpt-4o-mini"
    assert versao.versao_prompt == "v1"
    assert versao.tokens_entrada == 310
    assert versao.tokens_saida == 95


def test_salvar_versao_invalida_persiste_o_motivo(tmp_path: Path) -> None:
    """GERAR-09: o motivo da invalidez fica registrado para a próxima tentativa controlada."""

    repo = repositorio(tmp_path)
    mensagem_id = repo.criar(EXECUCAO_ID, ELEGIBILIDADE_ID, Canal.SMS)

    repo.salvar_versao(
        mensagem_id=mensagem_id,
        numero_tentativa=1,
        conteudo=SaidaCanal(corpo="a" * 161),
        duracao_ms=120.0,
        modelo="gpt-4o-mini",
        versao_prompt="v1",
        tokens_entrada=None,
        tokens_saida=None,
        valida=False,
        motivo_invalidez="limite_excedido:corpo:161:160",
    )

    versao = repo.obter_versao_atual(mensagem_id)
    assert versao is not None
    assert versao.valida is False
    assert versao.motivo_invalidez == "limite_excedido:corpo:161:160"
    assert versao.tokens_entrada is None
    assert versao.tokens_saida is None


def test_versao_atual_e_a_ultima_tentativa_persistida(tmp_path: Path) -> None:
    """A leitura da versão atual devolve a tentativa mais recente, não a primeira."""

    repo = repositorio(tmp_path)
    mensagem_id = repo.criar(EXECUCAO_ID, ELEGIBILIDADE_ID, Canal.SMS)
    repo.salvar_versao(
        mensagem_id, 1, SaidaCanal(corpo="primeira"), 10.0, "m", "v1", 1, 1, False, "motivo"
    )
    repo.salvar_versao(
        mensagem_id, 2, SaidaCanal(corpo="segunda"), 20.0, "m", "v1", 2, 2, True, None
    )

    versao = repo.obter_versao_atual(mensagem_id)
    assert versao is not None
    assert versao.numero_tentativa == 2
    assert versao.conteudo.corpo == "segunda"


def test_transicionar_avanca_o_estado_e_incrementa_a_versao(tmp_path: Path) -> None:
    """GERAR-10: a mensagem válida avança de `gerando` para `criticando`."""

    repo = repositorio(tmp_path)
    mensagem_id = repo.criar(EXECUCAO_ID, ELEGIBILIDADE_ID, Canal.SMS)

    repo.transicionar(mensagem_id, 1, EstadoMensagem.CRITICANDO)

    registro = repo.obter(mensagem_id)
    assert registro is not None
    assert registro.estado is EstadoMensagem.CRITICANDO
    assert registro.versao == 2


def test_transicionar_com_versao_errada_e_recusado_sem_mutar(tmp_path: Path) -> None:
    """AD-008: a checagem otimista recusa a mutação concorrente, sem efeito parcial."""

    repo = repositorio(tmp_path)
    mensagem_id = repo.criar(EXECUCAO_ID, ELEGIBILIDADE_ID, Canal.SMS)

    with pytest.raises(ConflitoVersaoMensagem):
        repo.transicionar(mensagem_id, 7, EstadoMensagem.CRITICANDO)

    registro = repo.obter(mensagem_id)
    assert registro is not None
    assert registro.estado is EstadoMensagem.GERANDO
    assert registro.versao == 1


def test_transicionar_a_partir_de_terminal_e_recusado(tmp_path: Path) -> None:
    """AD-7: um terminal de mensagem nunca reabre, mesma semântica da execução."""

    repo = repositorio(tmp_path)
    mensagem_id = repo.criar(EXECUCAO_ID, ELEGIBILIDADE_ID, Canal.SMS)
    repo.transicionar(mensagem_id, 1, EstadoMensagem.FALHOU_INTEGRACAO_IA)

    with pytest.raises(TransicaoMensagemInvalida) as captura:
        repo.transicionar(mensagem_id, 2, EstadoMensagem.CRITICANDO)

    assert captura.value.estado_atual is EstadoMensagem.FALHOU_INTEGRACAO_IA
    registro = repo.obter(mensagem_id)
    assert registro is not None
    assert registro.estado is EstadoMensagem.FALHOU_INTEGRACAO_IA
    assert registro.versao == 2


def test_listar_por_execucao_traz_apenas_as_mensagens_daquela_execucao(
    tmp_path: Path,
) -> None:
    """GERAR-11: a reidratação lê da persistência as mensagens da execução consultada."""

    repo = repositorio(tmp_path)
    primeira = repo.criar(EXECUCAO_ID, uuid4(), Canal.SMS)
    segunda = repo.criar(EXECUCAO_ID, uuid4(), Canal.EMAIL)
    repo.criar(uuid4(), uuid4(), Canal.WHATSAPP)

    registros = repo.listar_por_execucao(EXECUCAO_ID)

    assert {registro.id for registro in registros} == {primeira, segunda}


def test_conteudo_de_whatsapp_e_sms_nao_carrega_assunto(tmp_path: Path) -> None:
    """O conteúdo persistido tem exatamente os campos do canal: `{corpo}` sem assunto."""

    repo = repositorio(tmp_path)
    mensagem_id = repo.criar(EXECUCAO_ID, ELEGIBILIDADE_ID, Canal.SMS)
    repo.salvar_versao(
        mensagem_id, 1, CONTEUDO_SMS, 10.0, "gpt-4o-mini", "v1", 5, 5, True, None
    )

    versao = repo.obter_versao_atual(mensagem_id)
    assert versao is not None
    assert versao.conteudo.assunto is None
    assert versao.conteudo.corpo == CONTEUDO_SMS.corpo
