"""Caso de uso da abertura do comunicado e da primeira visualização (VISU-01, 04, 05).

`obter_comunicado` resolve a entrega simulada e o resumo exibível ao segurado sintético,
validando que a mensagem de origem pertence ao `segurado_id` informado antes de devolver
qualquer dado — mesmo padrão de não-enumeração de 4.2: uma entrega inexistente e uma entrega
de outro segurado são indistinguíveis, ambas `None` (VISU-05, AD-011).

`registrar_visualizacao` só grava quando a mensagem de origem está em `simulada_entregue`
(VISU-04): mensagem ainda não simulada, rejeitada, excluída ou em exceção nunca vira marco de
visualização — a checagem acontece antes de qualquer escrita, nunca depois.

SPEC_DEVIATION: o `design.md` declara `registrar_visualizacao(self, entrega_simulada_id) ->
VisualizacaoComunicado`, sem `segurado_id` e sem devolver `None`. `obter_comunicado` (GET) e
`registrar_visualizacao` (POST) são duas chamadas HTTP separadas e não confiáveis entre si — a
segunda não pode presumir que a primeira já validou o pertencimento ao segurado. `segurado_id`
é obrigatório aqui pela mesma razão de VISU-05, e o retorno é `VisualizacaoComunicado | None`
para que uma entrega de outro segurado feche com o mesmo não-encontrado do `GET`, nunca com uma
gravação.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RegistroElegibilidade,
)
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    ApresentacaoSimulada,
    EntregaSimulada,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import RegistroMensagem
from central_preventiva.adaptadores.persistencia.repositorio_visualizacoes_comunicado import (
    VisualizacaoComunicado,
)
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.validador_saida_canal import Canal


class MensagemNaoElegivelParaComunicado(RuntimeError):
    """Indica que a mensagem de origem da entrega não está em `simulada_entregue` (VISU-04)."""

    def __init__(self, entrega_simulada_id: UUID, estado: EstadoMensagem) -> None:
        """Identifica a entrega e o estado que impede a visualização."""

        super().__init__(
            f"A entrega '{entrega_simulada_id}' tem mensagem de origem em '{estado}', "
            "não elegível para virar comunicado."
        )
        self.entrega_simulada_id = entrega_simulada_id
        self.estado = estado


@dataclass(frozen=True, slots=True)
class Comunicado:
    """O que Carlos vê ao abrir um comunicado: conteúdo, canal e visualização, se houver."""

    entrega_simulada_id: UUID
    mensagem_id: UUID
    canal: Canal
    apresentacao: ApresentacaoSimulada
    criado_em: datetime
    visualizacao: VisualizacaoComunicado | None


class _RepositorioMensagens(Protocol):
    """Porta mínima de `mensagens` (3.2)."""

    def obter(self, mensagem_id: UUID) -> RegistroMensagem | None: ...


class _RepositorioEntregasSimuladas(Protocol):
    """Porta mínima de `entregas_simuladas` (3.6)."""

    def obter_por_id(self, entrega_simulada_id: UUID) -> EntregaSimulada | None: ...


class _RepositorioElegibilidades(Protocol):
    """Porta mínima do público elegível preservado pela execução (2.5)."""

    def obter_por_id(self, id_registro: UUID) -> RegistroElegibilidade | None: ...


class _RepositorioVisualizacoesComunicado(Protocol):
    """Porta mínima de `visualizacoes_comunicado` (4.3)."""

    def registrar_primeira_visualizacao(
        self, entrega_simulada_id: UUID, segurado_id: UUID
    ) -> VisualizacaoComunicado: ...

    def obter_por_entrega(self, entrega_simulada_id: UUID) -> VisualizacaoComunicado | None: ...


@dataclass(frozen=True, slots=True)
class PortasVisualizacaoComunicado:
    """Agrupa as portas de que a visualização do comunicado depende."""

    mensagens: _RepositorioMensagens
    entregas: _RepositorioEntregasSimuladas
    elegibilidades: _RepositorioElegibilidades
    visualizacoes: _RepositorioVisualizacoesComunicado


class ServicoVisualizacaoComunicado:
    """Resolve o comunicado exibível e registra sua primeira visualização."""

    def __init__(self, portas: PortasVisualizacaoComunicado) -> None:
        """Guarda as portas usadas pela visualização do comunicado."""

        self._portas = portas

    def obter_comunicado(
        self, entrega_simulada_id: UUID, segurado_id: UUID
    ) -> Comunicado | None:
        """Devolve o comunicado, ou `None` se a entrega não existir ou não pertencer ao
        `segurado_id` informado (VISU-05) — resposta idêntica nos dois casos."""

        resolucao = self._resolver(entrega_simulada_id, segurado_id)
        if resolucao is None:
            return None
        entrega, _ = resolucao
        return Comunicado(
            entrega_simulada_id=entrega.id,
            mensagem_id=entrega.mensagem_id,
            canal=entrega.canal,
            apresentacao=entrega.apresentacao,
            criado_em=entrega.criado_em,
            visualizacao=self._portas.visualizacoes.obter_por_entrega(entrega.id),
        )

    def registrar_visualizacao(
        self, entrega_simulada_id: UUID, segurado_id: UUID
    ) -> VisualizacaoComunicado | None:
        """Registra a primeira visualização, ou `None` se a entrega não pertencer ao
        `segurado_id` informado (VISU-05). Levanta `MensagemNaoElegivelParaComunicado` se a
        mensagem de origem não estiver em `simulada_entregue` (VISU-04)."""

        resolucao = self._resolver(entrega_simulada_id, segurado_id)
        if resolucao is None:
            return None
        entrega, mensagem = resolucao
        if mensagem.estado is not EstadoMensagem.SIMULADA_ENTREGUE:
            raise MensagemNaoElegivelParaComunicado(entrega_simulada_id, mensagem.estado)
        return self._portas.visualizacoes.registrar_primeira_visualizacao(
            entrega.id, segurado_id
        )

    def _resolver(
        self, entrega_simulada_id: UUID, segurado_id: UUID
    ) -> tuple[EntregaSimulada, RegistroMensagem] | None:
        """Resolve a entrega e a mensagem de origem, validando o pertencimento ao segurado.

        Uma entrega inexistente e uma entrega cuja mensagem pertence a outro segurado
        devolvem o mesmo `None` — nenhuma distinção que revele a existência cruzada de um
        registro (VISU-05, AD-011, mesmo padrão de 4.2).
        """

        entrega = self._portas.entregas.obter_por_id(entrega_simulada_id)
        if entrega is None:
            return None
        mensagem = self._portas.mensagens.obter(entrega.mensagem_id)
        if mensagem is None:
            return None
        elegibilidade = self._portas.elegibilidades.obter_por_id(mensagem.elegibilidade_id)
        if elegibilidade is None or elegibilidade.segurado_id != segurado_id:
            return None
        return entrega, mensagem
