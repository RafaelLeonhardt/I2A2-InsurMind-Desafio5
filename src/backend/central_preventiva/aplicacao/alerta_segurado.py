"""Caso de uso do alerta mais relevante do segurado ativo (VISAO-01..06, 5.1).

`ServicoAlertaSegurado.obter_mais_relevante` monta o alerta a partir da elegibilidade
`incluido` mais recente do segurado (2.5), sem depender de `avaliacoes_risco` (2.3) ou de
`contextos_agente` (3.1): ambas só existem depois que uma execução real do Épico 2/3 chega
lá, e o segurado padrão da demonstração começa só com a linha semeada de elegibilidade, sem
nenhuma execução associada (`execucao_id IS NULL`). Evento e regra, ao contrário, sempre
existem para qualquer elegibilidade persistida — então a severidade é recomputada com a
mesma função pura e determinística do avaliador de risco (RISCO-06/07: mesma entrada sempre
produz a mesma saída), e as recomendações reusam a mesma constante estática que
`MontadorContextoAgente` usa para montar `ContextoAgente.orientacoes_seguranca` — a mesma
fonte de dado, sem depender do registro persistido existir.

SPEC_DEVIATION: o design.md lista `RepositorioContextosAgente` e `RepositorioAvaliacoesRisco`
como dependências. Nenhuma das duas é usada pelo motivo acima — ambas ficariam `None` para o
segurado padrão da demonstração, quebrando exatamente o caminho que esta história existe
para corrigir (AD-9, mockup estático).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RegistroElegibilidade,
)
from central_preventiva.adaptadores.persistencia.repositorio_regras import Regra
from central_preventiva.aplicacao.portas_meteorologia import (
    AreaMonitorada,
    EstadoSincronizacao,
    Sincronizacao,
    TentativaColeta,
)
from central_preventiva.dominio.avaliador_risco import RegraSnapshot, avaliar
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)
from central_preventiva.dominio.montador_contexto_agente import ORIENTACOES_POR_EVENTO

OPERANDO_AREA_APLICAVEL = "área aplicável"
"""Nome estável do critério de área da avaliação de risco (dominio/avaliador_risco.py) —
usado para separar o critério de área do critério de intensidade/ocorrência, nunca por
posição."""


@dataclass(frozen=True, slots=True)
class AlertaSegurado:
    """O alerta mais relevante exibível ao segurado ativo: evento, período, localização,
    impactos, recomendações, origem e caráter da fonte no momento da consulta."""

    elegibilidade_id: UUID
    evento_tipo: TipoEventoMeteorologico
    severidade: str
    periodo_inicio: datetime
    periodo_fim: datetime
    localizacao: str
    impactos_esperados: tuple[str, ...]
    recomendacoes: tuple[str, ...]
    origem: ProvenienciaEvento
    instante_observado: datetime
    fonte_degradada: bool


class _RepositorioElegibilidades(Protocol):
    """Porta mínima de `elegibilidades_historicas` (2.5, estendida em 5.1)."""

    def obter_mais_recente_por_segurado(
        self, segurado_id: UUID
    ) -> RegistroElegibilidade | None: ...


class _RepositorioEventos(Protocol):
    """Porta mínima de `eventos_meteorologicos` (2.1)."""

    def buscar_por_id(self, id: UUID) -> EventoMeteorologico | None: ...


class _RepositorioRegras(Protocol):
    """Porta mínima de `regras` (2.3/2.4)."""

    def obter_por_id(self, regra_id: UUID) -> Regra | None: ...


class _RepositorioAreasMonitoradas(Protocol):
    """Porta mínima de `areas_monitoradas_inmet` (AD-007)."""

    def listar_ativas(self) -> tuple[AreaMonitorada, ...]: ...


class _RepositorioSincronizacoes(Protocol):
    """Porta mínima de `sincronizacoes_meteorologicas` (2.1/2.2)."""

    def listar_recentes(self) -> tuple[Sincronizacao, ...]: ...


class _RepositorioTentativasColeta(Protocol):
    """Porta mínima de `tentativas_coleta_meteorologica` (2.2)."""

    def listar_tentativas(self, sincronizacao_id: UUID) -> tuple[TentativaColeta, ...]: ...


@dataclass(frozen=True, slots=True)
class PortasAlertaSegurado:
    """Agrupa as portas de que o alerta do segurado depende."""

    elegibilidades: _RepositorioElegibilidades
    eventos: _RepositorioEventos
    regras: _RepositorioRegras
    areas_monitoradas: _RepositorioAreasMonitoradas
    sincronizacoes: _RepositorioSincronizacoes
    tentativas: _RepositorioTentativasColeta


class ServicoAlertaSegurado:
    """Resolve o alerta mais relevante do segurado ativo, só leitura."""

    def __init__(self, portas: PortasAlertaSegurado) -> None:
        """Guarda as portas usadas pela consulta do alerta."""

        self._portas = portas

    def obter_mais_relevante(self, segurado_id: UUID) -> AlertaSegurado | None:
        """Monta o alerta a partir da elegibilidade `incluido` mais recente do segurado,
        ou `None` se não houver nenhuma (VISAO-04)."""

        registro = self._portas.elegibilidades.obter_mais_recente_por_segurado(segurado_id)
        if registro is None:
            return None

        evento = self._portas.eventos.buscar_por_id(registro.evento_id)
        assert evento is not None, (
            f"evento {registro.evento_id} referenciado pela elegibilidade "
            f"{registro.id} não encontrado"
        )
        regra = self._portas.regras.obter_por_id(registro.regra_id)
        assert regra is not None, (
            f"regra {registro.regra_id} referenciada pela elegibilidade "
            f"{registro.id} não encontrada"
        )

        resultado_risco = avaliar(
            evento,
            RegraSnapshot(
                id=regra.id,
                evento_tipo=regra.evento_tipo,
                limiar_meteorologico=regra.limiar_meteorologico,
                area_aplicavel=regra.area_aplicavel,
                apolice_tipo=regra.apolice_tipo,
                cobertura_exigida=regra.cobertura_exigida,
                versao=regra.versao,
            ),
        )
        criterio_severidade = next(
            (
                criterio
                for criterio in resultado_risco.criterios
                if criterio.operando != OPERANDO_AREA_APLICAVEL
            ),
            None,
        )
        severidade = (
            f"{criterio_severidade.valor_observado} — {criterio_severidade.justificativa}"
            if criterio_severidade is not None
            else ""
        )

        return AlertaSegurado(
            elegibilidade_id=registro.id,
            evento_tipo=evento.tipo,
            severidade=severidade,
            periodo_inicio=evento.periodo_inicio,
            periodo_fim=evento.periodo_fim,
            localizacao=evento.area,
            impactos_esperados=(regra.cobertura_exigida,),
            recomendacoes=ORIENTACOES_POR_EVENTO.get(evento.tipo, ()),
            origem=evento.proveniencia,
            instante_observado=evento.instante_observado,
            fonte_degradada=self._fonte_degradada(evento),
        )

    def _fonte_degradada(self, evento: EventoMeteorologico) -> bool:
        """Reflete o estado da última sincronização real da área do evento (VISAO-05).

        Nunca se aplica a evento sintético (`granizo`, AD-013): não há sincronização real
        para refletir, e rotular um cenário sintético como "fonte degradada" confundiria as
        duas noções de origem que a spec exige manter distintas (VISAO-02).
        """

        if evento.proveniencia is not ProvenienciaEvento.REAL_INMET:
            return False

        area = next(
            (
                candidata
                for candidata in self._portas.areas_monitoradas.listar_ativas()
                if candidata.codigo_ibge_area == evento.area
            ),
            None,
        )
        if area is None:
            return False

        ultima = next(
            (
                sincronizacao
                for sincronizacao in self._portas.sincronizacoes.listar_recentes()
                if sincronizacao.area_monitorada_id == area.id
            ),
            None,
        )
        if ultima is None:
            return False
        if ultima.estado is EstadoSincronizacao.FALHA:
            return True

        tentativas = self._portas.tentativas.listar_tentativas(ultima.id)
        return len(tentativas) > 1
