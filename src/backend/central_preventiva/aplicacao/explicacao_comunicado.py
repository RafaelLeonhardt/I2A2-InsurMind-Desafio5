"""Caso de uso da explicação acessível de um comunicado (EXPLICACAO-01..05).

`ServicoExplicacaoComunicado.obter` reusa por composição a mesma junção de dados de
`ServicoDetalheResultado` (4.2) — não duplica nenhuma consulta — trocando a verificação de
pertencimento de `execucao_id` (lado de Marina) para `segurado_id` (lado de Carlos), no mesmo
padrão de resolução de `ServicoVisualizacaoComunicado` (4.3): uma entrega inexistente e uma
entrega cuja mensagem pertence a outro segurado devolvem o mesmo `None` (AD-011).

A camada de tradução adicionada aqui rotula cada seção como `DETERMINISTICA` (evento e regra,
2.1-2.4) ou `AGENTE` (geração, crítica, decisões humanas, 3.2/3.3/3.5) e detecta lacuna de
proveniência por seção, sem nunca preencher um dado ausente com inferência (EXPLICACAO-05).
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_criticas import (
    RegistroAvaliacaoCritica,
)
from central_preventiva.adaptadores.persistencia.repositorio_contextos_agente import (
    RegistroContextoAgente,
)
from central_preventiva.adaptadores.persistencia.repositorio_decisoes_humanas import (
    DecisaoHumana,
)
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RegistroElegibilidade,
)
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    ApresentacaoSimulada,
    EntregaSimulada,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    SnapshotExecucao,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import RegistroMensagem
from central_preventiva.aplicacao.detalhe_resultado import DetalheResultado, VersaoDetalhada
from central_preventiva.dominio.decisao_humana import ResultadoDecisaoHumana
from central_preventiva.dominio.evento_meteorologico import EventoMeteorologico


class OrigemInformacao(StrEnum):
    """Classificação fixa por origem do dado — nunca uma heurística (design.md)."""

    DETERMINISTICA = "deterministica"
    AGENTE = "agente"


class StatusProcedencia(StrEnum):
    """O que a seção agêntica sabe sobre a completude da sua própria proveniência."""

    COMPLETA = "completa"
    PARCIAL = "parcial"
    EXCECAO = "excecao"


class OrigemRegeneracao(StrEnum):
    """Por que uma tentativa de geração além da primeira existe."""

    PRIMEIRA_TENTATIVA = "primeira_tentativa"
    AUTOMATICA = "automatica"
    HUMANA = "humana"


@dataclass(frozen=True, slots=True)
class SecaoEvento:
    """Evento e regra que originaram a mensagem — sempre `DETERMINISTICA` (EXPLICACAO-01)."""

    origem: OrigemInformacao
    evento: EventoMeteorologico | None
    regra_id: UUID
    regra_versao: int


@dataclass(frozen=True, slots=True)
class SecaoContexto:
    """Categorias de dado usadas e não usadas pelo agente redator (EXPLICACAO-03)."""

    categorias_usadas: tuple[str, ...]
    categorias_nao_usadas: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TentativaExplicada:
    """Uma tentativa de geração traduzida: redator, crítico, decisões humanas."""

    numero_tentativa: int
    origem_regeneracao: OrigemRegeneracao
    corpo: str
    assunto: str | None
    modelo_redator: str
    avaliacao_critica: RegistroAvaliacaoCritica | None
    decisoes_humanas: tuple[DecisaoHumana, ...]


@dataclass(frozen=True, slots=True)
class SecaoAgente:
    """Os papéis do agente redator e do agente crítico — sempre `AGENTE` (EXPLICACAO-02)."""

    origem: OrigemInformacao
    status: StatusProcedencia
    tentativas: tuple[TentativaExplicada, ...]
    causa_excecao: str | None


@dataclass(frozen=True, slots=True)
class ExplicacaoComunicado:
    """Tudo que Carlos vê em "Como esta mensagem foi criada": determinístico, agente,
    contexto minimizado e prévia fiel, com lacuna de proveniência nunca preenchida."""

    entrega_simulada_id: UUID
    mensagem_id: UUID
    execucao_id: UUID
    execucao_origem_id: UUID | None
    evento_e_regra: SecaoEvento
    contexto: SecaoContexto | None
    agente: SecaoAgente
    apresentacao_simulada: ApresentacaoSimulada | None


class _RepositorioEntregasSimuladas(Protocol):
    """Porta mínima de `entregas_simuladas` (3.6)."""

    def obter_por_id(self, entrega_simulada_id: UUID) -> EntregaSimulada | None: ...


class _RepositorioMensagens(Protocol):
    """Porta mínima de `mensagens` (3.2)."""

    def obter(self, mensagem_id: UUID) -> RegistroMensagem | None: ...


class _RepositorioElegibilidades(Protocol):
    """Porta mínima do público elegível preservado pela execução (2.5)."""

    def obter_por_id(self, id_registro: UUID) -> RegistroElegibilidade | None: ...


class _ServicoDetalheResultado(Protocol):
    """Porta mínima da junção completa de origem de uma mensagem (4.2), reusada por
    composição em vez de duplicada."""

    def obter(self, execucao_id: UUID, mensagem_id: UUID) -> DetalheResultado | None: ...


class _RepositorioContextosAgente(Protocol):
    """Porta mínima de `contextos_agente` (3.1)."""

    def obter_por_elegibilidade(self, elegibilidade_id: UUID) -> RegistroContextoAgente | None: ...


class _RepositorioExecucoes(Protocol):
    """Porta mínima de `execucao_preventiva` (2.6/4.4)."""

    def buscar(self, execucao_id: UUID) -> SnapshotExecucao | None: ...


@dataclass(frozen=True, slots=True)
class PortasExplicacaoComunicado:
    """Agrupa as portas de que a explicação do comunicado depende."""

    entregas: _RepositorioEntregasSimuladas
    mensagens: _RepositorioMensagens
    elegibilidades: _RepositorioElegibilidades
    detalhe: _ServicoDetalheResultado
    contextos: _RepositorioContextosAgente
    execucoes: _RepositorioExecucoes


def _origem_regeneracao(anterior: VersaoDetalhada | None) -> OrigemRegeneracao:
    """Deriva por que uma tentativa existe a partir do desfecho da tentativa anterior.

    Uma nova tentativa só é criada depois de uma reprovação crítica (ciclo automático de
    3.4) ou de uma decisão humana `regenerar` (3.5) sobre a tentativa anterior — os dois
    casos nunca se sobrepõem no fluxo real, então a decisão humana, quando presente, é
    sempre a causa mais específica.
    """

    if anterior is None:
        return OrigemRegeneracao.PRIMEIRA_TENTATIVA
    if any(
        decisao.resultado is ResultadoDecisaoHumana.REGENERAR
        for decisao in anterior.decisoes_humanas
    ):
        return OrigemRegeneracao.HUMANA
    return OrigemRegeneracao.AUTOMATICA


def _montar_secao_agente(detalhe: DetalheResultado) -> SecaoAgente:
    """Traduz as tentativas de geração, detectando exceção ou lacuna de proveniência.

    Uma mensagem em exceção (nunca chegou a `criticando`, ou esgotou tentativas) mostra
    `EXCECAO` com a causa sanitizada — nunca uma seção de crítica vazia parecendo
    incompleta por engano (Edge Case). Uma tentativa intermediária sem avaliação crítica
    persistida (dado de teste simulando lacuna) mostra `PARCIAL`, sem inferir o veredito
    que faltou (EXPLICACAO-05).
    """

    tentativas = tuple(
        TentativaExplicada(
            numero_tentativa=versao_detalhada.versao.numero_tentativa,
            origem_regeneracao=_origem_regeneracao(
                detalhe.versoes[indice - 1] if indice > 0 else None
            ),
            corpo=versao_detalhada.versao.conteudo.corpo,
            assunto=versao_detalhada.versao.conteudo.assunto,
            modelo_redator=versao_detalhada.versao.modelo,
            avaliacao_critica=versao_detalhada.avaliacao_critica,
            decisoes_humanas=versao_detalhada.decisoes_humanas,
        )
        for indice, versao_detalhada in enumerate(detalhe.versoes)
    )

    if detalhe.excecao is not None:
        return SecaoAgente(
            origem=OrigemInformacao.AGENTE,
            status=StatusProcedencia.EXCECAO,
            tentativas=tentativas,
            causa_excecao=detalhe.excecao.causa,
        )

    tentativas_intermediarias = detalhe.versoes[:-1]
    tem_lacuna = any(
        versao_detalhada.avaliacao_critica is None
        for versao_detalhada in tentativas_intermediarias
    )
    return SecaoAgente(
        origem=OrigemInformacao.AGENTE,
        status=StatusProcedencia.PARCIAL if tem_lacuna else StatusProcedencia.COMPLETA,
        tentativas=tentativas,
        causa_excecao=None,
    )


class ServicoExplicacaoComunicado:
    """Monta a explicação acessível de um comunicado, sem nenhuma escrita."""

    def __init__(self, portas: PortasExplicacaoComunicado) -> None:
        """Guarda as portas de leitura usadas pela explicação."""

        self._portas = portas

    def obter(
        self, segurado_id: UUID, entrega_simulada_id: UUID
    ) -> ExplicacaoComunicado | None:
        """Devolve a explicação completa, ou `None` se a entrega não existir ou não
        pertencer ao `segurado_id` informado — resposta idêntica nos dois casos, mesmo
        padrão de não-enumeração de 4.2/4.3 (AD-011)."""

        entrega = self._portas.entregas.obter_por_id(entrega_simulada_id)
        if entrega is None:
            return None
        mensagem = self._portas.mensagens.obter(entrega.mensagem_id)
        if mensagem is None:
            return None
        elegibilidade = self._portas.elegibilidades.obter_por_id(mensagem.elegibilidade_id)
        if elegibilidade is None or elegibilidade.segurado_id != segurado_id:
            return None

        detalhe = self._portas.detalhe.obter(mensagem.execucao_id, mensagem.id)
        assert detalhe is not None, (
            f"detalhe da mensagem {mensagem.id} não encontrado apesar de pertencer "
            f"à execução {mensagem.execucao_id}"
        )

        registro_contexto = self._portas.contextos.obter_por_elegibilidade(
            mensagem.elegibilidade_id
        )
        contexto = (
            None
            if registro_contexto is None
            else SecaoContexto(
                categorias_usadas=registro_contexto.categorias_usadas,
                categorias_nao_usadas=registro_contexto.categorias_nao_usadas,
            )
        )

        snapshot_execucao = self._portas.execucoes.buscar(mensagem.execucao_id)

        return ExplicacaoComunicado(
            entrega_simulada_id=entrega.id,
            mensagem_id=mensagem.id,
            execucao_id=mensagem.execucao_id,
            execucao_origem_id=(
                None if snapshot_execucao is None else snapshot_execucao.execucao_origem_id
            ),
            evento_e_regra=SecaoEvento(
                origem=OrigemInformacao.DETERMINISTICA,
                evento=detalhe.evento,
                regra_id=detalhe.regra_id,
                regra_versao=detalhe.regra_versao,
            ),
            contexto=contexto,
            agente=_montar_secao_agente(detalhe),
            apresentacao_simulada=detalhe.apresentacao_simulada,
        )
