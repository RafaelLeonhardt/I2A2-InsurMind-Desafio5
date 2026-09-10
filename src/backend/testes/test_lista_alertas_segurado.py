"""Testes do caso de uso da lista e do detalhe dos alertas do segurado (ALERTAS-01..06, 5.2).

Os repositórios são os reais, sobre um banco temporário migrado — mesma escolha de
`test_alerta_segurado.py` (5.1) e `test_detalhe_resultado.py` (4.2).
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from central_preventiva.adaptadores.http.linha_do_tempo import montar_servico_linha_do_tempo
from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RepositorioElegibilidades,
)
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    MensagemAprovada,
    RepositorioEntregasSimuladas,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    RepositorioExecucaoPreventiva,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import RepositorioMensagens
from central_preventiva.adaptadores.persistencia.repositorio_meteorologia import (
    RepositorioAreasMonitoradas,
    RepositorioEventosMeteorologicos,
    RepositorioSincronizacoes,
    RepositorioTentativasColeta,
)
from central_preventiva.adaptadores.persistencia.repositorio_regras import RepositorioRegras
from central_preventiva.aplicacao.alerta_segurado import PortasAlertaSegurado, ServicoAlertaSegurado
from central_preventiva.aplicacao.lista_alertas_segurado import (
    ClassificacaoAlerta,
    PortasListaAlertasSegurado,
    ServicoListaAlertasSegurado,
)
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.avaliador_elegibilidade import ResultadoElegibilidade
from central_preventiva.dominio.avaliador_risco import Criterio
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

AREA = "9990001"
REGRA_ID = uuid4()
SEGURADO_ID = uuid4()
OUTRO_SEGURADO_ID = uuid4()
APOLICE_ID = uuid4()

RESULTADO_INCLUIDO = ResultadoElegibilidade(
    elegivel=True,
    criterios=(Criterio("área afetada", AREA, True, "Área corresponde."),),
    canal="whatsapp",
    motivo="incluido",
    justificativa="Segurado e apólice atendem à regra ativa.",
)


class Contexto:
    """Reúne o caso de uso real e os repositórios reais sobre um banco temporário migrado."""

    def __init__(self, tmp_path: Path) -> None:
        """Migra o banco e compõe o serviço real sobre os repositórios reais."""

        self.caminho = tmp_path / "central_preventiva.duckdb"
        ExecutorMigracoes(self.caminho).aplicar_pendentes()
        self.elegibilidades = RepositorioElegibilidades(self.caminho)
        self.eventos = RepositorioEventosMeteorologicos(self.caminho)
        self.regras = RepositorioRegras(self.caminho)
        self.execucoes = RepositorioExecucaoPreventiva(self.caminho)
        self.mensagens = RepositorioMensagens(self.caminho)
        self.entregas = RepositorioEntregasSimuladas(self.caminho)
        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(
                "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
                "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
                "VALUES (?, 'chuva_intensa', 50.0, ?, 'residencial', 'alagamento', 24, "
                "'whatsapp', 1, 'ativa')",
                [REGRA_ID, AREA],
            )
        alerta_segurado = ServicoAlertaSegurado(
            PortasAlertaSegurado(
                elegibilidades=self.elegibilidades,
                eventos=self.eventos,
                regras=self.regras,
                areas_monitoradas=RepositorioAreasMonitoradas(self.caminho),
                sincronizacoes=RepositorioSincronizacoes(self.caminho),
                tentativas=RepositorioTentativasColeta(self.caminho),
                entregas=self.entregas,
            )
        )
        configuracao = Configuracao(
            host_api="127.0.0.1",
            origem_frontend="http://127.0.0.1:5151",
            caminho_banco=self.caminho,
        )
        self.servico = ServicoListaAlertasSegurado(
            PortasListaAlertasSegurado(
                elegibilidades=self.elegibilidades,
                execucoes=self.execucoes,
                alerta_segurado=alerta_segurado,
                linha_do_tempo=montar_servico_linha_do_tempo(configuracao),
            )
        )

    def salvar_evento(
        self, periodo_inicio: datetime, periodo_fim: datetime
    ) -> EventoMeteorologico:
        """Persiste um evento real cujo período é informado pelo teste."""

        evento = EventoMeteorologico(
            id=uuid4(),
            tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
            area=AREA,
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            intensidade=62.5,
            proveniencia=ProvenienciaEvento.REAL_INMET,
            instante_observado=periodo_inicio,
        )
        self.eventos.salvar(evento)
        return evento

    def salvar_elegibilidade(
        self,
        evento_id: UUID,
        execucao_id: UUID | None,
        segurado_id: UUID = SEGURADO_ID,
    ) -> UUID:
        """Persiste a elegibilidade `incluido` do segurado para o evento informado."""

        if execucao_id is None:
            id_registro = uuid4()
            with abrir_conexao(self.caminho) as conexao:
                conexao.execute(
                    "INSERT INTO elegibilidades_historicas "
                    "(id, execucao_id, evento_id, regra_id, segurado_id, apolice_id, "
                    "elegivel, criterios, canal, nome_segurado, justificativa) "
                    "VALUES (?, NULL, ?, ?, ?, ?, true, '[]', 'whatsapp', 'Pessoa Teste', "
                    "'semeado')",
                    [id_registro, evento_id, REGRA_ID, segurado_id, APOLICE_ID],
                )
            return id_registro
        id_registro = self.elegibilidades.salvar(
            execucao_id, evento_id, REGRA_ID, segurado_id, APOLICE_ID, "Pessoa Teste",
            RESULTADO_INCLUIDO,
        )
        assert id_registro is not None
        return id_registro

    def marcar_entrega_simulada(self, elegibilidade_id: UUID) -> UUID:
        """Cria mensagem+entrega `simulada_entregue` para a elegibilidade (6.8)."""

        execucao_id = uuid4()
        mensagem_id = self.mensagens.criar(execucao_id, elegibilidade_id, Canal.WHATSAPP)
        [entrega_id] = self.entregas.criar_lote(
            execucao_id,
            [MensagemAprovada(mensagem_id, Canal.WHATSAPP, SaidaCanal(corpo="Corpo"))],
        )
        self.mensagens.transicionar(mensagem_id, 1, EstadoMensagem.SIMULADA_ENTREGUE)
        return entrega_id


def _periodo_futuro() -> tuple[datetime, datetime]:
    daqui_uma_semana = datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7)
    return daqui_uma_semana, daqui_uma_semana + timedelta(hours=6)


def _periodo_passado() -> tuple[datetime, datetime]:
    ha_uma_semana = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=7)
    return ha_uma_semana, ha_uma_semana + timedelta(hours=6)


def test_listar_devolve_lista_vazia_sem_nenhum_alerta(tmp_path: Path) -> None:
    contexto = Contexto(tmp_path)

    assert contexto.servico.listar(SEGURADO_ID) == []


def test_listar_classifica_execucao_nao_terminal_como_ainda_nao_simulado(
    tmp_path: Path,
) -> None:
    contexto = Contexto(tmp_path)
    inicio, fim = _periodo_futuro()
    evento = contexto.salvar_evento(inicio, fim)
    execucao_id = contexto.execucoes.criar(EstadoExecucao.SIMULANDO)
    contexto.salvar_elegibilidade(evento.id, execucao_id)

    [item] = contexto.servico.listar(SEGURADO_ID)

    assert item.classificacao is ClassificacaoAlerta.AINDA_NAO_SIMULADO


def test_listar_classifica_execucao_concluida_dentro_do_periodo_como_ativo(
    tmp_path: Path,
) -> None:
    contexto = Contexto(tmp_path)
    inicio, fim = _periodo_futuro()
    evento = contexto.salvar_evento(inicio, fim)
    execucao_id = contexto.execucoes.criar(EstadoExecucao.CONCLUIDA)
    contexto.salvar_elegibilidade(evento.id, execucao_id)

    [item] = contexto.servico.listar(SEGURADO_ID)

    assert item.classificacao is ClassificacaoAlerta.ATIVO


def test_listar_classifica_execucao_concluida_fora_do_periodo_como_anterior(
    tmp_path: Path,
) -> None:
    contexto = Contexto(tmp_path)
    inicio, fim = _periodo_passado()
    evento = contexto.salvar_evento(inicio, fim)
    execucao_id = contexto.execucoes.criar(EstadoExecucao.FALHOU_SIMULACAO)
    contexto.salvar_elegibilidade(evento.id, execucao_id)

    [item] = contexto.servico.listar(SEGURADO_ID)

    assert item.classificacao is ClassificacaoAlerta.ANTERIOR


def test_listar_classifica_linha_semeada_sem_execucao_pelo_periodo(tmp_path: Path) -> None:
    """SPEC_DEVIATION do módulo: sem execução, classifica só pelo período."""

    contexto = Contexto(tmp_path)
    inicio, fim = _periodo_futuro()
    evento = contexto.salvar_evento(inicio, fim)
    contexto.salvar_elegibilidade(evento.id, None)

    [item] = contexto.servico.listar(SEGURADO_ID)

    assert item.classificacao is ClassificacaoAlerta.ATIVO


def test_listar_nao_devolve_alertas_de_outro_segurado(tmp_path: Path) -> None:
    contexto = Contexto(tmp_path)
    inicio, fim = _periodo_futuro()
    evento = contexto.salvar_evento(inicio, fim)
    execucao_id = contexto.execucoes.criar(EstadoExecucao.CONCLUIDA)
    contexto.salvar_elegibilidade(evento.id, execucao_id, segurado_id=OUTRO_SEGURADO_ID)

    assert contexto.servico.listar(SEGURADO_ID) == []


def test_obter_detalhe_de_elegibilidade_inexistente_devolve_none(tmp_path: Path) -> None:
    contexto = Contexto(tmp_path)

    assert contexto.servico.obter_detalhe(SEGURADO_ID, uuid4()) is None


def test_obter_detalhe_de_outro_segurado_devolve_none(tmp_path: Path) -> None:
    contexto = Contexto(tmp_path)
    inicio, fim = _periodo_futuro()
    evento = contexto.salvar_evento(inicio, fim)
    execucao_id = contexto.execucoes.criar(EstadoExecucao.CONCLUIDA)
    id_registro = contexto.salvar_elegibilidade(
        evento.id, execucao_id, segurado_id=OUTRO_SEGURADO_ID
    )

    assert contexto.servico.obter_detalhe(SEGURADO_ID, id_registro) is None


def test_obter_detalhe_de_alerta_valido_traz_apolice_justificativa_e_linha_do_tempo(
    tmp_path: Path,
) -> None:
    contexto = Contexto(tmp_path)
    inicio, fim = _periodo_futuro()
    evento = contexto.salvar_evento(inicio, fim)
    execucao_id = contexto.execucoes.criar(EstadoExecucao.CONCLUIDA)
    id_registro = contexto.salvar_elegibilidade(evento.id, execucao_id)

    detalhe = contexto.servico.obter_detalhe(SEGURADO_ID, id_registro)

    assert detalhe is not None
    assert detalhe.apolice_id == APOLICE_ID
    assert detalhe.justificativa == "Segurado e apólice atendem à regra ativa."
    assert detalhe.classificacao is ClassificacaoAlerta.ATIVO
    assert detalhe.alerta.evento_tipo is TipoEventoMeteorologico.CHUVA_INTENSA
    assert len(detalhe.linha_do_tempo) > 0


def test_obter_detalhe_de_linha_semeada_sem_execucao_traz_linha_do_tempo_vazia(
    tmp_path: Path,
) -> None:
    contexto = Contexto(tmp_path)
    inicio, fim = _periodo_futuro()
    evento = contexto.salvar_evento(inicio, fim)
    id_registro = contexto.salvar_elegibilidade(evento.id, None)

    detalhe = contexto.servico.obter_detalhe(SEGURADO_ID, id_registro)

    assert detalhe is not None
    assert detalhe.linha_do_tempo == ()


def test_listar_expoe_entrega_simulada_id_por_item(tmp_path: Path) -> None:
    """6.8 (ABRIREXP-01): cada item da lista carrega o `entrega_simulada_id` da sua
    própria elegibilidade — `None` para a que ainda não tem entrega."""

    contexto = Contexto(tmp_path)
    inicio, fim = _periodo_futuro()
    evento = contexto.salvar_evento(inicio, fim)
    execucao_com_entrega = contexto.execucoes.criar(EstadoExecucao.CONCLUIDA)
    id_com_entrega = contexto.salvar_elegibilidade(evento.id, execucao_com_entrega)
    entrega_id = contexto.marcar_entrega_simulada(id_com_entrega)
    id_sem_entrega = contexto.salvar_elegibilidade(evento.id, None)

    itens = {item.alerta.elegibilidade_id: item for item in contexto.servico.listar(SEGURADO_ID)}

    assert itens[id_com_entrega].alerta.entrega_simulada_id == entrega_id
    assert itens[id_sem_entrega].alerta.entrega_simulada_id is None


def test_obter_detalhe_expoe_entrega_simulada_id_do_alerta_selecionado(tmp_path: Path) -> None:
    """6.8 (ABRIREXP-02): o detalhe do alerta selecionado carrega o `entrega_simulada_id`
    daquele alerta, nunca o de outro."""

    contexto = Contexto(tmp_path)
    inicio, fim = _periodo_futuro()
    evento = contexto.salvar_evento(inicio, fim)
    execucao_id = contexto.execucoes.criar(EstadoExecucao.CONCLUIDA)
    id_registro = contexto.salvar_elegibilidade(evento.id, execucao_id)
    entrega_id = contexto.marcar_entrega_simulada(id_registro)
    outra_execucao_id = contexto.execucoes.criar(EstadoExecucao.CONCLUIDA)
    outro_registro = contexto.salvar_elegibilidade(evento.id, outra_execucao_id)

    detalhe = contexto.servico.obter_detalhe(SEGURADO_ID, id_registro)
    outro_detalhe = contexto.servico.obter_detalhe(SEGURADO_ID, outro_registro)

    assert detalhe is not None
    assert detalhe.alerta.entrega_simulada_id == entrega_id
    assert outro_detalhe is not None
    assert outro_detalhe.alerta.entrega_simulada_id is None
