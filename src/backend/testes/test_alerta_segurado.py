"""Testes do caso de uso do alerta mais relevante do segurado ativo (VISAO-01..06, 5.1).

Os repositórios são os reais, sobre um banco temporário migrado: o alerta é uma junção de
leitura pura sobre schema já garantido por 2.1/2.2/2.3/2.5, sem nenhuma escrita própria a
testar com dublê — mesma escolha de `test_detalhe_resultado.py`.
"""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RepositorioElegibilidades,
)
from central_preventiva.adaptadores.persistencia.repositorio_meteorologia import (
    RepositorioAreasMonitoradas,
    RepositorioEventosMeteorologicos,
    RepositorioSincronizacoes,
    RepositorioTentativasColeta,
)
from central_preventiva.adaptadores.persistencia.repositorio_regras import RepositorioRegras
from central_preventiva.adaptadores.persistencia.semeador import SemeadorDadosSinteticos
from central_preventiva.aplicacao.alerta_segurado import PortasAlertaSegurado, ServicoAlertaSegurado
from central_preventiva.aplicacao.portas_meteorologia import (
    CodigoResultadoTentativa,
    EstadoSincronizacao,
    OrigemSincronizacao,
)
from central_preventiva.dominio.avaliador_elegibilidade import ResultadoElegibilidade
from central_preventiva.dominio.avaliador_risco import Criterio
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)
from central_preventiva.dominio.identificadores_demonstracao import SEGURADO_PADRAO
from central_preventiva.dominio.montador_contexto_agente import ORIENTACOES_POR_EVENTO

AREA = "9990001"
REGRA_ID = uuid4()
SEGURADO_ID = uuid4()
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
        self.areas = RepositorioAreasMonitoradas(self.caminho)
        self.sincronizacoes = RepositorioSincronizacoes(self.caminho)
        self.tentativas = RepositorioTentativasColeta(self.caminho)
        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(
                "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
                "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
                "VALUES (?, 'chuva_intensa', 50.0, ?, 'residencial', 'alagamento', 24, "
                "'whatsapp', 1, 'ativa')",
                [REGRA_ID, AREA],
            )
        self.servico = ServicoAlertaSegurado(
            PortasAlertaSegurado(
                elegibilidades=self.elegibilidades,
                eventos=self.eventos,
                regras=self.regras,
                areas_monitoradas=self.areas,
                sincronizacoes=self.sincronizacoes,
                tentativas=self.tentativas,
            )
        )

    def salvar_evento(self, evento: EventoMeteorologico) -> None:
        """Persiste o evento meteorológico do cenário."""

        self.eventos.salvar(evento)

    def salvar_elegibilidade(self, evento_id: UUID) -> None:
        """Persiste a elegibilidade `incluido` do segurado para o evento informado."""

        self.elegibilidades.salvar(
            uuid4(), evento_id, REGRA_ID, SEGURADO_ID, APOLICE_ID, "Pessoa Teste",
            RESULTADO_INCLUIDO,
        )


def _evento_real(intensidade: float = 62.5) -> EventoMeteorologico:
    return EventoMeteorologico(
        id=uuid4(),
        tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
        area=AREA,
        periodo_inicio=datetime(2026, 9, 4, 12, 0),
        periodo_fim=datetime(2026, 9, 4, 18, 0),
        intensidade=intensidade,
        proveniencia=ProvenienciaEvento.REAL_INMET,
        instante_observado=datetime(2026, 9, 4, 18, 0),
    )


def _evento_sintetico() -> EventoMeteorologico:
    return EventoMeteorologico(
        id=uuid4(),
        tipo=TipoEventoMeteorologico.GRANIZO,
        area=AREA,
        periodo_inicio=datetime(2026, 9, 4, 12, 0),
        periodo_fim=datetime(2026, 9, 4, 18, 0),
        intensidade=1.0,
        proveniencia=ProvenienciaEvento.SINTETICO,
        instante_observado=datetime(2026, 9, 4, 18, 0),
    )


def test_sem_elegibilidade_devolve_none(tmp_path: Path) -> None:
    contexto = Contexto(tmp_path)

    assert contexto.servico.obter_mais_relevante(SEGURADO_ID) is None


def test_alerta_real_traz_todos_os_campos_do_ac_e_nunca_rotula_como_sintetico(
    tmp_path: Path,
) -> None:
    contexto = Contexto(tmp_path)
    evento = _evento_real()
    contexto.salvar_evento(evento)
    contexto.salvar_elegibilidade(evento.id)

    alerta = contexto.servico.obter_mais_relevante(SEGURADO_ID)

    assert alerta is not None
    assert alerta.evento_tipo is TipoEventoMeteorologico.CHUVA_INTENSA
    assert alerta.periodo_inicio == evento.periodo_inicio
    assert alerta.periodo_fim == evento.periodo_fim
    assert alerta.localizacao == AREA
    assert alerta.impactos_esperados == ("alagamento",)
    assert alerta.recomendacoes == ORIENTACOES_POR_EVENTO[TipoEventoMeteorologico.CHUVA_INTENSA]
    assert "62.5" in alerta.severidade
    assert alerta.origem is ProvenienciaEvento.REAL_INMET
    assert alerta.instante_observado == evento.instante_observado
    assert alerta.fonte_degradada is False


def test_alerta_sintetico_tem_origem_rotulada_como_tal(tmp_path: Path) -> None:
    contexto = Contexto(tmp_path)
    evento = _evento_sintetico()
    contexto.salvar_evento(evento)
    contexto.salvar_elegibilidade(evento.id)

    alerta = contexto.servico.obter_mais_relevante(SEGURADO_ID)

    assert alerta is not None
    assert alerta.origem is ProvenienciaEvento.SINTETICO
    assert alerta.fonte_degradada is False


def test_fonte_degradada_quando_ultima_sincronizacao_da_area_falhou(tmp_path: Path) -> None:
    contexto = Contexto(tmp_path)
    evento = _evento_real()
    contexto.salvar_evento(evento)
    contexto.salvar_elegibilidade(evento.id)

    id_area = uuid4()
    with abrir_conexao(contexto.caminho) as conexao:
        conexao.execute(
            "INSERT INTO areas_monitoradas_inmet "
            "(id, codigo_estacao_inmet, nome_estacao, codigo_ibge_area, ativa) "
            "VALUES (?, 'A701', 'Estação de Teste', ?, true)",
            [id_area, AREA],
        )
    sincronizacao = contexto.sincronizacoes.criar(
        uuid4(), id_area, OrigemSincronizacao.AUTOMATICA, EstadoSincronizacao.COLETANDO
    )
    contexto.sincronizacoes.atualizar_estado(sincronizacao.id, EstadoSincronizacao.FALHA)

    alerta = contexto.servico.obter_mais_relevante(SEGURADO_ID)

    assert alerta is not None
    assert alerta.fonte_degradada is True


def test_fonte_degradada_quando_ultima_sincronizacao_precisou_de_mais_de_uma_tentativa(
    tmp_path: Path,
) -> None:
    contexto = Contexto(tmp_path)
    evento = _evento_real()
    contexto.salvar_evento(evento)
    contexto.salvar_elegibilidade(evento.id)

    id_area = uuid4()
    with abrir_conexao(contexto.caminho) as conexao:
        conexao.execute(
            "INSERT INTO areas_monitoradas_inmet "
            "(id, codigo_estacao_inmet, nome_estacao, codigo_ibge_area, ativa) "
            "VALUES (?, 'A701', 'Estação de Teste', ?, true)",
            [id_area, AREA],
        )
    sincronizacao = contexto.sincronizacoes.criar(
        uuid4(), id_area, OrigemSincronizacao.AUTOMATICA, EstadoSincronizacao.COLETANDO
    )
    agora = datetime.now(UTC)
    contexto.tentativas.registrar_tentativa(
        sincronizacao.id, 1, CodigoResultadoTentativa.TIMEOUT, agora, agora
    )
    contexto.tentativas.registrar_tentativa(
        sincronizacao.id, 2, CodigoResultadoTentativa.SUCESSO, agora, agora
    )
    contexto.sincronizacoes.atualizar_estado(sincronizacao.id, EstadoSincronizacao.CONCLUIDO, 1)

    alerta = contexto.servico.obter_mais_relevante(SEGURADO_ID)

    assert alerta is not None
    assert alerta.fonte_degradada is True


def test_fonte_operacional_quando_ultima_sincronizacao_concluiu_de_primeira(
    tmp_path: Path,
) -> None:
    contexto = Contexto(tmp_path)
    evento = _evento_real()
    contexto.salvar_evento(evento)
    contexto.salvar_elegibilidade(evento.id)

    id_area = uuid4()
    with abrir_conexao(contexto.caminho) as conexao:
        conexao.execute(
            "INSERT INTO areas_monitoradas_inmet "
            "(id, codigo_estacao_inmet, nome_estacao, codigo_ibge_area, ativa) "
            "VALUES (?, 'A701', 'Estação de Teste', ?, true)",
            [id_area, AREA],
        )
    sincronizacao = contexto.sincronizacoes.criar(
        uuid4(), id_area, OrigemSincronizacao.AUTOMATICA, EstadoSincronizacao.COLETANDO
    )
    agora = datetime.now(UTC)
    contexto.tentativas.registrar_tentativa(
        sincronizacao.id, 1, CodigoResultadoTentativa.SUCESSO, agora, agora
    )
    contexto.sincronizacoes.atualizar_estado(sincronizacao.id, EstadoSincronizacao.CONCLUIDO, 1)

    alerta = contexto.servico.obter_mais_relevante(SEGURADO_ID)

    assert alerta is not None
    assert alerta.fonte_degradada is False


def test_fonte_nunca_degradada_sem_nenhuma_sincronizacao_registrada(tmp_path: Path) -> None:
    contexto = Contexto(tmp_path)
    evento = _evento_real()
    contexto.salvar_evento(evento)
    contexto.salvar_elegibilidade(evento.id)

    alerta = contexto.servico.obter_mais_relevante(SEGURADO_ID)

    assert alerta is not None
    assert alerta.fonte_degradada is False


def test_snapshot_degradado_sem_elegibilidade_do_segurado_e_tratado_como_sem_alerta(
    tmp_path: Path,
) -> None:
    """Edge case da spec: sincronização em falha sem nenhuma elegibilidade do segurado
    nunca vira "alerta degradado" — nenhum alerta de fato existe para ele."""

    contexto = Contexto(tmp_path)
    id_area = uuid4()
    with abrir_conexao(contexto.caminho) as conexao:
        conexao.execute(
            "INSERT INTO areas_monitoradas_inmet "
            "(id, codigo_estacao_inmet, nome_estacao, codigo_ibge_area, ativa) "
            "VALUES (?, 'A701', 'Estação de Teste', ?, true)",
            [id_area, AREA],
        )
    sincronizacao = contexto.sincronizacoes.criar(
        uuid4(), id_area, OrigemSincronizacao.AUTOMATICA, EstadoSincronizacao.COLETANDO
    )
    contexto.sincronizacoes.atualizar_estado(sincronizacao.id, EstadoSincronizacao.FALHA)

    assert contexto.servico.obter_mais_relevante(SEGURADO_ID) is None


def test_segurado_padrao_semeado_recebe_alerta_completo_sem_avaliacoes_risco_ou_contexto(
    tmp_path: Path,
) -> None:
    """Ancora a SPEC_DEVIATION do módulo: a persona semeada da demonstração (execucao_id
    NULO, sem avaliacoes_risco/contextos_agente) recebe um alerta completo recomputando
    risco e reusando ORIENTACOES_POR_EVENTO — não `None` nem campos vazios."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    SemeadorDadosSinteticos(caminho).semear()
    servico = ServicoAlertaSegurado(
        PortasAlertaSegurado(
            elegibilidades=RepositorioElegibilidades(caminho),
            eventos=RepositorioEventosMeteorologicos(caminho),
            regras=RepositorioRegras(caminho),
            areas_monitoradas=RepositorioAreasMonitoradas(caminho),
            sincronizacoes=RepositorioSincronizacoes(caminho),
            tentativas=RepositorioTentativasColeta(caminho),
        )
    )

    alerta = servico.obter_mais_relevante(SEGURADO_PADRAO)

    assert alerta is not None
    assert alerta.evento_tipo is TipoEventoMeteorologico.CHUVA_INTENSA
    assert alerta.severidade != ""
    assert alerta.periodo_inicio is not None
    assert alerta.localizacao != ""
    assert alerta.impactos_esperados == ("alagamento",)
    assert alerta.recomendacoes == ORIENTACOES_POR_EVENTO[TipoEventoMeteorologico.CHUVA_INTENSA]
    assert alerta.origem is ProvenienciaEvento.SINTETICO
    assert alerta.fonte_degradada is False
