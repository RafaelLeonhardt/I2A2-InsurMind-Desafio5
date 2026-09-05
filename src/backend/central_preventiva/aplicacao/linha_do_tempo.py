"""Caso de uso da linha do tempo ponta a ponta e da busca de execuções (TIMELINE-01..09).

`ServicoLinhaDoTempo.montar` é uma agregação de leitura pura sobre até 9 fontes já
persistidas pelos Épicos 2/3/4 — nenhuma tabela nova, nenhuma escrita. Cada fonte contribui
sua fatia de `MarcoLinhaDoTempo` (`timestamp`, `ator`, `acao`, `resultado`, `correlacao`,
`tipo`, `mensagem_id` opcional); a lista final é ordenada por `timestamp`, e o frontend
agrupa visualmente por `mensagem_id` mantendo a ordem cronológica geral entre grupos (Tech
Decision do `design.md` — nenhuma segunda estrutura de dados no backend).

Uma execução `sem_risco`/`sem_elegiveis` nunca produz marcos de geração/crítica/simulação por
construção: essas fontes são sempre lidas por `execucao_id`/`mensagem_id`, e nenhuma mensagem
existe quando o público nunca chegou a se formar (TIMELINE-03).

SPEC_DEVIATION: o `design.md` lista `sincronizacoes_meteorologicas`/`tentativas_coleta_
meteorologica` (2.1/2.2) como fontes correlacionadas "por execucao_id". Nenhuma das duas
tabelas tem essa coluna — `Sincronizacao` é uma tentativa de coleta por área monitorada, sem
vínculo a uma execução específica (`ServicoColetaMeteorologica.coletar_para_execucao` cria uma
sincronização, mas nunca persiste o vínculo). O marco real e correlacionado da etapa de
coleta já existe em `marcos_execucao` (2.6): `GerenciadorExecucoes` registra
`coleta_concluida` no sucesso e o próprio estado `falhou_coleta` na falha, cada um com
timestamp. A linha do tempo usa `marcos_execucao` como a fonte real da etapa de coleta, não
uma junção direta com `sincronizacoes_meteorologicas`.

SPEC_DEVIATION: `RepositorioExcecoesOperacionais` ganhou `listar_por_execucao` (não listado
no `design.md`) — `montar` precisa ler, numa única consulta, tanto a exceção da execução
quanto a de cada mensagem, e só existia leitura por mensagem individual (4.2).
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_criticas import (
    RegistroAvaliacaoCritica,
)
from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_risco import (
    AvaliacaoRisco,
)
from central_preventiva.adaptadores.persistencia.repositorio_decisoes_humanas import (
    DecisaoHumana,
)
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RegistroElegibilidade,
)
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    EntregaSimulada,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    Marco,
    RegistroExcecaoOperacional,
    SnapshotExecucao,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    RegistroMensagem,
    VersaoMensagem,
)
from central_preventiva.adaptadores.persistencia.repositorio_visualizacoes_comunicado import (
    VisualizacaoComunicado,
)
from central_preventiva.dominio.estados_execucao import EstadoExecucao

ATOR_SISTEMA = "sistema"
ATOR_IA = "ia"
ATOR_SEGURADO = "segurado"

TIPO_EXECUCAO = "execucao"
TIPO_RISCO = "risco"
TIPO_ELEGIBILIDADE = "elegibilidade"
TIPO_GERACAO = "geracao"
TIPO_CRITICA = "critica"
TIPO_DECISAO_HUMANA = "decisao_humana"
TIPO_EXCECAO = "excecao"
TIPO_SIMULACAO = "simulacao"
TIPO_VISUALIZACAO = "visualizacao"


@dataclass(frozen=True, slots=True)
class MarcoLinhaDoTempo:
    """Um evento normalizado da cronologia, de qualquer uma das fontes agregadas."""

    timestamp: datetime
    ator: str
    acao: str
    resultado: str
    correlacao: str
    tipo: str
    mensagem_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class LinhaDoTempo:
    """A cronologia completa de uma execução, com a cadeia de correlação."""

    execucao_id: UUID
    estado: EstadoExecucao
    marcos: tuple[MarcoLinhaDoTempo, ...]
    execucao_origem_id: UUID | None
    retentativas: tuple[UUID, ...]


class _RepositorioExecucaoPreventiva(Protocol):
    """Porta mínima do agregado da execução (2.2/2.6/3.1/4.4)."""

    def buscar(self, execucao_id: UUID) -> SnapshotExecucao | None: ...

    def listar_marcos(self, execucao_id: UUID) -> list[Marco]: ...

    def listar_correlacionadas(self, execucao_origem_id: UUID) -> list[SnapshotExecucao]: ...


class _RepositorioAvaliacoesRisco(Protocol):
    """Porta mínima de `avaliacoes_risco` (2.3)."""

    def obter_por_execucao(self, execucao_id: UUID) -> AvaliacaoRisco | None: ...


class _RepositorioElegibilidades(Protocol):
    """Porta mínima do público elegível preservado pela execução (2.5)."""

    def listar_por_execucao(self, execucao_id: UUID) -> list[RegistroElegibilidade]: ...


class _RepositorioMensagens(Protocol):
    """Porta mínima de `mensagens`/`versoes_mensagem` (3.2)."""

    def listar_por_execucao(self, execucao_id: UUID) -> list[RegistroMensagem]: ...

    def listar_versoes(self, mensagem_id: UUID) -> list[VersaoMensagem]: ...


class _RepositorioAvaliacoesCriticas(Protocol):
    """Porta mínima de `avaliacoes_criticas` (3.3)."""

    def obter_por_versao(self, versao_mensagem_id: UUID) -> RegistroAvaliacaoCritica | None: ...


class _RepositorioDecisoesHumanas(Protocol):
    """Porta mínima de `decisoes_humanas` (3.5)."""

    def obter_por_mensagem(self, mensagem_id: UUID) -> list[DecisaoHumana]: ...


class _RepositorioExcecoesOperacionais(Protocol):
    """Porta mínima de `excecoes_operacionais` (2.2/3.4/4.4)."""

    def listar_por_execucao(self, execucao_id: UUID) -> list[RegistroExcecaoOperacional]: ...


class _RepositorioEntregasSimuladas(Protocol):
    """Porta mínima de `entregas_simuladas` (3.6)."""

    def listar_por_execucao(self, execucao_id: UUID) -> list[EntregaSimulada]: ...


class _RepositorioVisualizacoesComunicado(Protocol):
    """Porta mínima de `visualizacoes_comunicado` (4.3)."""

    def obter_por_entrega(self, entrega_simulada_id: UUID) -> VisualizacaoComunicado | None: ...


@dataclass(frozen=True, slots=True)
class PortasLinhaDoTempo:
    """Agrupa as portas de leitura de que a linha do tempo depende."""

    execucoes: _RepositorioExecucaoPreventiva
    avaliacoes_risco: _RepositorioAvaliacoesRisco
    elegibilidades: _RepositorioElegibilidades
    mensagens: _RepositorioMensagens
    avaliacoes_criticas: _RepositorioAvaliacoesCriticas
    decisoes: _RepositorioDecisoesHumanas
    excecoes: _RepositorioExcecoesOperacionais
    entregas: _RepositorioEntregasSimuladas
    visualizacoes: _RepositorioVisualizacoesComunicado


class ServicoLinhaDoTempo:
    """Agrega, normaliza e ordena todos os marcos de uma execução; busca por filtro."""

    def __init__(self, portas: PortasLinhaDoTempo) -> None:
        """Guarda as portas de leitura usadas pela linha do tempo."""

        self._portas = portas

    def montar(self, execucao_id: UUID) -> LinhaDoTempo | None:
        """Reconstrói a cronologia completa da execução, ou `None` se ela não existir."""

        snapshot = self._portas.execucoes.buscar(execucao_id)
        if snapshot is None:
            return None

        marcos: list[MarcoLinhaDoTempo] = []
        marcos.extend(self._marcos_execucao(execucao_id))
        marcos.extend(self._marco_risco(execucao_id))
        marcos.extend(self._marcos_elegibilidade(execucao_id))

        excecoes_por_mensagem: dict[UUID, list[RegistroExcecaoOperacional]] = defaultdict(list)
        for excecao in self._portas.excecoes.listar_por_execucao(execucao_id):
            if excecao.mensagem_id is None:
                marcos.append(
                    MarcoLinhaDoTempo(
                        timestamp=excecao.criado_em,
                        ator=ATOR_SISTEMA,
                        acao="exceção técnica da execução",
                        resultado=excecao.causa,
                        correlacao=str(execucao_id),
                        tipo=TIPO_EXCECAO,
                    )
                )
            else:
                excecoes_por_mensagem[excecao.mensagem_id].append(excecao)

        for registro_mensagem in self._portas.mensagens.listar_por_execucao(execucao_id):
            marcos.extend(self._marcos_mensagem(registro_mensagem))
            for excecao in excecoes_por_mensagem.get(registro_mensagem.id, []):
                marcos.append(
                    MarcoLinhaDoTempo(
                        timestamp=excecao.criado_em,
                        ator=ATOR_SISTEMA,
                        acao="exceção técnica da mensagem",
                        resultado=excecao.causa,
                        correlacao=str(registro_mensagem.id),
                        tipo=TIPO_EXCECAO,
                        mensagem_id=registro_mensagem.id,
                    )
                )

        marcos.extend(self._marcos_simulacao_e_visualizacao(execucao_id))

        return LinhaDoTempo(
            execucao_id=execucao_id,
            estado=snapshot.estado,
            marcos=tuple(sorted(marcos, key=lambda marco: marco.timestamp)),
            execucao_origem_id=snapshot.execucao_origem_id,
            retentativas=tuple(
                correlacionada.id
                for correlacionada in self._portas.execucoes.listar_correlacionadas(execucao_id)
            ),
        )

    def _marcos_execucao(self, execucao_id: UUID) -> list[MarcoLinhaDoTempo]:
        """Traduz os marcos de `marcos_execucao` (2.6) — a espinha dorsal da cronologia."""

        return [
            MarcoLinhaDoTempo(
                timestamp=marco.criado_em,
                ator=ATOR_SISTEMA,
                acao=marco.marco,
                resultado=marco.causa if marco.causa is not None else "concluído",
                correlacao=str(execucao_id),
                tipo=TIPO_EXECUCAO,
            )
            for marco in self._portas.execucoes.listar_marcos(execucao_id)
        ]

    def _marco_risco(self, execucao_id: UUID) -> list[MarcoLinhaDoTempo]:
        """Traduz a avaliação de risco/regra da execução (2.3), se existir."""

        avaliacao = self._portas.avaliacoes_risco.obter_por_execucao(execucao_id)
        if avaliacao is None:
            return []
        correlacao = str(avaliacao.regra_id) if avaliacao.regra_id is not None else str(
            avaliacao.evento_id
        )
        return [
            MarcoLinhaDoTempo(
                timestamp=avaliacao.criado_em,
                ator=ATOR_SISTEMA,
                acao="avaliação de risco e regra",
                resultado="relevante" if avaliacao.relevante else avaliacao.motivo,
                correlacao=correlacao,
                tipo=TIPO_RISCO,
            )
        ]

    def _marcos_elegibilidade(self, execucao_id: UUID) -> list[MarcoLinhaDoTempo]:
        """Traduz cada item do público elegível avaliado (2.5)."""

        return [
            MarcoLinhaDoTempo(
                timestamp=registro.criado_em,
                ator=ATOR_SISTEMA,
                acao="avaliação de elegibilidade",
                resultado="incluído" if registro.elegivel else "excluído",
                correlacao=str(registro.id),
                tipo=TIPO_ELEGIBILIDADE,
            )
            for registro in self._portas.elegibilidades.listar_por_execucao(execucao_id)
        ]

    def _marcos_mensagem(self, registro_mensagem: RegistroMensagem) -> list[MarcoLinhaDoTempo]:
        """Traduz gerações, críticas e decisões humanas de uma mensagem (3.2/3.3/3.5)."""

        marcos: list[MarcoLinhaDoTempo] = []
        decisoes_por_versao: dict[UUID, list[DecisaoHumana]] = defaultdict(list)
        for decisao in self._portas.decisoes.obter_por_mensagem(registro_mensagem.id):
            decisoes_por_versao[decisao.versao_mensagem_id].append(decisao)

        for versao in self._portas.mensagens.listar_versoes(registro_mensagem.id):
            marcos.append(
                MarcoLinhaDoTempo(
                    timestamp=versao.criado_em,
                    ator=ATOR_IA,
                    acao=f"geração — tentativa {versao.numero_tentativa}",
                    resultado="válida"
                    if versao.valida
                    else f"inválida ({versao.motivo_invalidez})",
                    correlacao=str(registro_mensagem.id),
                    tipo=TIPO_GERACAO,
                    mensagem_id=registro_mensagem.id,
                )
            )
            avaliacao_critica = self._portas.avaliacoes_criticas.obter_por_versao(versao.id)
            if avaliacao_critica is not None:
                marcos.append(
                    MarcoLinhaDoTempo(
                        timestamp=avaliacao_critica.criado_em,
                        ator=ATOR_IA,
                        acao="crítica",
                        resultado="aprovada"
                        if avaliacao_critica.avaliacao.aprovada
                        else "reprovada",
                        correlacao=str(registro_mensagem.id),
                        tipo=TIPO_CRITICA,
                        mensagem_id=registro_mensagem.id,
                    )
                )
            for decisao in decisoes_por_versao.get(versao.id, []):
                marcos.append(
                    MarcoLinhaDoTempo(
                        timestamp=decisao.criado_em,
                        ator=decisao.perfil_responsavel,
                        acao="decisão humana",
                        resultado=str(decisao.resultado),
                        correlacao=str(registro_mensagem.id),
                        tipo=TIPO_DECISAO_HUMANA,
                        mensagem_id=registro_mensagem.id,
                    )
                )
        return marcos

    def _marcos_simulacao_e_visualizacao(self, execucao_id: UUID) -> list[MarcoLinhaDoTempo]:
        """Traduz a entrega simulada e sua primeira visualização, se houver (3.6/4.3)."""

        marcos: list[MarcoLinhaDoTempo] = []
        for entrega in self._portas.entregas.listar_por_execucao(execucao_id):
            marcos.append(
                MarcoLinhaDoTempo(
                    timestamp=entrega.criado_em,
                    ator=ATOR_SISTEMA,
                    acao="simulação",
                    resultado="Enviada — simulação",
                    correlacao=str(entrega.mensagem_id),
                    tipo=TIPO_SIMULACAO,
                    mensagem_id=entrega.mensagem_id,
                )
            )
            visualizacao = self._portas.visualizacoes.obter_por_entrega(entrega.id)
            if visualizacao is not None:
                marcos.append(
                    MarcoLinhaDoTempo(
                        timestamp=visualizacao.visualizada_em,
                        ator=ATOR_SEGURADO,
                        acao="visualização",
                        resultado="visualizada no portal",
                        correlacao=str(entrega.mensagem_id),
                        tipo=TIPO_VISUALIZACAO,
                        mensagem_id=entrega.mensagem_id,
                    )
                )
        return marcos
