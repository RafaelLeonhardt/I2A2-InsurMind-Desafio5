"""Testes do `ServicoGestaoRegras`: validar, testar e ativar versões (REGRA-07..13)."""

from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID, uuid4

import pytest

from central_preventiva.aplicacao.gestao_regras import (
    ConfiguracaoInvalida,
    NenhumCenarioAplicavel,
    PortasGestaoRegras,
    ServicoGestaoRegras,
)
from central_preventiva.aplicacao.portas_persistencia import (
    ConflitoIdempotencia,
    RespostaRegistrada,
)
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)
from central_preventiva.dominio.validador_regra import DadosRegra

AREA = "9990001"

DADOS_CHUVA_VALIDOS = DadosRegra(
    evento_tipo="chuva_intensa",
    limiar_meteorologico=50.0,
    area_aplicavel=AREA,
    apolice_tipo="residencial",
    cobertura_exigida="alagamento",
    antecedencia_horas=24,
    canal="whatsapp",
)


def evento_sintetico_chuva(intensidade: float = 72.5) -> EventoMeteorologico:
    return EventoMeteorologico(
        id=uuid4(),
        tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
        area=AREA,
        periodo_inicio=datetime(2026, 3, 10, 6, 0),
        periodo_fim=datetime(2026, 3, 10, 18, 0),
        intensidade=intensidade,
        proveniencia=ProvenienciaEvento.SINTETICO,
        instante_observado=datetime(2026, 3, 9, 18, 0),
    )


@dataclass(frozen=True, slots=True)
class RegraFalsa:
    id: UUID
    versao: int
    estado: str
    evento_tipo: object
    limiar_meteorologico: float
    area_aplicavel: str
    apolice_tipo: str
    cobertura_exigida: str
    antecedencia_horas: int
    canal: str


class RepositorioRegrasFalso:
    def __init__(self) -> None:
        self.chamadas: list[tuple[UUID, int, DadosRegra]] = []

    def criar_nova_versao(
        self, regra_anterior_id: UUID, versao_esperada: int, dados: DadosRegra
    ) -> RegraFalsa:
        self.chamadas.append((regra_anterior_id, versao_esperada, dados))
        return RegraFalsa(
            id=uuid4(),
            versao=versao_esperada + 1,
            estado="ativa",
            evento_tipo=dados.evento_tipo,
            limiar_meteorologico=dados.limiar_meteorologico,
            area_aplicavel=dados.area_aplicavel,
            apolice_tipo=dados.apolice_tipo,
            cobertura_exigida=dados.cobertura_exigida,
            antecedencia_horas=dados.antecedencia_horas,
            canal=dados.canal,
        )


class RepositorioEventosFalso:
    def __init__(self, eventos: tuple[EventoMeteorologico, ...]) -> None:
        self._eventos = eventos

    def listar_sinteticos_por_tipo(
        self, tipo: TipoEventoMeteorologico
    ) -> tuple[EventoMeteorologico, ...]:
        return tuple(evento for evento in self._eventos if evento.tipo == tipo)


class RepositorioIdempotenciaFalso:
    def __init__(self) -> None:
        self._respostas: dict[tuple[str, str], RespostaRegistrada] = {}

    def buscar(self, chave: str, operacao: str) -> RespostaRegistrada | None:
        return self._respostas.get((chave, operacao))

    def registrar(
        self, chave: str, operacao: str, hash_requisicao: str, status: int, corpo: str
    ) -> None:
        self._respostas[(chave, operacao)] = RespostaRegistrada(
            hash_requisicao=hash_requisicao, status=status, corpo=corpo
        )


def montar_servico(
    eventos: tuple[EventoMeteorologico, ...] = (),
) -> tuple[ServicoGestaoRegras, RepositorioRegrasFalso, RepositorioIdempotenciaFalso]:
    regras = RepositorioRegrasFalso()
    idempotencia = RepositorioIdempotenciaFalso()
    portas = PortasGestaoRegras(
        regras=regras,  # type: ignore[arg-type]
        eventos=RepositorioEventosFalso(eventos),  # type: ignore[arg-type]
        idempotencia=idempotencia,  # type: ignore[arg-type]
    )
    return ServicoGestaoRegras(portas), regras, idempotencia


def test_testar_configuracao_invalida_bloqueia_sem_chamar_avaliador() -> None:
    servico, _, _ = montar_servico((evento_sintetico_chuva(),))
    dados_invalidos = replace(DADOS_CHUVA_VALIDOS, limiar_meteorologico=-1.0)

    with pytest.raises(ConfiguracaoInvalida) as excecao:
        servico.testar(uuid4(), dados_invalidos)

    assert any(erro.campo == "limiar_meteorologico" for erro in excecao.value.erros)


def test_testar_configuracao_valida_aplica_avaliador_a_cada_cenario_sintetico() -> None:
    servico, _, _ = montar_servico((evento_sintetico_chuva(72.5),))

    resultados = servico.testar(uuid4(), DADOS_CHUVA_VALIDOS)

    assert len(resultados) == 1
    assert resultados[0].resultado.relevante is True


def test_testar_sem_cenario_aplicavel_devolve_tupla_vazia_sem_erro() -> None:
    servico, _, _ = montar_servico(())

    resultados = servico.testar(uuid4(), DADOS_CHUVA_VALIDOS)

    assert resultados == ()


def test_testar_filtra_cenarios_por_tipo_de_evento_da_regra() -> None:
    evento_granizo = EventoMeteorologico(
        id=uuid4(),
        tipo=TipoEventoMeteorologico.GRANIZO,
        area="9990002",
        periodo_inicio=datetime(2026, 3, 12, 14, 0),
        periodo_fim=datetime(2026, 3, 12, 20, 0),
        intensidade=31.0,
        proveniencia=ProvenienciaEvento.SINTETICO,
        instante_observado=datetime(2026, 3, 12, 8, 0),
    )
    servico, _, _ = montar_servico((evento_granizo,))

    resultados = servico.testar(uuid4(), DADOS_CHUVA_VALIDOS)

    assert resultados == ()


def test_ativar_configuracao_invalida_bloqueia_sem_criar_versao() -> None:
    servico, regras, _ = montar_servico((evento_sintetico_chuva(),))
    dados_invalidos = replace(DADOS_CHUVA_VALIDOS, canal="pombo-correio")

    with pytest.raises(ConfiguracaoInvalida):
        servico.ativar(uuid4(), 1, dados_invalidos, "chave-1", "hash-1")

    assert regras.chamadas == []


def test_ativar_sem_cenario_aplicavel_bloqueia_sem_criar_versao() -> None:
    servico, regras, _ = montar_servico(())

    with pytest.raises(NenhumCenarioAplicavel):
        servico.ativar(uuid4(), 1, DADOS_CHUVA_VALIDOS, "chave-1", "hash-1")

    assert regras.chamadas == []


def test_ativar_configuracao_valida_e_testada_cria_nova_versao() -> None:
    servico, regras, _ = montar_servico((evento_sintetico_chuva(),))
    regra_anterior_id = uuid4()

    ativada = servico.ativar(regra_anterior_id, 1, DADOS_CHUVA_VALIDOS, "chave-1", "hash-1")

    assert ativada.versao == 2
    assert ativada.estado == "ativa"
    assert len(regras.chamadas) == 1
    assert regras.chamadas[0] == (regra_anterior_id, 1, DADOS_CHUVA_VALIDOS)


def test_ativar_repetido_com_mesma_chave_e_hash_devolve_resposta_registrada_sem_criar_outra() -> (
    None
):
    servico, regras, _ = montar_servico((evento_sintetico_chuva(),))
    regra_anterior_id = uuid4()

    primeira = servico.ativar(regra_anterior_id, 1, DADOS_CHUVA_VALIDOS, "chave-1", "hash-1")
    segunda = servico.ativar(regra_anterior_id, 1, DADOS_CHUVA_VALIDOS, "chave-1", "hash-1")

    assert segunda == primeira
    assert len(regras.chamadas) == 1


def test_ativar_mesma_chave_com_hash_diferente_levanta_conflito_idempotencia() -> None:
    servico, regras, _ = montar_servico((evento_sintetico_chuva(),))
    regra_anterior_id = uuid4()

    servico.ativar(regra_anterior_id, 1, DADOS_CHUVA_VALIDOS, "chave-1", "hash-1")

    with pytest.raises(ConflitoIdempotencia):
        servico.ativar(regra_anterior_id, 1, DADOS_CHUVA_VALIDOS, "chave-1", "hash-2")

    assert len(regras.chamadas) == 1
