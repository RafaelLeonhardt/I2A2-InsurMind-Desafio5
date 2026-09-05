"""Testes do caso de uso da visualização do comunicado (VISU-01, 04, 05).

Os repositórios são os reais, sobre um banco temporário migrado: a visualização é uma junção
de leitura mais uma escrita de dedução por `UNIQUE`, ambas já garantidas pelo próprio DuckDB —
testá-las com dublê provaria pouco. Mesma escolha de `test_simulacao.py`/
`test_detalhe_resultado.py`.
"""

from pathlib import Path
from uuid import UUID, uuid4

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RepositorioElegibilidades,
)
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    MensagemAprovada,
    RepositorioEntregasSimuladas,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    RepositorioMensagens,
)
from central_preventiva.adaptadores.persistencia.repositorio_visualizacoes_comunicado import (
    RepositorioVisualizacoesComunicado,
)
from central_preventiva.adaptadores.persistencia.serializacao_criterios import (
    serializar_criterios,
)
from central_preventiva.aplicacao.visualizacao_comunicado import (
    MensagemNaoElegivelParaComunicado,
    PortasVisualizacaoComunicado,
    ServicoVisualizacaoComunicado,
)
from central_preventiva.dominio.avaliador_elegibilidade import (
    OPERANDO_AREA_AFETADA,
    OPERANDO_COBERTURA_EXIGIDA,
)
from central_preventiva.dominio.avaliador_risco import Criterio
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

EXECUCAO_ID = UUID("11111111-1111-1111-1111-111111111111")
EVENTO_ID = UUID("22222222-2222-2222-2222-222222222222")
REGRA_ID = UUID("33333333-3333-3333-3333-333333333333")
CARLOS_ID = UUID("44444444-4444-4444-4444-444444444444")
OUTRO_SEGURADO_ID = UUID("55555555-5555-5555-5555-555555555555")
CRITERIOS = (
    Criterio(OPERANDO_AREA_AFETADA, "9990001", True, "Área corresponde."),
    Criterio(OPERANDO_COBERTURA_EXIGIDA, "alagamento", True, "Possui cobertura."),
)


class Cenario:
    """Reúne o caso de uso real e os repositórios reais sobre um banco temporário migrado."""

    def __init__(self, tmp_path: Path) -> None:
        """Migra o banco e semeia regra/execução."""

        self.caminho = tmp_path / "central_preventiva.duckdb"
        ExecutorMigracoes(self.caminho).aplicar_pendentes()
        self.mensagens = RepositorioMensagens(self.caminho)
        self.entregas = RepositorioEntregasSimuladas(self.caminho)
        self.elegibilidades = RepositorioElegibilidades(self.caminho)
        self.visualizacoes = RepositorioVisualizacoesComunicado(self.caminho)
        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(
                "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
                "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
                "VALUES (?, 'chuva_intensa', 50.0, '9990001', 'residencial', 'alagamento', "
                "6, 'sms', 1, 'ativa')",
                [REGRA_ID],
            )
            conexao.execute(
                "INSERT INTO execucao_preventiva (id, estado, versao) "
                "VALUES (?, 'concluida', 1)",
                [EXECUCAO_ID],
            )
        self.servico = ServicoVisualizacaoComunicado(
            PortasVisualizacaoComunicado(
                mensagens=self.mensagens,
                entregas=self.entregas,
                elegibilidades=self.elegibilidades,
                visualizacoes=self.visualizacoes,
            )
        )

    def elegibilidade(self, segurado_id: UUID) -> UUID:
        """Insere um item do público elegível para o segurado informado."""

        id_registro = uuid4()
        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(
                "INSERT INTO elegibilidades_historicas "
                "(id, execucao_id, evento_id, regra_id, segurado_id, "
                "apolice_id, elegivel, criterios, canal, nome_segurado, justificativa) "
                "VALUES (?, ?, ?, ?, ?, ?, true, ?, 'sms', 'Carlos Teste', "
                "'Atende integralmente aos critérios da regra ativa.')",
                [
                    id_registro,
                    EXECUCAO_ID,
                    EVENTO_ID,
                    REGRA_ID,
                    segurado_id,
                    uuid4(),
                    serializar_criterios(CRITERIOS),
                ],
            )
        return id_registro

    def entrega(
        self,
        estado: EstadoMensagem = EstadoMensagem.SIMULADA_ENTREGUE,
        segurado_id: UUID = CARLOS_ID,
    ) -> UUID:
        """Cria mensagem+entrega simulada para o segurado informado, no estado pedido.

        Uma entrega simulada só existe de verdade quando `entregas_simuladas.criar_lote` é
        chamado (3.6, sempre que a mensagem chega a `simulada_entregue`); para os demais
        estados (não elegíveis), a linha de teste ainda precisa de uma entrega para exercitar
        `obter_por_id`, então ela é criada da mesma forma e a mensagem é transicionada depois.
        """

        elegibilidade_id = self.elegibilidade(segurado_id)
        mensagem_id = self.mensagens.criar(EXECUCAO_ID, elegibilidade_id, Canal.SMS)
        [entrega_id] = self.entregas.criar_lote(
            EXECUCAO_ID,
            [MensagemAprovada(mensagem_id, Canal.SMS, SaidaCanal(corpo="Chuva forte hoje."))],
        )
        if estado is not EstadoMensagem.GERANDO:
            self.mensagens.transicionar(mensagem_id, 1, estado)
        return entrega_id


def test_registrar_visualizacao_grava_quando_mensagem_esta_simulada_entregue(
    tmp_path: Path,
) -> None:
    """VISU-01: mensagem em `simulada_entregue` registra a primeira visualização."""

    cenario = Cenario(tmp_path)
    entrega_id = cenario.entrega(EstadoMensagem.SIMULADA_ENTREGUE)

    visualizacao = cenario.servico.registrar_visualizacao(entrega_id, CARLOS_ID)

    assert visualizacao is not None
    assert visualizacao.entrega_simulada_id == entrega_id
    assert visualizacao.segurado_id == CARLOS_ID
    assert cenario.visualizacoes.obter_por_entrega(entrega_id) == visualizacao


def test_registrar_visualizacao_recusa_mensagem_falhou_conteudo_sem_gravar(
    tmp_path: Path,
) -> None:
    """VISU-04: mensagem em `falhou_conteudo` é recusada, sem nenhum marco criado."""

    cenario = Cenario(tmp_path)
    entrega_id = cenario.entrega(EstadoMensagem.FALHOU_CONTEUDO)

    try:
        cenario.servico.registrar_visualizacao(entrega_id, CARLOS_ID)
        raise AssertionError("deveria ter recusado")
    except MensagemNaoElegivelParaComunicado as recusa:
        assert recusa.entrega_simulada_id == entrega_id
        assert recusa.estado is EstadoMensagem.FALHOU_CONTEUDO

    assert cenario.visualizacoes.obter_por_entrega(entrega_id) is None


def test_registrar_visualizacao_recusa_mensagem_rejeitada_sem_gravar(tmp_path: Path) -> None:
    """VISU-04: mensagem `rejeitada` é recusada, sem nenhum marco criado."""

    cenario = Cenario(tmp_path)
    entrega_id = cenario.entrega(EstadoMensagem.REJEITADA)

    try:
        cenario.servico.registrar_visualizacao(entrega_id, CARLOS_ID)
        raise AssertionError("deveria ter recusado")
    except MensagemNaoElegivelParaComunicado:
        pass

    assert cenario.visualizacoes.obter_por_entrega(entrega_id) is None


def test_registrar_visualizacao_recusa_mensagem_excluida_sem_gravar(tmp_path: Path) -> None:
    """VISU-04: mensagem `excluida` é recusada, sem nenhum marco criado."""

    cenario = Cenario(tmp_path)
    entrega_id = cenario.entrega(EstadoMensagem.EXCLUIDA)

    try:
        cenario.servico.registrar_visualizacao(entrega_id, CARLOS_ID)
        raise AssertionError("deveria ter recusado")
    except MensagemNaoElegivelParaComunicado:
        pass

    assert cenario.visualizacoes.obter_por_entrega(entrega_id) is None


def test_registrar_visualizacao_recusa_mensagem_ainda_gerando_sem_gravar(
    tmp_path: Path,
) -> None:
    """VISU-04: mensagem ainda não simulada (`gerando`) é recusada, sem nenhum marco criado."""

    cenario = Cenario(tmp_path)
    entrega_id = cenario.entrega(EstadoMensagem.GERANDO)

    try:
        cenario.servico.registrar_visualizacao(entrega_id, CARLOS_ID)
        raise AssertionError("deveria ter recusado")
    except MensagemNaoElegivelParaComunicado:
        pass

    assert cenario.visualizacoes.obter_por_entrega(entrega_id) is None


def test_obter_comunicado_de_outro_segurado_devolve_none(tmp_path: Path) -> None:
    """VISU-05: entrega de outro segurado devolve o mesmo `None` de uma entrega
    inexistente (AD-011)."""

    cenario = Cenario(tmp_path)
    entrega_id = cenario.entrega(EstadoMensagem.SIMULADA_ENTREGUE, segurado_id=OUTRO_SEGURADO_ID)

    comunicado_de_outro = cenario.servico.obter_comunicado(entrega_id, CARLOS_ID)
    comunicado_inexistente = cenario.servico.obter_comunicado(uuid4(), CARLOS_ID)

    assert comunicado_de_outro is None
    assert comunicado_inexistente is None


def test_registrar_visualizacao_de_outro_segurado_devolve_none_sem_gravar(
    tmp_path: Path,
) -> None:
    """VISU-05: o POST de visualização também aplica o isolamento por segurado, não só o GET."""

    cenario = Cenario(tmp_path)
    entrega_id = cenario.entrega(EstadoMensagem.SIMULADA_ENTREGUE, segurado_id=OUTRO_SEGURADO_ID)

    resultado = cenario.servico.registrar_visualizacao(entrega_id, CARLOS_ID)

    assert resultado is None
    assert cenario.visualizacoes.obter_por_entrega(entrega_id) is None


def test_obter_comunicado_traz_apresentacao_canal_e_visualizacao_quando_ja_vista(
    tmp_path: Path,
) -> None:
    """P1 AC1/AC2: o comunicado exibe conteúdo, canal e a visualização, quando já registrada."""

    cenario = Cenario(tmp_path)
    entrega_id = cenario.entrega(EstadoMensagem.SIMULADA_ENTREGUE)

    antes = cenario.servico.obter_comunicado(entrega_id, CARLOS_ID)
    cenario.servico.registrar_visualizacao(entrega_id, CARLOS_ID)
    depois = cenario.servico.obter_comunicado(entrega_id, CARLOS_ID)

    assert antes is not None
    assert antes.visualizacao is None
    assert antes.canal is Canal.SMS
    assert antes.apresentacao.corpo == "Chuva forte hoje."
    assert depois is not None
    assert depois.visualizacao is not None
    assert depois.visualizacao.segurado_id == CARLOS_ID
