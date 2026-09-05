"""Caso de uso da lista completa e do detalhe dos alertas do segurado ativo
(ALERTAS-01..06, 5.2).

Estende a mesma consulta de 5.1 para todas as elegibilidades `incluido` do segurado, não
só a mais recente, classificando cada uma em `ativo`/`anterior`/`ainda_nao_simulado` pelo
estado da execução associada. `obter_detalhe` reusa o mesmo padrão de não-enumeração de
4.2/4.3: uma elegibilidade inexistente e uma de outro segurado devolvem o mesmo `None`.

SPEC_DEVIATION: o design.md declara `listar(self, segurado_id) -> list[AlertaSegurado]`,
sem nenhum campo de classificação. Sem a classificação, a interface não pode cumprir
ALERTAS-01 ("ativos e anteriores são distinguíveis") — o próprio diagrama do Approach do
design.md já descreve a classificação como parte do fluxo. `listar` devolve
`list[ItemAlertaListado]` (alerta + classificação) em vez de `list[AlertaSegurado]` puro.

SPEC_DEVIATION: uma elegibilidade semeada sem execução (`execucao_id IS NULL`, mesmo caso
de 5.1) não tem `SnapshotExecucao` para consultar. Classificá-la exige decidir algo que o
design.md não previu; por analogia com a SPEC_DEVIATION de 5.1 (a linha semeada já
representa um alerta pronto para exibição, não um em andamento), ela é classificada só
pelo período do evento, como se a execução já tivesse concluído.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RegistroElegibilidade,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    SnapshotExecucao,
)
from central_preventiva.aplicacao.alerta_segurado import AlertaSegurado
from central_preventiva.aplicacao.linha_do_tempo import LinhaDoTempo, MarcoLinhaDoTempo
from central_preventiva.dominio.estados_execucao import EstadoExecucao

_ESTADOS_COM_DESFECHO_DE_SIMULACAO = frozenset(
    {EstadoExecucao.CONCLUIDA, EstadoExecucao.FALHOU_SIMULACAO}
)
"""Únicos estados em que a simulação já tem um desfecho definitivo (ALERTAS-01/05) — todo
o restante (em andamento ou terminal antes de chegar à simulação) é "ainda não simulado"."""


class ClassificacaoAlerta(StrEnum):
    """As três classificações possíveis de um alerta (ALERTAS-01, ALERTAS-05)."""

    ATIVO = "ativo"
    ANTERIOR = "anterior"
    AINDA_NAO_SIMULADO = "ainda_nao_simulado"


@dataclass(frozen=True, slots=True)
class ItemAlertaListado:
    """Um item da lista de alertas: o alerta em si e sua classificação."""

    alerta: AlertaSegurado
    classificacao: ClassificacaoAlerta


@dataclass(frozen=True, slots=True)
class DetalheAlertaSegurado:
    """O detalhe completo de um alerta: alerta, classificação, contexto da apólice e
    linha do tempo da execução que o produziu."""

    alerta: AlertaSegurado
    classificacao: ClassificacaoAlerta
    apolice_id: UUID
    justificativa: str
    linha_do_tempo: tuple[MarcoLinhaDoTempo, ...]


class _RepositorioElegibilidades(Protocol):
    """Porta mínima de `elegibilidades_historicas` (2.5, estendida em 5.1/5.2)."""

    def listar_todas_por_segurado(self, segurado_id: UUID) -> list[RegistroElegibilidade]: ...

    def obter_por_id(self, id_registro: UUID) -> RegistroElegibilidade | None: ...


class _RepositorioExecucaoPreventiva(Protocol):
    """Porta mínima de `execucao_preventiva` (2.2)."""

    def buscar(self, execucao_id: UUID) -> SnapshotExecucao | None: ...


class _ServicoAlertaSegurado(Protocol):
    """Porta mínima de `ServicoAlertaSegurado` (5.1) — monta o alerta reusando a mesma
    lógica de recomputação de risco e fonte degradada, sem duplicá-la aqui."""

    def montar_para_registro(self, registro: RegistroElegibilidade) -> AlertaSegurado: ...


class _ServicoLinhaDoTempo(Protocol):
    """Porta mínima de `ServicoLinhaDoTempo` (4.4)."""

    def montar(self, execucao_id: UUID) -> LinhaDoTempo | None: ...


@dataclass(frozen=True, slots=True)
class PortasListaAlertasSegurado:
    """Agrupa as portas de que a lista/detalhe de alertas do segurado depende."""

    elegibilidades: _RepositorioElegibilidades
    execucoes: _RepositorioExecucaoPreventiva
    alerta_segurado: _ServicoAlertaSegurado
    linha_do_tempo: _ServicoLinhaDoTempo


class ServicoListaAlertasSegurado:
    """Lista e classifica todos os alertas do segurado; resolve o detalhe de um alerta
    específico com verificação de pertencimento, só leitura."""

    def __init__(self, portas: PortasListaAlertasSegurado) -> None:
        """Guarda as portas usadas pela lista/detalhe de alertas."""

        self._portas = portas

    def listar(self, segurado_id: UUID) -> list[ItemAlertaListado]:
        """Lista todos os alertas `incluido` do segurado, mais recentes primeiro, cada
        um com sua classificação (ALERTAS-01)."""

        registros = self._portas.elegibilidades.listar_todas_por_segurado(segurado_id)
        return [self._item(registro) for registro in registros]

    def obter_detalhe(
        self, segurado_id: UUID, elegibilidade_id: UUID
    ) -> DetalheAlertaSegurado | None:
        """Devolve o detalhe do alerta, ou `None` se a elegibilidade não existir ou não
        pertencer ao `segurado_id` informado (ALERTAS-05) — resposta idêntica nos dois
        casos, mesmo padrão de não-enumeração de 4.2/4.3."""

        registro = self._portas.elegibilidades.obter_por_id(elegibilidade_id)
        if registro is None or registro.segurado_id != segurado_id:
            return None

        alerta = self._portas.alerta_segurado.montar_para_registro(registro)
        classificacao = self._classificar(registro, alerta)
        marcos: tuple[MarcoLinhaDoTempo, ...] = ()
        if registro.execucao_id is not None:
            linha = self._portas.linha_do_tempo.montar(registro.execucao_id)
            if linha is not None:
                marcos = linha.marcos

        return DetalheAlertaSegurado(
            alerta=alerta,
            classificacao=classificacao,
            apolice_id=registro.apolice_id,
            justificativa=registro.justificativa,
            linha_do_tempo=marcos,
        )

    def _item(self, registro: RegistroElegibilidade) -> ItemAlertaListado:
        """Monta um item da lista a partir de um registro de elegibilidade."""

        alerta = self._portas.alerta_segurado.montar_para_registro(registro)
        return ItemAlertaListado(alerta=alerta, classificacao=self._classificar(registro, alerta))

    def _classificar(
        self, registro: RegistroElegibilidade, alerta: AlertaSegurado
    ) -> ClassificacaoAlerta:
        """Classifica um alerta em `ativo`/`anterior`/`ainda_nao_simulado` pelo estado da
        execução associada (ALERTAS-01, ALERTAS-05) — ver SPEC_DEVIATION do módulo para a
        linha semeada sem execução."""

        if registro.execucao_id is not None:
            snapshot = self._portas.execucoes.buscar(registro.execucao_id)
            if snapshot is None or snapshot.estado not in _ESTADOS_COM_DESFECHO_DE_SIMULACAO:
                return ClassificacaoAlerta.AINDA_NAO_SIMULADO

        agora = datetime.now(UTC).replace(tzinfo=None)
        if alerta.periodo_fim >= agora:
            return ClassificacaoAlerta.ATIVO
        return ClassificacaoAlerta.ANTERIOR
