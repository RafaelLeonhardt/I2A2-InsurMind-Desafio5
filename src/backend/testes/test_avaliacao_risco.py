"""Testes do `ServicoAvaliacaoRisco`: orquestração de avaliação e transição (RISCO-09, RISCO-10)."""

from datetime import datetime
from uuid import UUID, uuid4

from central_preventiva.aplicacao.avaliacao_risco import (
    PortasAvaliacaoRisco,
    ServicoAvaliacaoRisco,
)
from central_preventiva.dominio.avaliador_risco import (
    MOTIVO_SEM_REGRA_ATIVA,
    RegraSnapshot,
    ResultadoAvaliacaoRisco,
)
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)

AREA = "9990001"

REGRA_CHUVA = RegraSnapshot(
    id=uuid4(),
    evento_tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
    limiar_meteorologico=50.0,
    area_aplicavel=AREA,
    apolice_tipo="residencial",
    versao=7,  # não-trivial de propósito: discrimina "propaga a versão" de "grava um literal"
)


def evento_chuva(intensidade: float) -> EventoMeteorologico:
    return EventoMeteorologico(
        id=uuid4(),
        tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
        area=AREA,
        periodo_inicio=datetime(2026, 8, 30, 17, 0),
        periodo_fim=datetime(2026, 8, 30, 18, 0),
        intensidade=intensidade,
        proveniencia=ProvenienciaEvento.REAL_INMET,
        instante_observado=datetime(2026, 8, 30, 18, 0),
    )


class RegrasFalsas:
    def __init__(self, regra: RegraSnapshot | None) -> None:
        self._regra = regra

    def obter_ativa(self, evento_tipo: TipoEventoMeteorologico) -> RegraSnapshot | None:
        return self._regra


class AvaliacoesFalsas:
    def __init__(self) -> None:
        self.salvas: list[
            tuple[UUID, UUID, UUID | None, int | None, ResultadoAvaliacaoRisco]
        ] = []

    def salvar(
        self,
        execucao_id: UUID,
        evento_id: UUID,
        regra_id: UUID | None,
        regra_versao: int | None,
        resultado: ResultadoAvaliacaoRisco,
    ) -> UUID:
        id_avaliacao = uuid4()
        self.salvas.append((execucao_id, evento_id, regra_id, regra_versao, resultado))
        return id_avaliacao


class ExecucoesFalsas:
    def __init__(self) -> None:
        self.transicoes: list[tuple[UUID, int, EstadoExecucao]] = []

    def transicionar(
        self, execucao_id: UUID, versao_esperada: int, novo_estado: EstadoExecucao
    ) -> None:
        self.transicoes.append((execucao_id, versao_esperada, novo_estado))


def montar_servico(
    regra: RegraSnapshot | None,
) -> tuple[ServicoAvaliacaoRisco, AvaliacoesFalsas, ExecucoesFalsas]:
    avaliacoes = AvaliacoesFalsas()
    execucoes = ExecucoesFalsas()
    portas = PortasAvaliacaoRisco(
        regras=RegrasFalsas(regra),  # type: ignore[arg-type]
        avaliacoes=avaliacoes,  # type: ignore[arg-type]
        execucoes=execucoes,  # type: ignore[arg-type]
    )
    return ServicoAvaliacaoRisco(portas), avaliacoes, execucoes


def test_evento_nao_relevante_transiciona_para_sem_risco_com_snapshot_salvo() -> None:
    servico, avaliacoes, execucoes = montar_servico(REGRA_CHUVA)
    execucao_id = uuid4()

    resultado = servico.avaliar_evento(execucao_id, 1, evento_chuva(10.0))

    assert resultado.relevante is False
    assert len(avaliacoes.salvas) == 1
    assert execucoes.transicoes == [(execucao_id, 1, EstadoExecucao.SEM_RISCO)]


def test_evento_relevante_transiciona_para_avaliando_elegibilidade_com_snapshot_salvo() -> None:
    servico, avaliacoes, execucoes = montar_servico(REGRA_CHUVA)
    execucao_id = uuid4()

    resultado = servico.avaliar_evento(execucao_id, 1, evento_chuva(72.5))

    assert resultado.relevante is True
    assert len(avaliacoes.salvas) == 1
    assert execucoes.transicoes == [(execucao_id, 1, EstadoExecucao.AVALIANDO_ELEGIBILIDADE)]


def test_ausencia_de_regra_ativa_persiste_snapshot_com_regra_nula_e_transiciona_sem_risco() -> (
    None
):
    """RISCO-09: a decisão terminal sem regra ativa fica persistida e explicável, não
    apenas em memória — `regra_id`/`regra_versao` ficam nulos (migração 0005)."""

    servico, avaliacoes, execucoes = montar_servico(None)
    execucao_id = uuid4()
    evento = evento_chuva(72.5)

    resultado = servico.avaliar_evento(execucao_id, 1, evento)

    assert resultado.relevante is False
    assert resultado.motivo == MOTIVO_SEM_REGRA_ATIVA
    assert len(avaliacoes.salvas) == 1
    execucao_salva, evento_salvo, regra_salva, versao_salva, resultado_salvo = avaliacoes.salvas[0]
    assert execucao_salva == execucao_id
    assert evento_salvo == evento.id
    assert regra_salva is None
    assert versao_salva is None
    assert resultado_salvo.motivo == MOTIVO_SEM_REGRA_ATIVA
    assert execucoes.transicoes == [(execucao_id, 1, EstadoExecucao.SEM_RISCO)]


def test_snapshot_salvo_carrega_execucao_evento_regra_e_versao_corretos() -> None:
    servico, avaliacoes, _ = montar_servico(REGRA_CHUVA)
    execucao_id = uuid4()
    evento = evento_chuva(72.5)

    servico.avaliar_evento(execucao_id, 1, evento)

    execucao_salva, evento_salvo, regra_salva, versao_salva, resultado_salvo = avaliacoes.salvas[0]
    assert execucao_salva == execucao_id
    assert evento_salvo == evento.id
    assert regra_salva == REGRA_CHUVA.id
    assert versao_salva == REGRA_CHUVA.versao
    assert resultado_salvo.relevante is True
