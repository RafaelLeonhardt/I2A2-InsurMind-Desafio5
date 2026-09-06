"""Testes do caso de uso da lista de comunicados do segurado (COMUNICADOS-01, COMUNICADOS-02).

Os repositórios são os reais, sobre um banco temporário migrado — mesma escolha de
`test_lista_alertas_segurado.py` (5.2) e `test_visualizacao_comunicado.py` (4.3).
"""

from pathlib import Path
from uuid import UUID, uuid4

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
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
from central_preventiva.aplicacao.lista_comunicados import (
    PortasListaComunicados,
    ServicoListaComunicados,
)
from central_preventiva.dominio.avaliador_elegibilidade import (
    OPERANDO_AREA_AFETADA,
    OPERANDO_COBERTURA_EXIGIDA,
)
from central_preventiva.dominio.avaliador_risco import Criterio
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

EXECUCAO_ID = UUID("11111111-1111-1111-1111-111111111111")
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
        self.visualizacoes = RepositorioVisualizacoesComunicado(self.caminho)
        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(
                "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
                "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
                "VALUES (?, 'chuva_intensa', 50.0, '9990001', 'residencial', 'alagamento', "
                "6, 'sms', 1, 'ativa')",
                [uuid4()],
            )
            conexao.execute(
                "INSERT INTO execucao_preventiva (id, estado, versao) "
                "VALUES (?, 'concluida', 1)",
                [EXECUCAO_ID],
            )
        self.servico = ServicoListaComunicados(
            PortasListaComunicados(entregas=self.entregas, visualizacoes=self.visualizacoes)
        )

    def entrega(
        self,
        canal: Canal = Canal.SMS,
        corpo: str = "Chuva forte hoje.",
        segurado_id: UUID = CARLOS_ID,
        estado: EstadoMensagem = EstadoMensagem.SIMULADA_ENTREGUE,
    ) -> UUID:
        """Semeia elegibilidade+mensagem+entrega simulada para o segurado informado."""

        elegibilidade_id = uuid4()
        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(
                "INSERT INTO elegibilidades_historicas "
                "(id, execucao_id, evento_id, regra_id, segurado_id, "
                "apolice_id, elegivel, criterios, canal, nome_segurado, justificativa) "
                "VALUES (?, ?, ?, ?, ?, ?, true, ?, ?, 'Carlos Teste', "
                "'Atende integralmente aos critérios da regra ativa.')",
                [
                    elegibilidade_id,
                    EXECUCAO_ID,
                    uuid4(),
                    uuid4(),
                    segurado_id,
                    uuid4(),
                    serializar_criterios(CRITERIOS),
                    canal.value,
                ],
            )
        mensagem_id = self.mensagens.criar(EXECUCAO_ID, elegibilidade_id, canal)
        [entrega_id] = self.entregas.criar_lote(
            EXECUCAO_ID, [MensagemAprovada(mensagem_id, canal, SaidaCanal(corpo=corpo))]
        )
        if estado is not EstadoMensagem.GERANDO:
            self.mensagens.transicionar(mensagem_id, 1, estado)
        return entrega_id


def test_listar_devolve_lista_vazia_sem_nenhum_comunicado(tmp_path: Path) -> None:
    """COMUNICADOS-01, AC2: segurado sem comunicados recebe lista vazia."""

    cenario = Cenario(tmp_path)

    assert cenario.servico.listar(CARLOS_ID) == []


def test_listar_traz_canal_assunto_ou_resumo_data_e_visualizacao_pendente(
    tmp_path: Path,
) -> None:
    """COMUNICADOS-01, AC1: canal, assunto/resumo, data de cada registro do segurado."""

    cenario = Cenario(tmp_path)
    entrega_id = cenario.entrega(Canal.SMS, corpo="Chuva forte hoje.")

    [item] = cenario.servico.listar(CARLOS_ID)

    assert item.entrega_simulada_id == entrega_id
    assert item.canal is Canal.SMS
    assert item.assunto_ou_resumo == "Chuva forte hoje."
    assert item.criado_em is not None
    assert item.visualizacao is None


def test_listar_retorna_visualizacao_registrada_quando_ja_visualizado(tmp_path: Path) -> None:
    """COMUNICADOS-02: um comunicado já visualizado traz o estado 'Visualizada no portal'."""

    cenario = Cenario(tmp_path)
    entrega_id = cenario.entrega()
    visualizacao = cenario.visualizacoes.registrar_primeira_visualizacao(entrega_id, CARLOS_ID)

    [item] = cenario.servico.listar(CARLOS_ID)

    assert item.visualizacao == visualizacao


def test_listar_nao_mistura_comunicados_de_outro_segurado(tmp_path: Path) -> None:
    """COMUNICADOS-01, AC1: só comunicados do segurado ativo, nunca de outro."""

    cenario = Cenario(tmp_path)
    cenario.entrega(segurado_id=OUTRO_SEGURADO_ID)

    assert cenario.servico.listar(CARLOS_ID) == []
