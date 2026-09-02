"""Portas e tipos compartilhados da coleta e normalização meteorológica do INMET."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from central_preventiva.dominio.evento_meteorologico import EventoMeteorologico


class OrigemSincronizacao(StrEnum):
    """Origem de uma sincronização, alinhada ao `CHECK` de
    `sincronizacoes_meteorologicas.origem`."""

    AUTOMATICA = "automatica"
    MANUAL = "manual"


class EstadoSincronizacao(StrEnum):
    """Estado de uma sincronização, alinhado ao `CHECK` de
    `sincronizacoes_meteorologicas.estado`."""

    COLETANDO = "coletando"
    NORMALIZANDO = "normalizando"
    CONCLUIDO = "concluido"
    FALHA = "falha"


@dataclass(frozen=True, slots=True)
class AreaMonitorada:
    """Mapeia uma estação real do INMET para a área sintética da demonstração (AD-007)."""

    id: UUID
    codigo_estacao_inmet: str
    nome_estacao: str
    codigo_ibge_area: str
    ativa: bool


@dataclass(frozen=True, slots=True)
class RespostaColetaInmet:
    """Resposta bruta de uma chamada de coleta ao INMET, ainda não normalizada."""

    status_code: int
    corpo: object


@dataclass(frozen=True, slots=True)
class Sincronizacao:
    """Registro de uma tentativa de sincronização meteorológica, pronto para consulta."""

    id: UUID
    requisicao_id: UUID
    area_monitorada_id: UUID
    origem: OrigemSincronizacao
    estado: EstadoSincronizacao
    registros_validos: int
    motivo_falha: str | None
    iniciado_em: datetime
    finalizado_em: datetime | None


INTERVALO_SEGUNDOS_COLETA = 900
"""Intervalo entre coletas automáticas (15 minutos), confirmado no Design (AD-006)."""


class ColetorMeteorologico(Protocol):
    """Executa uma coleta meteorológica bruta para uma área monitorada, sem normalizar."""

    async def coletar(self, area: AreaMonitorada) -> RespostaColetaInmet:
        """Devolve a resposta bruta da fonte meteorológica para a área informada."""
        ...


class RepositorioAreasMonitoradas(Protocol):
    """Consulta o mapeamento entre estação real do INMET e área sintética."""

    def buscar_por_codigo_estacao(self, codigo_estacao_inmet: str) -> AreaMonitorada | None:
        """Resolve a área monitorada a partir do código real da estação, se houver mapeamento."""
        ...

    def buscar_por_id(self, id: UUID) -> AreaMonitorada | None:
        """Resolve a área monitorada a partir do seu identificador interno, se existir.

        # SPEC_DEVIATION: método ausente do `design.md` original de T3; adicionado em T8
        # porque `solicitar_coleta_manual` precisa resolver o `area_id` recebido pela API
        # em uma `AreaMonitorada` completa antes de disparar a coleta.
        """
        ...

    def listar_ativas(self) -> tuple[AreaMonitorada, ...]:
        """Lista as áreas monitoradas atualmente ativas, para a coleta automática.

        # SPEC_DEVIATION: método ausente do `design.md` original de T3; adicionado em T10
        # porque o `AgendadorMeteorologico` precisa enumerar todas as áreas ativas a cada
        # ciclo, sem lista manual.
        """
        ...


class RepositorioEventosMeteorologicos(Protocol):
    """Persiste eventos meteorológicos normalizados."""

    def salvar(self, evento: EventoMeteorologico) -> None:
        """Persiste o evento meteorológico normalizado."""
        ...

    def listar(self) -> tuple[EventoMeteorologico, ...]:
        """Lista os eventos meteorológicos normalizados, do mais recente para o mais antigo.

        # SPEC_DEVIATION: método ausente do `design.md` original de T3; adicionado em T9
        # porque `GET /api/v1/meteorologia/eventos` precisa consultar os eventos já
        # normalizados e persistidos.
        """
        ...


class RepositorioSincronizacoes(Protocol):
    """Persiste e consulta o histórico de tentativas de sincronização meteorológica."""

    def criar(
        self,
        requisicao_id: UUID,
        area_monitorada_id: UUID,
        origem: OrigemSincronizacao,
        estado: EstadoSincronizacao,
    ) -> Sincronizacao:
        """Persiste uma nova tentativa de sincronização, antes de qualquer resposta ao chamador."""
        ...

    def atualizar_estado(
        self,
        id: UUID,
        estado: EstadoSincronizacao,
        registros_validos: int = 0,
        motivo_falha: str | None = None,
    ) -> None:
        """Fecha ou avança o estado de uma sincronização já persistida."""
        ...

    def listar_recentes(self) -> tuple[Sincronizacao, ...]:
        """Lista o histórico de sincronizações, da mais recente para a mais antiga."""
        ...

    def buscar_por_id(self, id: UUID) -> Sincronizacao | None:
        """Resolve a sincronização a partir do seu identificador, ou `None` se ausente.

        # SPEC_DEVIATION: método ausente do `design.md` original de T3 (2.1); adicionado
        # em T5 (2.2) porque `solicitar_nova_tentativa` precisa resolver a área da
        # sincronização de origem antes de disparar a nova tentativa correlacionada.
        """
        ...


class CodigoResultadoTentativa(StrEnum):
    """Resultado de uma tentativa individual de coleta, alinhado ao `CHECK` de
    `tentativas_coleta_meteorologica.codigo_resultado`."""

    SUCESSO = "sucesso"
    TIMEOUT = "timeout"
    ERRO_TRANSPORTE = "erro_transporte"
    STATUS_ERRO = "status_erro"


@dataclass(frozen=True, slots=True)
class TentativaColeta:
    """Registro de uma tentativa individual dentro de uma coleta com retry (RESIL-02)."""

    id: UUID
    sincronizacao_id: UUID
    numero_tentativa: int
    codigo_resultado: CodigoResultadoTentativa
    iniciado_em: datetime
    finalizado_em: datetime


class RepositorioTentativasColeta(Protocol):
    """Persiste e consulta as tentativas individuais de uma coleta com retry."""

    def registrar_tentativa(
        self,
        sincronizacao_id: UUID,
        numero_tentativa: int,
        codigo_resultado: CodigoResultadoTentativa,
        iniciado_em: datetime,
        finalizado_em: datetime,
    ) -> None:
        """Persiste uma tentativa individual, assim que ela termina."""
        ...

    def listar_tentativas(self, sincronizacao_id: UUID) -> tuple[TentativaColeta, ...]:
        """Lista as tentativas de uma sincronização, em ordem crescente de número."""
        ...


class RepositorioCenariosSinteticosAtivados(Protocol):
    """Registra quando/qual cenário sintético de contingência foi ativado (RESIL-13)."""

    def registrar(self, sincronizacao_id: UUID, identificador_cenario: str) -> None:
        """Persiste a ativação de um cenário sintético, correlacionada à sua sincronização."""
        ...
