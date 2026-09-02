"""Testes do `ServicoAvaliacaoElegibilidade`: orquestração de candidatos e persistência."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from central_preventiva.aplicacao.avaliacao_elegibilidade import (
    PortasAvaliacaoElegibilidade,
    ServicoAvaliacaoElegibilidade,
)
from central_preventiva.dominio.avaliador_elegibilidade import (
    CandidatoElegibilidade,
    ResultadoElegibilidade,
)
from central_preventiva.dominio.avaliador_risco import RegraSnapshot
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
    cobertura_exigida="alagamento",
    versao=1,
)

EVENTO_CHUVA = EventoMeteorologico(
    id=uuid4(),
    tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
    area=AREA,
    periodo_inicio=datetime(2026, 3, 10, 6, 0),
    periodo_fim=datetime(2026, 3, 10, 18, 0),
    intensidade=72.5,
    proveniencia=ProvenienciaEvento.SINTETICO,
    instante_observado=datetime(2026, 3, 9, 18, 0),
)


def candidato_elegivel() -> CandidatoElegibilidade:
    return CandidatoElegibilidade(
        segurado_id=uuid4(),
        apolice_id=uuid4(),
        nome_segurado="Pessoa Segurada Sintética",
        codigo_ibge_area=AREA,
        canal_preferido="whatsapp",
        participa_de_alertas=True,
        apolice_tipo="residencial",
        apolice_situacao="ativa",
        coberturas=("alagamento",),
    )


def candidato_excluido() -> CandidatoElegibilidade:
    return CandidatoElegibilidade(
        segurado_id=uuid4(),
        apolice_id=uuid4(),
        nome_segurado="Pessoa Segurada Sintética 2",
        codigo_ibge_area=AREA,
        canal_preferido="email",
        participa_de_alertas=True,
        apolice_tipo="residencial",
        apolice_situacao="cancelada",
        coberturas=("alagamento",),
    )


@dataclass(frozen=True, slots=True)
class ContagemFalsa:
    incluidos: int
    excluidos: int


class RepositorioCandidatosFalso:
    def __init__(self, candidatos: list[CandidatoElegibilidade]) -> None:
        self._candidatos = candidatos

    def listar_candidatos(self, area: str) -> list[CandidatoElegibilidade]:
        return [c for c in self._candidatos if c.codigo_ibge_area == area]


class RepositorioElegibilidadesFalso:
    def __init__(self) -> None:
        self.chamadas: list[
            tuple[UUID, UUID, UUID, UUID, UUID, str, ResultadoElegibilidade]
        ] = []
        self._por_execucao: dict[UUID, list[ResultadoElegibilidade]] = {}

    def salvar(
        self,
        execucao_id: UUID,
        evento_id: UUID,
        regra_id: UUID,
        segurado_id: UUID,
        apolice_id: UUID,
        nome_segurado: str,
        resultado: ResultadoElegibilidade,
    ) -> UUID | None:
        self.chamadas.append(
            (execucao_id, evento_id, regra_id, segurado_id, apolice_id, nome_segurado, resultado)
        )
        self._por_execucao.setdefault(execucao_id, []).append(resultado)
        return uuid4()

    def contar_por_execucao(self, execucao_id: UUID) -> ContagemFalsa:
        resultados = self._por_execucao.get(execucao_id, [])
        incluidos = sum(1 for r in resultados if r.elegivel)
        excluidos = sum(1 for r in resultados if not r.elegivel)
        return ContagemFalsa(incluidos=incluidos, excluidos=excluidos)


def montar_servico(
    candidatos: list[CandidatoElegibilidade],
) -> tuple[ServicoAvaliacaoElegibilidade, RepositorioElegibilidadesFalso]:
    elegibilidades = RepositorioElegibilidadesFalso()
    portas = PortasAvaliacaoElegibilidade(
        candidatos=RepositorioCandidatosFalso(candidatos),  # type: ignore[arg-type]
        elegibilidades=elegibilidades,  # type: ignore[arg-type]
    )
    return ServicoAvaliacaoElegibilidade(portas), elegibilidades


def test_evento_sem_nenhum_candidato_devolve_conjunto_vazio_valido() -> None:
    servico, elegibilidades = montar_servico([])
    execucao_id = uuid4()

    contagem = servico.avaliar_publico(execucao_id, EVENTO_CHUVA, REGRA_CHUVA)

    assert contagem.incluidos == 0
    assert contagem.excluidos == 0
    assert elegibilidades.chamadas == []


def test_avalia_cada_candidato_e_persiste_um_resultado_por_combinacao() -> None:
    incluido = candidato_elegivel()
    excluido = candidato_excluido()
    servico, elegibilidades = montar_servico([incluido, excluido])
    execucao_id = uuid4()

    contagem = servico.avaliar_publico(execucao_id, EVENTO_CHUVA, REGRA_CHUVA)

    assert contagem.incluidos == 1
    assert contagem.excluidos == 1
    assert len(elegibilidades.chamadas) == 2
    segurados_chamados = {chamada[3] for chamada in elegibilidades.chamadas}
    assert segurados_chamados == {incluido.segurado_id, excluido.segurado_id}


def test_snapshot_salvo_carrega_execucao_evento_regra_e_ids_corretos() -> None:
    candidato = candidato_elegivel()
    servico, elegibilidades = montar_servico([candidato])
    execucao_id = uuid4()

    servico.avaliar_publico(execucao_id, EVENTO_CHUVA, REGRA_CHUVA)

    (
        execucao_salva,
        evento_salvo,
        regra_salva,
        segurado_salvo,
        apolice_salva,
        nome_salvo,
        resultado,
    ) = elegibilidades.chamadas[0]
    assert execucao_salva == execucao_id
    assert evento_salvo == EVENTO_CHUVA.id
    assert regra_salva == REGRA_CHUVA.id
    assert segurado_salvo == candidato.segurado_id
    assert apolice_salva == candidato.apolice_id
    assert nome_salvo == candidato.nome_segurado
    assert resultado.elegivel is True


def test_reprocessar_a_mesma_execucao_nao_duplica_chamadas_por_combinacao() -> None:
    candidato = candidato_elegivel()
    servico, elegibilidades = montar_servico([candidato])
    execucao_id = uuid4()

    servico.avaliar_publico(execucao_id, EVENTO_CHUVA, REGRA_CHUVA)
    servico.avaliar_publico(execucao_id, EVENTO_CHUVA, REGRA_CHUVA)

    assert len(elegibilidades.chamadas) == 2
    combinacoes = {(c[3], c[4]) for c in elegibilidades.chamadas}
    assert len(combinacoes) == 1
