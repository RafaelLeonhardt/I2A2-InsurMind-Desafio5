"""Caso de uso da lista de comunicados do segurado ativo (COMUNICADOS-01, COMUNICADOS-02).

`ServicoListaComunicados.listar` é uma agregação de leitura pura: cada entrega simulada do
segurado (3.6, já filtrada por `simulada_entregue` em `listar_por_segurado`, 5.5) ganha o
estado de visualização já registrado, se houver (`visualizacoes_comunicado`, 4.3) — nenhuma
tabela nova, nenhuma escrita. O detalhe e o registro da própria visualização continuam sendo
`ServicoVisualizacaoComunicado` (4.3), reusado sem alteração pelo roteador HTTP desta história.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    EntregaDoSegurado,
)
from central_preventiva.adaptadores.persistencia.repositorio_visualizacoes_comunicado import (
    VisualizacaoComunicado,
)
from central_preventiva.dominio.validador_saida_canal import Canal


@dataclass(frozen=True, slots=True)
class ItemComunicadoListado:
    """Um item da lista de comunicados: canal, assunto/resumo, data e visualização."""

    entrega_simulada_id: UUID
    mensagem_id: UUID
    canal: Canal
    assunto_ou_resumo: str
    criado_em: datetime
    visualizacao: VisualizacaoComunicado | None


class _RepositorioEntregasSimuladas(Protocol):
    """Porta mínima de `entregas_simuladas` (3.6, estendida em 5.5)."""

    def listar_por_segurado(self, segurado_id: UUID) -> list[EntregaDoSegurado]: ...


class _RepositorioVisualizacoesComunicado(Protocol):
    """Porta mínima de `visualizacoes_comunicado` (4.3)."""

    def obter_por_entrega(self, entrega_simulada_id: UUID) -> VisualizacaoComunicado | None: ...


@dataclass(frozen=True, slots=True)
class PortasListaComunicados:
    """Agrupa as portas de que a lista de comunicados depende."""

    entregas: _RepositorioEntregasSimuladas
    visualizacoes: _RepositorioVisualizacoesComunicado


class ServicoListaComunicados:
    """Monta a lista de comunicados do segurado, com o estado de visualização de cada um."""

    def __init__(self, portas: PortasListaComunicados) -> None:
        """Guarda as portas usadas pela lista de comunicados."""

        self._portas = portas

    def listar(self, segurado_id: UUID) -> list[ItemComunicadoListado]:
        """Lista os comunicados do segurado, mais antigos primeiro (COMUNICADOS-01/02).

        Devolve lista vazia quando o segurado não tiver nenhum comunicado — nunca um erro.
        """

        entregas = self._portas.entregas.listar_por_segurado(segurado_id)
        return [self._item(entrega) for entrega in entregas]

    def _item(self, entrega: EntregaDoSegurado) -> ItemComunicadoListado:
        """Monta um item da lista a partir de uma entrega do segurado."""

        return ItemComunicadoListado(
            entrega_simulada_id=entrega.id,
            mensagem_id=entrega.mensagem_id,
            canal=entrega.canal,
            assunto_ou_resumo=entrega.assunto_ou_resumo,
            criado_em=entrega.criado_em,
            visualizacao=self._portas.visualizacoes.obter_por_entrega(entrega.id),
        )
