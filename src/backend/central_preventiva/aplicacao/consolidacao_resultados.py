"""Caso de uso de consolidação e reconciliação de resultados da simulação (RESULT-01..07,09).

`ServicoConsolidacaoResultados.consolidar` é uma agregação somente leitura sobre `mensagens`
(3.2) e `entregas_simuladas` (3.6) — nenhuma escrita, nenhuma migração nova. A sequência de
exibição `Preparada`/`Processada`/`Enviada — simulação` já aconteceu inteira e atomicamente no
momento em que uma entrega existe (3.6, `ServicoSimulacao.confirmar`); esta consulta apenas
traduz esse fato, sem persistir nenhum sub-estado novo (design.md, Tech Decisions).

Totais por canal e por estado cobrem **todas** as mensagens da execução, para que a soma
reconcilie com a quantidade real de aprovadas/simuladas/rejeitadas/excluídas/em exceção
(RESULT-02). `nao_simulaveis` extrai só as rejeitadas, excluídas e em exceção técnica, com um
motivo legível, para explicar a diferença sem somá-las às entregas simuladas (RESULT-03).

`concluido` é verdadeiro só em `concluida`/`falhou_simulacao` (AD-004): antes disso, uma
mensagem pode migrar de `aprovada` para `simulada_entregue` a qualquer instante dentro da
transação 1 de 3.6, e mostrar um total parcial nesse meio-tempo o apresentaria como final, o
que a spec proíbe (Edge Case "consulta durante `simulando`"). Enquanto não concluído, os totais
vêm vazios — apenas `estado` é significativo.

`divergencia` compara a contagem de `mensagens.estado = simulada_entregue` com a de
`entregas_simuladas`: as duas só divergem por corrupção de dado, nunca em operação normal (a
criação de ambas é atômica em 3.6). Detectada, a divergência é reportada com os dois lados e a
`execucao_id` como correlação — nunca "corrigida" nem ocultada (RESULT-09, design.md Risks).
"""

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    EntregaSimulada,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    SnapshotExecucao,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import RegistroMensagem
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.validador_saida_canal import Canal

ESTADOS_CONCLUSAO_SIMULACAO: frozenset[EstadoExecucao] = frozenset(
    {EstadoExecucao.CONCLUIDA, EstadoExecucao.FALHOU_SIMULACAO}
)
"""Estados em que a simulação terminou (com sucesso ou falha local) e os totais são finais."""

MOTIVOS_NAO_SIMULAVEL: dict[EstadoMensagem, str] = {
    EstadoMensagem.REJEITADA: "rejeitada pela revisão humana",
    EstadoMensagem.EXCLUIDA: "excluída da revisão humana",
    EstadoMensagem.FALHOU_CONTEUDO: "esgotou as tentativas de geração de conteúdo válido",
    EstadoMensagem.FALHOU_INTEGRACAO_IA: "falhou na integração com o agente de IA",
}
"""Estados terminais de mensagem que nunca viram entrega simulada, com o motivo legível."""


class ExecucaoInexistente(RuntimeError):
    """Indica que o `execucao_id` informado não corresponde a nenhuma execução (AD-011)."""

    def __init__(self, execucao_id: UUID) -> None:
        """Identifica a execução ausente e monta a mensagem em português."""

        super().__init__(f"A execução '{execucao_id}' não existe.")
        self.execucao_id = execucao_id


@dataclass(frozen=True, slots=True)
class MensagemNaoSimulavel:
    """Uma mensagem que nunca foi nem será simulada nesta execução, com o motivo."""

    mensagem_id: UUID
    canal: Canal
    estado: EstadoMensagem
    motivo: str


@dataclass(frozen=True, slots=True)
class DivergenciaTotais:
    """Inconsistência entre `mensagens.simulada_entregue` e `entregas_simuladas` (RESULT-09).

    Nunca esperada em operação normal (a criação de ambas é atômica em 3.6); reportada com os
    dois lados e a execução como correlação, nunca reconciliada silenciosamente.
    """

    execucao_id: UUID
    mensagens_simulada_entregue: int
    entregas_persistidas: int


@dataclass(frozen=True, slots=True)
class ResultadoConsolidado:
    """Totais reconciláveis do lote, ou o progresso real enquanto a simulação não terminou."""

    execucao_id: UUID
    estado: EstadoExecucao
    concluido: bool
    totais_por_canal: tuple[tuple[Canal, int], ...]
    totais_por_estado: tuple[tuple[EstadoMensagem, int], ...]
    nao_simulaveis: tuple[MensagemNaoSimulavel, ...]
    divergencia: DivergenciaTotais | None


class _RepositorioExecucaoPreventiva(Protocol):
    """Porta mínima do agregado da execução (2.2)."""

    def buscar(self, execucao_id: UUID) -> SnapshotExecucao | None: ...


class _RepositorioMensagens(Protocol):
    """Porta mínima de `mensagens` (3.2)."""

    def listar_por_execucao(
        self, execucao_id: UUID, conexao: Any = None
    ) -> list[RegistroMensagem]: ...


class _RepositorioEntregasSimuladas(Protocol):
    """Porta mínima de `entregas_simuladas` (3.6)."""

    def listar_por_execucao(self, execucao_id: UUID) -> list[EntregaSimulada]: ...


@dataclass(frozen=True, slots=True)
class PortasConsolidacaoResultados:
    """Agrupa as portas de leitura de que a consolidação de resultados depende."""

    execucoes: _RepositorioExecucaoPreventiva
    mensagens: _RepositorioMensagens
    entregas: _RepositorioEntregasSimuladas


class ServicoConsolidacaoResultados:
    """Agrega totais por canal/estado e reconcilia a simulação, sem nenhuma escrita."""

    def __init__(self, portas: PortasConsolidacaoResultados) -> None:
        """Guarda as portas de leitura usadas pela consolidação."""

        self._portas = portas

    def consolidar(self, execucao_id: UUID) -> ResultadoConsolidado:
        """Reconstrói os resultados do DuckDB a cada chamada (RESULT-06/07): nunca persiste
        nem repete nenhuma transição, e nunca reabre ou regride um estado terminal."""

        snapshot = self._portas.execucoes.buscar(execucao_id)
        if snapshot is None:
            raise ExecucaoInexistente(execucao_id)

        concluido = snapshot.estado in ESTADOS_CONCLUSAO_SIMULACAO
        if not concluido:
            return ResultadoConsolidado(
                execucao_id=execucao_id,
                estado=snapshot.estado,
                concluido=False,
                totais_por_canal=(),
                totais_por_estado=(),
                nao_simulaveis=(),
                divergencia=None,
            )

        registros = self._portas.mensagens.listar_por_execucao(execucao_id)
        entregas = self._portas.entregas.listar_por_execucao(execucao_id)

        totais_por_canal = tuple(
            (canal, sum(1 for registro in registros if registro.canal is canal))
            for canal in Canal
        )
        estados_presentes = sorted({registro.estado for registro in registros}, key=str)
        totais_por_estado = tuple(
            (estado, sum(1 for registro in registros if registro.estado is estado))
            for estado in estados_presentes
        )
        nao_simulaveis = tuple(
            MensagemNaoSimulavel(
                mensagem_id=registro.id,
                canal=registro.canal,
                estado=registro.estado,
                motivo=MOTIVOS_NAO_SIMULAVEL[registro.estado],
            )
            for registro in registros
            if registro.estado in MOTIVOS_NAO_SIMULAVEL
        )

        simuladas_entregues = sum(
            1 for registro in registros if registro.estado is EstadoMensagem.SIMULADA_ENTREGUE
        )
        divergencia = (
            None
            if simuladas_entregues == len(entregas)
            else DivergenciaTotais(
                execucao_id=execucao_id,
                mensagens_simulada_entregue=simuladas_entregues,
                entregas_persistidas=len(entregas),
            )
        )

        return ResultadoConsolidado(
            execucao_id=execucao_id,
            estado=snapshot.estado,
            concluido=True,
            totais_por_canal=totais_por_canal,
            totais_por_estado=totais_por_estado,
            nao_simulaveis=nao_simulaveis,
            divergencia=divergencia,
        )
