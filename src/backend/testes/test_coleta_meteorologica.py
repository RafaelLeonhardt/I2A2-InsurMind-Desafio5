"""Testes do caso de uso `ServicoColetaMeteorologica` (INMET-03..06,11,12,16)."""

import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import pytest

from central_preventiva.adaptadores.meteorologia.cliente_inmet import AdaptadorInmetFalso
from central_preventiva.adaptadores.meteorologia.normalizador_inmet import NormalizadorInmet
from central_preventiva.aplicacao.coleta_meteorologica import (
    AreaMonitoradaInexistente,
    PortasColetaMeteorologica,
    ServicoColetaMeteorologica,
)
from central_preventiva.aplicacao.portas_meteorologia import (
    AreaMonitorada,
    EstadoSincronizacao,
    OrigemSincronizacao,
    RespostaColetaInmet,
    Sincronizacao,
)
from central_preventiva.aplicacao.portas_persistencia import (
    ConflitoIdempotencia,
    RespostaRegistrada,
)
from central_preventiva.dominio.evento_meteorologico import (
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)

AREA = AreaMonitorada(
    id=UUID("11111111-1111-1111-1111-111111111111"),
    codigo_estacao_inmet="A701",
    nome_estacao="Estação de Teste",
    codigo_ibge_area="9990001",
    ativa=True,
)

RESPOSTA_VALIDA = RespostaColetaInmet(
    status_code=200,
    corpo={"CHUVA": "42.0", "DT_MEDICAO": "2026-08-30", "HR_MEDICAO": "1200"},
)
RESPOSTA_INVALIDA = RespostaColetaInmet(status_code=200, corpo={"CHUVA": None})


class AreasFalsas:
    """Porta de áreas monitoradas falsa, resolvendo por id de um dicionário fixo."""

    def __init__(self, areas: dict[UUID, AreaMonitorada]) -> None:
        self._areas = areas

    def buscar_por_codigo_estacao(self, codigo_estacao_inmet: str) -> AreaMonitorada | None:
        for area in self._areas.values():
            if area.codigo_estacao_inmet == codigo_estacao_inmet:
                return area
        return None

    def buscar_por_id(self, id: UUID) -> AreaMonitorada | None:
        return self._areas.get(id)


class EventosFalsos:
    """Porta de eventos meteorológicos falsa, registrando os eventos salvos."""

    def __init__(self) -> None:
        self.salvos: list[object] = []

    def salvar(self, evento: object) -> None:
        self.salvos.append(evento)


class SincronizacoesFalsas:
    """Porta de sincronizações falsa, sobre um dicionário em memória."""

    def __init__(self) -> None:
        self._linhas: dict[UUID, Sincronizacao] = {}
        self.chamadas_criar = 0

    def criar(
        self,
        requisicao_id: UUID,
        area_monitorada_id: UUID,
        origem: OrigemSincronizacao,
        estado: EstadoSincronizacao,
    ) -> Sincronizacao:
        self.chamadas_criar += 1
        sincronizacao = Sincronizacao(
            id=uuid4(),
            requisicao_id=requisicao_id,
            area_monitorada_id=area_monitorada_id,
            origem=origem,
            estado=estado,
            registros_validos=0,
            motivo_falha=None,
            iniciado_em=datetime.now(UTC),
            finalizado_em=None,
        )
        self._linhas[sincronizacao.id] = sincronizacao
        return sincronizacao

    def atualizar_estado(
        self,
        id: UUID,
        estado: EstadoSincronizacao,
        registros_validos: int = 0,
        motivo_falha: str | None = None,
    ) -> None:
        atual = self._linhas[id]
        self._linhas[id] = Sincronizacao(
            id=atual.id,
            requisicao_id=atual.requisicao_id,
            area_monitorada_id=atual.area_monitorada_id,
            origem=atual.origem,
            estado=estado,
            registros_validos=registros_validos,
            motivo_falha=motivo_falha,
            iniciado_em=atual.iniciado_em,
            finalizado_em=datetime.now(UTC),
        )

    def listar_recentes(self) -> tuple[Sincronizacao, ...]:
        return tuple(
            sorted(self._linhas.values(), key=lambda s: s.iniciado_em, reverse=True)
        )

    def estado_de(self, id: UUID) -> Sincronizacao:
        return self._linhas[id]


class IdempotenciaFalsa:
    """Porta de idempotência falsa, sobre um dicionário em memória."""

    def __init__(self) -> None:
        self._registros: dict[tuple[str, str], RespostaRegistrada] = {}
        self.chamadas_registrar = 0

    def buscar(self, chave: str, operacao: str) -> RespostaRegistrada | None:
        return self._registros.get((chave, operacao))

    def registrar(
        self, chave: str, operacao: str, hash_requisicao: str, status: int, corpo: str
    ) -> None:
        self.chamadas_registrar += 1
        self._registros[(chave, operacao)] = RespostaRegistrada(
            hash_requisicao=hash_requisicao, status=status, corpo=corpo
        )


def montar_servico(
    coletor: AdaptadorInmetFalso,
    areas: dict[UUID, AreaMonitorada] | None = None,
) -> tuple[ServicoColetaMeteorologica, SincronizacoesFalsas, EventosFalsos, IdempotenciaFalsa]:
    sincronizacoes = SincronizacoesFalsas()
    eventos = EventosFalsos()
    idempotencia = IdempotenciaFalsa()
    portas = PortasColetaMeteorologica(
        idempotencia=idempotencia,
        areas=AreasFalsas(areas if areas is not None else {AREA.id: AREA}),
        coletor=coletor,
        normalizador=NormalizadorInmet(),
        eventos=eventos,  # type: ignore[arg-type]
        sincronizacoes=sincronizacoes,  # type: ignore[arg-type]
    )
    return ServicoColetaMeteorologica(portas), sincronizacoes, eventos, idempotencia


def test_solicitar_coleta_manual_persiste_sincronizacao_em_coletando_antes_de_qualquer_coisa() -> (
    None
):
    coletor = AdaptadorInmetFalso(resposta=RESPOSTA_VALIDA)
    servico, sincronizacoes, _, _ = montar_servico(coletor)

    aceita = asyncio.run(servico.solicitar_coleta_manual(AREA.id, "chave-1", "hash-1"))

    assert sincronizacoes.chamadas_criar == 1
    criada = sincronizacoes.listar_recentes()[0]
    assert criada.estado == EstadoSincronizacao.CONCLUIDO  # já fechada ao fim da execução síncrona
    assert aceita.sincronizacao.id == criada.id


def test_executar_coleta_com_sucesso_produz_evento_normalizado_e_sincronizacao_concluida() -> None:
    coletor = AdaptadorInmetFalso(resposta=RESPOSTA_VALIDA)
    servico, sincronizacoes, eventos, _ = montar_servico(coletor)

    resultado = asyncio.run(
        servico.executar_coleta(AREA, uuid4(), OrigemSincronizacao.AUTOMATICA)
    )

    assert resultado.estado == EstadoSincronizacao.CONCLUIDO
    assert resultado.registros_validos == 1
    assert resultado.motivo_falha is None
    assert len(eventos.salvos) == 1
    evento = eventos.salvos[0]
    assert evento.tipo == TipoEventoMeteorologico.CHUVA_INTENSA  # type: ignore[union-attr]
    assert evento.proveniencia == ProvenienciaEvento.REAL_INMET  # type: ignore[union-attr]


def test_executar_coleta_com_resposta_invalida_produz_falha_com_motivo_sem_criar_evento() -> None:
    coletor = AdaptadorInmetFalso(resposta=RESPOSTA_INVALIDA)
    servico, sincronizacoes, eventos, _ = montar_servico(coletor)

    resultado = asyncio.run(
        servico.executar_coleta(AREA, uuid4(), OrigemSincronizacao.AUTOMATICA)
    )

    assert resultado.estado == EstadoSincronizacao.FALHA
    assert resultado.motivo_falha == "campo_ausente"
    assert eventos.salvos == []


def test_executar_coleta_com_erro_de_transporte_produz_falha_sem_criar_evento() -> None:
    coletor = AdaptadorInmetFalso(excecao=httpx.TimeoutException("timeout"))
    servico, sincronizacoes, eventos, _ = montar_servico(coletor)

    resultado = asyncio.run(
        servico.executar_coleta(AREA, uuid4(), OrigemSincronizacao.AUTOMATICA)
    )

    assert resultado.estado == EstadoSincronizacao.FALHA
    assert resultado.motivo_falha == "erro_transporte_ou_timeout"
    assert eventos.salvos == []


def test_repetir_solicitar_coleta_manual_com_mesma_chave_nao_dispara_nova_coleta() -> None:
    coletor = AdaptadorInmetFalso(resposta=RESPOSTA_VALIDA)
    servico, sincronizacoes, _, idempotencia = montar_servico(coletor)

    primeira = asyncio.run(servico.solicitar_coleta_manual(AREA.id, "chave-repetida", "hash-x"))
    segunda = asyncio.run(servico.solicitar_coleta_manual(AREA.id, "chave-repetida", "hash-x"))

    assert len(coletor.chamadas) == 1
    assert sincronizacoes.chamadas_criar == 1
    assert segunda.sincronizacao.id == primeira.sincronizacao.id
    assert segunda.aceito_em == primeira.aceito_em


def test_repetir_chave_com_hash_diferente_levanta_conflito_idempotencia() -> None:
    coletor = AdaptadorInmetFalso(resposta=RESPOSTA_VALIDA)
    servico, _, _, _ = montar_servico(coletor)
    asyncio.run(servico.solicitar_coleta_manual(AREA.id, "chave-y", "hash-original"))

    with pytest.raises(ConflitoIdempotencia):
        asyncio.run(servico.solicitar_coleta_manual(AREA.id, "chave-y", "hash-diferente"))


def test_solicitar_coleta_manual_com_area_inexistente_levanta_erro_tipado() -> None:
    coletor = AdaptadorInmetFalso(resposta=RESPOSTA_VALIDA)
    servico, _, _, _ = montar_servico(coletor, areas={})

    with pytest.raises(AreaMonitoradaInexistente):
        asyncio.run(servico.solicitar_coleta_manual(AREA.id, "chave-z", "hash-z"))


def test_nenhum_log_do_caso_de_uso_expoe_corpo_externo_ou_credenciais(
    capsys: pytest.CaptureFixture[str],
) -> None:
    coletor = AdaptadorInmetFalso(resposta=RESPOSTA_VALIDA)
    servico, _, _, _ = montar_servico(coletor)

    asyncio.run(servico.executar_coleta(AREA, uuid4(), OrigemSincronizacao.AUTOMATICA))

    saida = capsys.readouterr()
    assert "CHUVA" not in saida.out
    assert "CHUVA" not in saida.err
