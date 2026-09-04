"""Testes do caso de uso de consolidação de resultados (RESULT-01..07,09).

Os repositórios de mensagem, entrega simulada e execução são os reais, sobre um banco
temporário migrado: a consolidação é uma leitura pura sobre schema já garantido por 3.2/3.6,
sem nenhuma escrita própria a testar com dublê.
"""

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    MensagemAprovada,
    RepositorioEntregasSimuladas,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    RepositorioExecucaoPreventiva,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    RepositorioMensagens,
)
from central_preventiva.aplicacao.consolidacao_resultados import (
    ExecucaoInexistente,
    PortasConsolidacaoResultados,
    ServicoConsolidacaoResultados,
)
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

EXECUCAO_ID = UUID("11111111-1111-1111-1111-111111111111")
CONTEUDO = SaidaCanal(corpo="Chuva forte hoje. Evite áreas alagadas.")


class Cenario:
    """Reúne o serviço real e os repositórios reais sobre um banco temporário migrado."""

    def __init__(self, tmp_path: Path, estado: EstadoExecucao) -> None:
        """Migra o banco e cria a execução no estado informado."""

        self.caminho = tmp_path / "central_preventiva.duckdb"
        ExecutorMigracoes(self.caminho).aplicar_pendentes()
        self.mensagens = RepositorioMensagens(self.caminho)
        self.entregas = RepositorioEntregasSimuladas(self.caminho)
        self.execucoes = RepositorioExecucaoPreventiva(self.caminho)
        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(
                "INSERT INTO execucao_preventiva (id, estado, versao) VALUES (?, ?, 1)",
                [EXECUCAO_ID, estado.value],
            )
        self.servico = ServicoConsolidacaoResultados(
            PortasConsolidacaoResultados(
                execucoes=self.execucoes, mensagens=self.mensagens, entregas=self.entregas
            )
        )

    def mensagem(self, canal: Canal, estado: EstadoMensagem) -> UUID:
        """Cria uma mensagem da execução do cenário, já no estado informado."""

        mensagem_id = self.mensagens.criar(EXECUCAO_ID, uuid4(), canal)
        if estado is not EstadoMensagem.GERANDO:
            self.mensagens.transicionar(mensagem_id, 1, estado)
        return mensagem_id

    def entregar(self, mensagem_id: UUID, canal: Canal) -> None:
        """Cria a entrega simulada real de uma mensagem já `simulada_entregue`."""

        self.entregas.criar_lote(
            EXECUCAO_ID, [MensagemAprovada(mensagem_id, canal, CONTEUDO)]
        )


def test_totais_reconciliam_simuladas_rejeitada_e_em_excecao(tmp_path: Path) -> None:
    """RESULT-02/03: 3 simuladas + 1 rejeitada + 1 em exceção — as 2 últimas em
    `nao_simulaveis`, nunca somadas às entregas simuladas."""

    cenario = Cenario(tmp_path, EstadoExecucao.CONCLUIDA)
    simuladas = [
        cenario.mensagem(Canal.SMS, EstadoMensagem.SIMULADA_ENTREGUE),
        cenario.mensagem(Canal.EMAIL, EstadoMensagem.SIMULADA_ENTREGUE),
        cenario.mensagem(Canal.WHATSAPP, EstadoMensagem.SIMULADA_ENTREGUE),
    ]
    for mensagem_id, canal in zip(simuladas, [Canal.SMS, Canal.EMAIL, Canal.WHATSAPP], strict=True):
        cenario.entregar(mensagem_id, canal)
    rejeitada_id = cenario.mensagem(Canal.SMS, EstadoMensagem.REJEITADA)
    excecao_id = cenario.mensagem(Canal.EMAIL, EstadoMensagem.FALHOU_CONTEUDO)

    resultado = cenario.servico.consolidar(EXECUCAO_ID)

    assert resultado.concluido is True
    assert dict(resultado.totais_por_estado)[EstadoMensagem.SIMULADA_ENTREGUE] == 3
    assert dict(resultado.totais_por_estado)[EstadoMensagem.REJEITADA] == 1
    assert dict(resultado.totais_por_estado)[EstadoMensagem.FALHOU_CONTEUDO] == 1
    assert sum(total for _, total in resultado.totais_por_canal) == 5
    ids_nao_simulaveis = {item.mensagem_id for item in resultado.nao_simulaveis}
    assert ids_nao_simulaveis == {rejeitada_id, excecao_id}
    assert resultado.divergencia is None


def test_nao_simulaveis_carregam_motivo_legivel_por_estado(tmp_path: Path) -> None:
    """RESULT-03: rejeitada e excluída têm motivos distintos e legíveis, não genéricos."""

    cenario = Cenario(tmp_path, EstadoExecucao.CONCLUIDA)
    rejeitada_id = cenario.mensagem(Canal.SMS, EstadoMensagem.REJEITADA)
    excluida_id = cenario.mensagem(Canal.EMAIL, EstadoMensagem.EXCLUIDA)

    resultado = cenario.servico.consolidar(EXECUCAO_ID)

    motivos = {item.mensagem_id: item.motivo for item in resultado.nao_simulaveis}
    assert motivos[rejeitada_id] == "rejeitada pela revisão humana"
    assert motivos[excluida_id] == "excluída da revisão humana"
    assert motivos[rejeitada_id] != motivos[excluida_id]


def test_falhou_simulacao_mostra_mensagens_ainda_aprovadas_sem_falha_de_canal(
    tmp_path: Path,
) -> None:
    """RESULT-04/05: `falhou_simulacao` mostra zero simuladas, mensagens em `aprovada`,
    nenhum texto de falha de canal (nenhuma delas cai em `nao_simulaveis`)."""

    cenario = Cenario(tmp_path, EstadoExecucao.FALHOU_SIMULACAO)
    cenario.mensagem(Canal.SMS, EstadoMensagem.APROVADA)
    cenario.mensagem(Canal.EMAIL, EstadoMensagem.APROVADA)

    resultado = cenario.servico.consolidar(EXECUCAO_ID)

    assert resultado.concluido is True
    assert dict(resultado.totais_por_estado)[EstadoMensagem.APROVADA] == 2
    assert EstadoMensagem.SIMULADA_ENTREGUE not in dict(resultado.totais_por_estado)
    assert resultado.nao_simulaveis == ()
    assert resultado.divergencia is None
    textos_motivo = {item.motivo for item in resultado.nao_simulaveis}
    assert not any(
        termo in texto.lower()
        for texto in textos_motivo
        for termo in ("whatsapp", "e-mail", "sms", "canal")
    )


def test_consolidar_duas_vezes_e_identico_sem_efeito_colateral(tmp_path: Path) -> None:
    """RESULT-06/07: reidratação pura — duas chamadas seguidas dão o mesmo resultado e não
    criam nenhuma linha nova."""

    cenario = Cenario(tmp_path, EstadoExecucao.CONCLUIDA)
    mensagem_id = cenario.mensagem(Canal.SMS, EstadoMensagem.SIMULADA_ENTREGUE)
    cenario.entregar(mensagem_id, Canal.SMS)

    primeira = cenario.servico.consolidar(EXECUCAO_ID)
    segunda = cenario.servico.consolidar(EXECUCAO_ID)

    assert primeira == segunda
    assert len(cenario.entregas.listar_por_execucao(EXECUCAO_ID)) == 1
    assert len(cenario.mensagens.listar_por_execucao(EXECUCAO_ID)) == 1


def test_divergencia_forcada_correlaciona_sem_corrigir_o_total(tmp_path: Path) -> None:
    """RESULT-09: 2 mensagens `simulada_entregue` mas só 1 entrega persistida — reportado
    como `totais_divergentes` com os dois lados, sem alterar o total exibido."""

    cenario = Cenario(tmp_path, EstadoExecucao.CONCLUIDA)
    primeira_id = cenario.mensagem(Canal.SMS, EstadoMensagem.SIMULADA_ENTREGUE)
    cenario.mensagem(Canal.EMAIL, EstadoMensagem.SIMULADA_ENTREGUE)
    cenario.entregar(primeira_id, Canal.SMS)

    resultado = cenario.servico.consolidar(EXECUCAO_ID)

    assert resultado.divergencia is not None
    assert resultado.divergencia.execucao_id == EXECUCAO_ID
    assert resultado.divergencia.mensagens_simulada_entregue == 2
    assert resultado.divergencia.entregas_persistidas == 1
    assert dict(resultado.totais_por_estado)[EstadoMensagem.SIMULADA_ENTREGUE] == 2


def test_execucao_ainda_simulando_nao_traz_totais_finais(tmp_path: Path) -> None:
    """Edge Case da spec: consulta durante `simulando` mostra o progresso real, nunca um
    total parcial apresentado como final."""

    cenario = Cenario(tmp_path, EstadoExecucao.SIMULANDO)
    cenario.mensagem(Canal.SMS, EstadoMensagem.APROVADA)

    resultado = cenario.servico.consolidar(EXECUCAO_ID)

    assert resultado.concluido is False
    assert resultado.estado is EstadoExecucao.SIMULANDO
    assert resultado.totais_por_canal == ()
    assert resultado.totais_por_estado == ()
    assert resultado.nao_simulaveis == ()
    assert resultado.divergencia is None


def test_execucao_sem_nenhuma_aprovada_mostra_zero_simuladas_sem_erro(tmp_path: Path) -> None:
    """Edge Case da spec: nenhuma mensagem aprovada no lote — totais mostram zero entregas
    simuladas, sem erro técnico."""

    cenario = Cenario(tmp_path, EstadoExecucao.CONCLUIDA)
    cenario.mensagem(Canal.SMS, EstadoMensagem.REJEITADA)
    cenario.mensagem(Canal.EMAIL, EstadoMensagem.EXCLUIDA)

    resultado = cenario.servico.consolidar(EXECUCAO_ID)

    assert EstadoMensagem.SIMULADA_ENTREGUE not in dict(resultado.totais_por_estado)
    assert len(resultado.nao_simulaveis) == 2
    assert resultado.divergencia is None


def test_duas_execucoes_distintas_sao_calculadas_independentemente(tmp_path: Path) -> None:
    """Edge Case da spec: origem e retentativa correlacionada nunca misturam contagens."""

    cenario = Cenario(tmp_path, EstadoExecucao.CONCLUIDA)
    mensagem_id = cenario.mensagem(Canal.SMS, EstadoMensagem.SIMULADA_ENTREGUE)
    cenario.entregar(mensagem_id, Canal.SMS)
    outra_execucao_id = uuid4()
    with abrir_conexao(cenario.caminho) as conexao:
        conexao.execute(
            "INSERT INTO execucao_preventiva (id, estado, versao) VALUES (?, ?, 1)",
            [outra_execucao_id, EstadoExecucao.CONCLUIDA.value],
        )
    outra_mensagem_id = cenario.mensagens.criar(outra_execucao_id, uuid4(), Canal.EMAIL)
    cenario.mensagens.transicionar(outra_mensagem_id, 1, EstadoMensagem.REJEITADA)

    resultado = cenario.servico.consolidar(outra_execucao_id)

    assert dict(resultado.totais_por_estado) == {EstadoMensagem.REJEITADA: 1}
    assert resultado.nao_simulaveis[0].mensagem_id == outra_mensagem_id


def test_execucao_inexistente_levanta_erro_especifico(tmp_path: Path) -> None:
    """AD-011: um `execucao_id` que não existe é recusado com um erro identificável."""

    cenario = Cenario(tmp_path, EstadoExecucao.CONCLUIDA)

    with pytest.raises(ExecucaoInexistente) as captura:
        cenario.servico.consolidar(uuid4())

    assert captura.value.execucao_id != EXECUCAO_ID
