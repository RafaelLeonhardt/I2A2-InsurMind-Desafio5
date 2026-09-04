"""Caso de uso da revisão humana do lote de comunicação (REVISAO-01..04).

Monta o lote que Marina revisa: cabeçalho da execução (evento, regra, público, distribuição
por canal, aprovações agênticas e exceções) e um item por mensagem, com destinatário
sintético, conteúdo de cada versão, verificação determinística, avaliação crítica, dados de
origem e proveniência já separados por categoria (REVISAO-03/04 — a separação visual é da
interface, mas ela só é possível porque o lote já chega agrupado assim).

A ordenação põe o que exige atenção primeiro (REVISAO-02): exceções de conteúdo ou de
integração, depois itens com histórico de reprovação em alguma tentativa, depois aprovações
limpas do crítico e, por último, itens que não pedem nada de Marina (já decididos, ou ainda
no ciclo automático).

O lote não lê `excecoes_operacionais`. Um item em exceção é identificado pelo próprio estado
da mensagem (`falhou_conteudo`/`falhou_integracao_ia`), e o porquê já está em dado de revisão:
o `motivo_invalidez` da versão recusada e os motivos categorizados da avaliação crítica. A
tabela de exceções guarda a mesma informação em forma operacional, para a trilha da execução
(2.2/3.4); duplicá-la aqui não acrescentaria nada ao que Marina precisa para decidir.

A transição agregada que *abre* este lote (REVISAO-01: a execução entra em
`aguardando_revisao` quando toda mensagem alcança um terminal de conteúdo) não mora aqui:
ela é disparada por `ServicoGeracaoMensagens.abrir_revisao_se_lote_completo`, o único ponto
por onde passa todo desfecho terminal de mensagem. Veja o `SPEC_DEVIATION` no topo de
`aplicacao/geracao_mensagens.py`.
"""

from dataclasses import dataclass
from datetime import datetime
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
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    SnapshotExecucao,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    LIMITE_TENTATIVAS_MENSAGEM,
    RegistroMensagem,
    VersaoMensagem,
)
from central_preventiva.dominio.avaliador_risco import Criterio
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.evento_meteorologico import EventoMeteorologico
from central_preventiva.dominio.validador_saida_canal import SaidaCanal

PRIORIDADE_EXCECAO = 0
"""Item que não produziu conteúdo utilizável: exige atenção antes de todos (REVISAO-02)."""

PRIORIDADE_REPROVACAO_HISTORICA = 1
"""Item aguardando revisão que foi reprovado em alguma tentativa anterior (REVISAO-02)."""

PRIORIDADE_APROVACAO_LIMPA = 2
"""Item aguardando revisão aprovado pelo crítico sem nenhuma reprovação no caminho."""

PRIORIDADE_SEM_PENDENCIA = 3
"""Item que não pede decisão agora: já decidido por Marina, ou ainda no ciclo automático."""

ESTADOS_EM_EXCECAO = frozenset(
    {EstadoMensagem.FALHOU_CONTEUDO, EstadoMensagem.FALHOU_INTEGRACAO_IA}
)
"""Os dois terminais de conteúdo que são exceção, e não aprovação agêntica (REVISAO-01)."""


@dataclass(frozen=True, slots=True)
class DestinatarioSintetico:
    """Quem receberia a mensagem, como o snapshot da elegibilidade registrou (REVISAO-03)."""

    elegibilidade_id: UUID
    segurado_id: UUID
    nome_segurado: str
    apolice_id: UUID
    codigo_ibge_area: str
    canal: str


@dataclass(frozen=True, slots=True)
class OrigemItem:
    """Os dados de origem que produziram a mensagem: evento, regra e critérios (REVISAO-03)."""

    evento_id: UUID
    regra_id: UUID
    regra_versao: int
    criterios: tuple[Criterio, ...]
    justificativa: str


@dataclass(frozen=True, slots=True)
class ProvenienciaItem:
    """Categorias de dado que entraram e que ficaram fora do contexto do agente (3.1)."""

    categorias_usadas: tuple[str, ...]
    categorias_nao_usadas: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VersaoRevisada:
    """Uma tentativa: conteúdo, verificação determinística e avaliação crítica (REVISAO-03)."""

    id: UUID
    numero_tentativa: int
    conteudo: SaidaCanal
    valida: bool
    motivo_invalidez: str | None
    modelo: str
    versao_prompt: str
    duracao_ms: float
    tokens_entrada: int | None
    tokens_saida: int | None
    criado_em: datetime
    avaliacao: RegistroAvaliacaoCritica | None


@dataclass(frozen=True, slots=True)
class ItemLoteRevisao:
    """Uma mensagem do lote, com tudo que a decisão humana precisa (REVISAO-03)."""

    mensagem_id: UUID
    canal: str
    estado: EstadoMensagem
    tentativa_atual: int
    limite_tentativas: int
    versao: int
    destinatario: DestinatarioSintetico
    origem: OrigemItem
    proveniencia: ProvenienciaItem | None
    versoes: tuple[VersaoRevisada, ...]
    decisoes: tuple[DecisaoHumana, ...]
    aprovada_pelo_critico: bool
    reprovacao_historica: bool
    em_excecao: bool
    decidivel: bool
    pode_regenerar: bool
    prioridade: int


@dataclass(frozen=True, slots=True)
class LoteRevisao:
    """O lote inteiro de uma execução, com o cabeçalho e os itens ordenados (REVISAO-01)."""

    execucao_id: UUID
    estado: EstadoExecucao
    evento: EventoMeteorologico | None
    regra_id: UUID | None
    regra_versao: int | None
    total_publico_incluido: int
    distribuicao_por_canal: tuple[tuple[str, int], ...]
    aprovacoes_agenticas: int
    itens_em_excecao: int
    itens: tuple[ItemLoteRevisao, ...]


class _RepositorioExecucaoPreventiva(Protocol):
    """Porta mínima do agregado da execução (2.2)."""

    def buscar(self, execucao_id: UUID) -> SnapshotExecucao | None: ...


class _RepositorioMensagens(Protocol):
    """Porta mínima de `mensagens`/`versoes_mensagem` (3.2/3.4)."""

    def listar_por_execucao(self, execucao_id: UUID) -> list[RegistroMensagem]: ...

    def listar_versoes(self, mensagem_id: UUID) -> list[VersaoMensagem]: ...


class _RepositorioElegibilidades(Protocol):
    """Porta mínima do público elegível preservado pela execução (2.5)."""

    def listar_por_execucao(self, execucao_id: UUID) -> list[RegistroElegibilidade]: ...


class _RepositorioAvaliacoesCriticas(Protocol):
    """Porta mínima de `avaliacoes_criticas` (3.3)."""

    def obter_por_versao(
        self, versao_mensagem_id: UUID
    ) -> RegistroAvaliacaoCritica | None: ...


class _RepositorioDecisoesHumanas(Protocol):
    """Porta mínima de `decisoes_humanas` (T2)."""

    def obter_por_mensagem(self, mensagem_id: UUID) -> list[DecisaoHumana]: ...


class _RepositorioContextosAgente(Protocol):
    """Porta mínima do contexto mínimo montado por item (3.1)."""

    def obter_por_elegibilidade(
        self, elegibilidade_id: UUID
    ) -> RegistroContextoAgente | None: ...


class _RepositorioEventos(Protocol):
    """Porta mínima do evento meteorológico que originou a execução (2.2)."""

    def buscar_por_id(self, id: UUID) -> EventoMeteorologico | None: ...  # noqa: A002


@dataclass(frozen=True, slots=True)
class PortasRevisaoLote:
    """Agrupa as portas de que a revisão do lote depende."""

    execucoes: _RepositorioExecucaoPreventiva
    mensagens: _RepositorioMensagens
    elegibilidades: _RepositorioElegibilidades
    avaliacoes: _RepositorioAvaliacoesCriticas
    decisoes: _RepositorioDecisoesHumanas
    contextos: _RepositorioContextosAgente
    eventos: _RepositorioEventos


class ServicoRevisaoLote:
    """Monta o lote de revisão e aplica as decisões humanas sobre ele."""

    def __init__(self, portas: PortasRevisaoLote) -> None:
        """Guarda as portas de leitura e escrita usadas pela revisão."""

        self._portas = portas

    def obter_lote(self, execucao_id: UUID) -> LoteRevisao | None:
        """Monta o lote da execução com os itens de atenção primeiro, ou `None` se não existir.

        A resposta é idêntica para execução inexistente e para execução de outro escopo
        (AD-011): quem traduz `None` em `404` é o roteador.
        """

        snapshot = self._portas.execucoes.buscar(execucao_id)
        if snapshot is None:
            return None

        elegibilidades = self._portas.elegibilidades.listar_por_execucao(execucao_id)
        por_elegibilidade = {registro.id: registro for registro in elegibilidades}
        mensagens = self._portas.mensagens.listar_por_execucao(execucao_id)
        itens = tuple(
            sorted(
                (self._item(registro, por_elegibilidade) for registro in mensagens),
                key=lambda item: item.prioridade,
            )
        )
        return LoteRevisao(
            execucao_id=execucao_id,
            estado=snapshot.estado,
            evento=self._evento_de(elegibilidades),
            regra_id=elegibilidades[0].regra_id if elegibilidades else None,
            regra_versao=elegibilidades[0].regra_versao if elegibilidades else None,
            total_publico_incluido=sum(1 for item in elegibilidades if item.elegivel),
            distribuicao_por_canal=_distribuicao_por_canal(itens),
            aprovacoes_agenticas=sum(1 for item in itens if item.aprovada_pelo_critico),
            itens_em_excecao=sum(1 for item in itens if item.em_excecao),
            itens=itens,
        )

    def _item(
        self,
        registro: RegistroMensagem,
        por_elegibilidade: dict[UUID, RegistroElegibilidade],
    ) -> ItemLoteRevisao:
        """Monta um item do lote a partir da mensagem e de todo o contexto dela."""

        elegibilidade = por_elegibilidade.get(registro.elegibilidade_id)
        assert elegibilidade is not None, (
            f"mensagem {registro.id} sem elegibilidade {registro.elegibilidade_id}"
        )
        versoes = tuple(
            self._versao(versao)
            for versao in self._portas.mensagens.listar_versoes(registro.id)
        )
        contexto = self._portas.contextos.obter_por_elegibilidade(registro.elegibilidade_id)
        aprovada_pelo_critico = _aprovada_pelo_critico(versoes)
        reprovacao_historica = _reprovacao_historica(versoes)
        em_excecao = registro.estado in ESTADOS_EM_EXCECAO
        decidivel = registro.estado is EstadoMensagem.AGUARDANDO_REVISAO
        return ItemLoteRevisao(
            mensagem_id=registro.id,
            canal=str(registro.canal),
            estado=registro.estado,
            tentativa_atual=registro.tentativa_atual,
            limite_tentativas=LIMITE_TENTATIVAS_MENSAGEM,
            versao=registro.versao,
            destinatario=DestinatarioSintetico(
                elegibilidade_id=elegibilidade.id,
                segurado_id=elegibilidade.segurado_id,
                nome_segurado=elegibilidade.nome_segurado,
                apolice_id=elegibilidade.apolice_id,
                codigo_ibge_area=elegibilidade.codigo_ibge_area,
                canal=elegibilidade.canal,
            ),
            origem=OrigemItem(
                evento_id=elegibilidade.evento_id,
                regra_id=elegibilidade.regra_id,
                regra_versao=elegibilidade.regra_versao,
                criterios=elegibilidade.criterios,
                justificativa=elegibilidade.justificativa,
            ),
            proveniencia=None
            if contexto is None
            else ProvenienciaItem(
                categorias_usadas=contexto.categorias_usadas,
                categorias_nao_usadas=contexto.categorias_nao_usadas,
            ),
            versoes=versoes,
            decisoes=tuple(self._portas.decisoes.obter_por_mensagem(registro.id)),
            aprovada_pelo_critico=aprovada_pelo_critico,
            reprovacao_historica=reprovacao_historica,
            em_excecao=em_excecao,
            decidivel=decidivel,
            pode_regenerar=decidivel
            and registro.tentativa_atual < LIMITE_TENTATIVAS_MENSAGEM,
            prioridade=_prioridade(registro.estado, em_excecao, reprovacao_historica),
        )

    def _versao(self, versao: VersaoMensagem) -> VersaoRevisada:
        """Junta a tentativa persistida à avaliação crítica dela, quando houver."""

        return VersaoRevisada(
            id=versao.id,
            numero_tentativa=versao.numero_tentativa,
            conteudo=versao.conteudo,
            valida=versao.valida,
            motivo_invalidez=versao.motivo_invalidez,
            modelo=versao.modelo,
            versao_prompt=versao.versao_prompt,
            duracao_ms=versao.duracao_ms,
            tokens_entrada=versao.tokens_entrada,
            tokens_saida=versao.tokens_saida,
            criado_em=versao.criado_em,
            avaliacao=self._portas.avaliacoes.obter_por_versao(versao.id),
        )

    def _evento_de(
        self, elegibilidades: list[RegistroElegibilidade]
    ) -> EventoMeteorologico | None:
        """Resolve o evento da execução: todo item do público aponta para o mesmo."""

        if not elegibilidades:
            return None
        return self._portas.eventos.buscar_por_id(elegibilidades[0].evento_id)


def _aprovada_pelo_critico(versoes: tuple[VersaoRevisada, ...]) -> bool:
    """Informa se a última tentativa foi aprovada pelo agente crítico (REVISAO-01).

    É a aprovação agêntica que o cabeçalho do lote conta, e a metade agêntica da aprovação
    dupla exigida pelo REVISAO-14 — a outra metade é a decisão de Marina.
    """

    if not versoes:
        return False
    ultima = versoes[-1]
    return ultima.avaliacao is not None and ultima.avaliacao.avaliacao.aprovada


def _reprovacao_historica(versoes: tuple[VersaoRevisada, ...]) -> bool:
    """Informa se alguma tentativa foi reprovada, ainda que a final tenha sido aprovada.

    Conta tanto a reprovação do crítico quanto a recusa determinística do validador de canal
    (3.2): as duas são histórico de reprovação e merecem a mesma checagem extra de Marina
    (REVISAO-02).
    """

    return any(
        not versao.valida
        or (versao.avaliacao is not None and not versao.avaliacao.avaliacao.aprovada)
        for versao in versoes
    )


def _prioridade(
    estado: EstadoMensagem, em_excecao: bool, reprovacao_historica: bool
) -> int:
    """Classifica o item na ordem de atenção do lote (REVISAO-02)."""

    if em_excecao:
        return PRIORIDADE_EXCECAO
    if estado is not EstadoMensagem.AGUARDANDO_REVISAO:
        return PRIORIDADE_SEM_PENDENCIA
    return (
        PRIORIDADE_REPROVACAO_HISTORICA
        if reprovacao_historica
        else PRIORIDADE_APROVACAO_LIMPA
    )


def _distribuicao_por_canal(itens: tuple[ItemLoteRevisao, ...]) -> tuple[tuple[str, int], ...]:
    """Conta as mensagens do lote por canal, em ordem alfabética estável (REVISAO-01)."""

    contagem: dict[str, int] = {}
    for item in itens:
        contagem[item.canal] = contagem.get(item.canal, 0) + 1
    return tuple(sorted(contagem.items()))
