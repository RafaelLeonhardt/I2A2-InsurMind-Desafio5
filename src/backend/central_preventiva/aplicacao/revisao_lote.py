"""Caso de uso da revisão humana do lote de comunicação (REVISAO-01..14).

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

`decidir_lote` aplica as decisões de Marina (REVISAO-05..14). Duas recusas diferentes, que
não se confundem:

- item **já decidido** (fora de `aguardando_revisao`) é recusado com motivo próprio e não
  impede as demais decisões válidas do mesmo envio (segundo Edge Case da spec) — a
  atomicidade vale para as decisões válidas enviadas, não obriga a re-decidir terminais;
- item com **`versao_esperada` desatualizada** é conflito real de concorrência otimista
  (AD-008): aborta a transação inteira, `409`, nenhuma decisão do envio é aplicada
  (REVISAO-12).

Depois de aplicar, o desfecho do agregado é recomputado do estado real das mensagens dentro
da mesma transação: alguma em `gerando`/`criticando` (regeneração humana ativa) leva a
`processando_mensagens`; alguma ainda em `aguardando_revisao` mantém o lote aberto; nenhuma
das duas e ao menos uma aprovada leva a `aguardando_confirmacao`; nenhuma aprovada conclui a
execução sem simulação (REVISAO-10, REVISAO-13, REVISAO-14).
"""

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, cast
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
    ConflitoVersaoMensagem,
    RegistroMensagem,
    VersaoMensagem,
)
from central_preventiva.aplicacao.portas_persistencia import (
    ConflitoIdempotencia,
    PortaIdempotencia,
)
from central_preventiva.dominio.avaliador_risco import Criterio
from central_preventiva.dominio.decisao_humana import (
    ResultadoDecisaoHumana,
    exige_justificativa,
)
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.estados_mensagem import EstadoMensagem, em_ciclo_de_conteudo
from central_preventiva.dominio.evento_meteorologico import EventoMeteorologico
from central_preventiva.dominio.validador_saida_canal import SaidaCanal

OPERACAO_DECISAO_LOTE = "decidir_lote_revisao"
"""Escopo da decisão em lote no armazenamento genérico de chaves idempotentes (AD-002)."""

STATUS_DECISAO_ACEITA = 200
"""Status registrado para a resposta de uma decisão em lote aplicada."""

MOTIVO_MENSAGEM_INEXISTENTE = "mensagem_inexistente"
"""Recusa de item que não existe ou não pertence a esta execução (AD-011)."""

MOTIVO_MENSAGEM_JA_DECIDIDA = "mensagem_ja_decidida"
"""Recusa de item fora de `aguardando_revisao` (segundo Edge Case da spec)."""

MOTIVO_LIMITE_DE_TENTATIVAS = "limite_de_tentativas_atingido"
"""Recusa de `regenerar` para mensagem que já consumiu as três tentativas (REVISAO-09)."""

MOTIVO_SEM_VERSAO_PARA_DECIDIR = "mensagem_sem_versao_para_decidir"
"""Recusa de item sem nenhuma versão persistida: não há o que decidir nem o que auditar."""

ESTADO_POR_RESULTADO: dict[ResultadoDecisaoHumana, EstadoMensagem] = {
    ResultadoDecisaoHumana.APROVAR: EstadoMensagem.APROVADA,
    ResultadoDecisaoHumana.REJEITAR: EstadoMensagem.REJEITADA,
    ResultadoDecisaoHumana.EXCLUIR: EstadoMensagem.EXCLUIDA,
}
"""Estado terminal de revisão de cada decisão que encerra a mensagem (AD-4, REVISAO-05).

`regenerar` não está aqui: ela não encerra a mensagem, reabre o ciclo de conteúdo em
`gerando` reusando o mesmo contador de tentativas do ciclo automático (REVISAO-08).
"""

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


@dataclass(frozen=True, slots=True)
class DecisaoRequisitada:
    """Uma decisão que Marina envia sobre uma mensagem específica (REVISAO-05)."""

    mensagem_id: UUID
    versao_esperada: int
    resultado: ResultadoDecisaoHumana
    justificativa: str | None = None


@dataclass(frozen=True, slots=True)
class DecisaoRecusada:
    """Um item excluído do envio, com o motivo estável da recusa (Edge Case 2)."""

    mensagem_id: UUID
    motivo: str


@dataclass(frozen=True, slots=True)
class ResultadoDecisaoLote:
    """Desfecho do envio: o que foi aplicado, o que foi recusado e onde o agregado parou."""

    execucao_id: UUID
    aplicadas: tuple[UUID, ...]
    recusadas: tuple[DecisaoRecusada, ...]
    estado: EstadoExecucao
    mensagens_aprovadas: tuple[UUID, ...]
    regeneracoes_ativas: tuple[UUID, ...]


class ExecucaoInexistente(RuntimeError):
    """Indica que o `execucao_id` informado não corresponde a nenhuma execução (AD-011)."""

    def __init__(self, execucao_id: UUID) -> None:
        """Identifica a execução ausente e monta a mensagem em português."""

        super().__init__(f"A execução '{execucao_id}' não existe.")
        self.execucao_id = execucao_id


class EstadoNaoRevisavel(RuntimeError):
    """Indica decisão enviada para uma execução fora de `aguardando_revisao`."""

    def __init__(self, execucao_id: UUID, estado: EstadoExecucao) -> None:
        """Identifica a execução e o estado que impede a decisão."""

        super().__init__(
            f"A execução '{execucao_id}' está em '{estado}' e não está em revisão."
        )
        self.execucao_id = execucao_id
        self.estado = estado


class JustificativaObrigatoria(RuntimeError):
    """Indica rejeição, exclusão ou regeneração enviada sem justificativa (REVISAO-06)."""

    def __init__(self, mensagem_id: UUID, resultado: ResultadoDecisaoHumana) -> None:
        """Identifica o item e a decisão que exigem justificativa."""

        super().__init__(
            f"A decisão '{resultado}' sobre a mensagem '{mensagem_id}' exige justificativa."
        )
        self.mensagem_id = mensagem_id
        self.resultado = resultado


class ConflitoVersaoDecisao(RuntimeError):
    """Indica `versao_esperada` desatualizada em ao menos um item do envio (REVISAO-12)."""

    def __init__(self, mensagens: tuple[UUID, ...]) -> None:
        """Identifica todos os itens conflitantes; nenhuma decisão do envio foi aplicada."""

        identificadores = ", ".join(str(item) for item in mensagens)
        super().__init__(
            f"As mensagens [{identificadores}] não estão na versão esperada. Nenhuma decisão "
            "do envio foi aplicada."
        )
        self.mensagens = mensagens


class _RepositorioExecucaoPreventiva(Protocol):
    """Porta mínima do agregado da execução (2.2)."""

    def buscar(self, execucao_id: UUID) -> SnapshotExecucao | None: ...

    def transicionar(
        self,
        execucao_id: UUID,
        versao_esperada: int,
        novo_estado: EstadoExecucao,
        conexao: Any = None,
    ) -> None: ...


class _RepositorioMensagens(Protocol):
    """Porta mínima de `mensagens`/`versoes_mensagem` (3.2/3.4)."""

    def listar_por_execucao(
        self, execucao_id: UUID, conexao: Any = None
    ) -> list[RegistroMensagem]: ...

    def listar_versoes(self, mensagem_id: UUID) -> list[VersaoMensagem]: ...

    def obter_versao_atual(self, mensagem_id: UUID) -> VersaoMensagem | None: ...

    def transicionar(
        self,
        mensagem_id: UUID,
        versao_esperada: int,
        novo_estado: EstadoMensagem,
        conexao: Any = None,
    ) -> None: ...

    def incrementar_tentativa(
        self, mensagem_id: UUID, versao_esperada: int, conexao: Any = None
    ) -> int: ...


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

    def salvar(
        self,
        mensagem_id: UUID,
        versao_mensagem_id: UUID,
        perfil: str,
        resultado: ResultadoDecisaoHumana,
        justificativa: str | None,
        conexao: Any = None,
    ) -> UUID: ...


class _Transacao(Protocol):
    """Porta da transação única do banco operacional (REVISAO-12)."""

    def executar[T](self, operacao: Callable[[Any], T]) -> T: ...


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
    idempotencia: PortaIdempotencia
    transacao: _Transacao
    acionar_regeneracao: Callable[[UUID], Awaitable[None]] | None = None
    """Retomada do ciclo automático das mensagens que a decisão humana devolveu a `gerando`.

    Reusa exatamente a reentrada de 3.4 (`ServicoGeracaoMensagens.retomar_mensagens_pendentes`
    → nó `gerar` do grafo), em vez de um segundo mecanismo de regeneração: a mensagem já está
    em `gerando` com a tentativa reservada, que é o marco durável de onde aquela retomada
    parte. Sem esse gatilho a mensagem regenerada ficaria parada até o próximo boot, e o
    agregado nunca voltaria a `aguardando_revisao` (REVISAO-10).
    """


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

    async def decidir_lote(
        self,
        execucao_id: UUID,
        decisoes: tuple[DecisaoRequisitada, ...],
        perfil: str,
        chave_idempotencia: str,
        hash_requisicao: str,
    ) -> ResultadoDecisaoLote:
        """Aplica as decisões válidas do envio numa única transação (REVISAO-12).

        Repetir a mesma chave idempotente devolve a resposta registrada sem reaplicar nada —
        é o que impede que um reenvio conte a tentativa de uma regeneração duas vezes
        (REVISAO-08, AD-002).
        """

        registrada = self._portas.idempotencia.buscar(
            chave_idempotencia, OPERACAO_DECISAO_LOTE
        )
        if registrada is not None:
            if registrada.hash_requisicao != hash_requisicao:
                raise ConflitoIdempotencia(
                    chave=chave_idempotencia, operacao=OPERACAO_DECISAO_LOTE
                )
            return _desserializar_decisao(registrada.corpo)

        resultado = self._decidir_agora(execucao_id, decisoes, perfil)
        self._portas.idempotencia.registrar(
            chave_idempotencia,
            OPERACAO_DECISAO_LOTE,
            hash_requisicao,
            STATUS_DECISAO_ACEITA,
            _serializar_decisao(resultado),
        )
        if resultado.regeneracoes_ativas and self._portas.acionar_regeneracao is not None:
            await self._portas.acionar_regeneracao(execucao_id)
        return resultado

    def _decidir_agora(
        self,
        execucao_id: UUID,
        decisoes: tuple[DecisaoRequisitada, ...],
        perfil: str,
    ) -> ResultadoDecisaoLote:
        """Valida, aplica e recomputa o agregado, já resolvida a idempotência do comando."""

        snapshot = self._portas.execucoes.buscar(execucao_id)
        if snapshot is None:
            raise ExecucaoInexistente(execucao_id)
        if snapshot.estado is not EstadoExecucao.AGUARDANDO_REVISAO:
            raise EstadoNaoRevisavel(execucao_id, snapshot.estado)

        for decisao in decisoes:
            if exige_justificativa(decisao.resultado) and not (
                decisao.justificativa or ""
            ).strip():
                raise JustificativaObrigatoria(decisao.mensagem_id, decisao.resultado)

        registros = {
            registro.id: registro
            for registro in self._portas.mensagens.listar_por_execucao(execucao_id)
        }
        aplicaveis: list[tuple[DecisaoRequisitada, UUID]] = []
        recusadas: list[DecisaoRecusada] = []
        for decisao in decisoes:
            motivo = self._recusa_de(decisao, registros)
            if motivo is not None:
                recusadas.append(DecisaoRecusada(decisao.mensagem_id, motivo))
                continue
            versao_atual = self._portas.mensagens.obter_versao_atual(decisao.mensagem_id)
            assert versao_atual is not None, "recusa de item sem versão já foi decidida acima"
            aplicaveis.append((decisao, versao_atual.id))

        estado_final = self._portas.transacao.executar(
            lambda conexao: self._aplicar(
                conexao, execucao_id, snapshot.versao, aplicaveis, perfil
            )
        )
        return ResultadoDecisaoLote(
            execucao_id=execucao_id,
            aplicadas=tuple(decisao.mensagem_id for decisao, _ in aplicaveis),
            recusadas=tuple(recusadas),
            estado=estado_final,
            mensagens_aprovadas=self._mensagens_aprovadas(execucao_id),
            regeneracoes_ativas=tuple(
                decisao.mensagem_id
                for decisao, _ in aplicaveis
                if decisao.resultado is ResultadoDecisaoHumana.REGENERAR
            ),
        )

    def _recusa_de(
        self, decisao: DecisaoRequisitada, registros: dict[UUID, RegistroMensagem]
    ) -> str | None:
        """Classifica a recusa por item, ou `None` quando a decisão é aplicável.

        Nenhuma destas recusas aborta o envio: elas retiram o item específico e deixam as
        demais decisões válidas seguirem (segundo Edge Case da spec). O conflito de
        `versao_esperada` é outra coisa, e é decidido dentro da transação.
        """

        registro = registros.get(decisao.mensagem_id)
        if registro is None:
            return MOTIVO_MENSAGEM_INEXISTENTE
        if registro.estado is not EstadoMensagem.AGUARDANDO_REVISAO:
            return MOTIVO_MENSAGEM_JA_DECIDIDA
        if (
            decisao.resultado is ResultadoDecisaoHumana.REGENERAR
            and registro.tentativa_atual >= LIMITE_TENTATIVAS_MENSAGEM
        ):
            return MOTIVO_LIMITE_DE_TENTATIVAS
        if self._portas.mensagens.obter_versao_atual(decisao.mensagem_id) is None:
            return MOTIVO_SEM_VERSAO_PARA_DECIDIR
        return None

    def _aplicar(
        self,
        conexao: Any,
        execucao_id: UUID,
        versao_execucao: int,
        aplicaveis: list[tuple[DecisaoRequisitada, UUID]],
        perfil: str,
    ) -> EstadoExecucao:
        """Grava decisões e transições na transação aberta e devolve o estado do agregado.

        Um conflito de `versao_esperada` em qualquer item levanta `ConflitoVersaoDecisao`
        depois de percorrer todos (para nomear todos os conflitantes), e a exceção faz a
        transação inteira voltar atrás: nenhuma decisão do envio fica aplicada (REVISAO-12).
        """

        conflitos: list[UUID] = []
        for decisao, versao_mensagem_id in aplicaveis:
            try:
                self._aplicar_item(conexao, decisao, versao_mensagem_id, perfil)
            except ConflitoVersaoMensagem:
                conflitos.append(decisao.mensagem_id)
        if conflitos:
            raise ConflitoVersaoDecisao(tuple(conflitos))

        alvo = _estado_agregado(
            self._portas.mensagens.listar_por_execucao(execucao_id, conexao)
        )
        if alvo is not EstadoExecucao.AGUARDANDO_REVISAO:
            self._portas.execucoes.transicionar(execucao_id, versao_execucao, alvo, conexao)
        return alvo

    def _aplicar_item(
        self,
        conexao: Any,
        decisao: DecisaoRequisitada,
        versao_mensagem_id: UUID,
        perfil: str,
    ) -> None:
        """Registra a decisão do item e move a mensagem para onde ela manda (REVISAO-05)."""

        self._portas.decisoes.salvar(
            decisao.mensagem_id,
            versao_mensagem_id,
            perfil,
            decisao.resultado,
            decisao.justificativa,
            conexao,
        )
        if decisao.resultado is ResultadoDecisaoHumana.REGENERAR:
            self._portas.mensagens.incrementar_tentativa(
                decisao.mensagem_id, decisao.versao_esperada, conexao
            )
            self._portas.mensagens.transicionar(
                decisao.mensagem_id,
                decisao.versao_esperada + 1,
                EstadoMensagem.GERANDO,
                conexao,
            )
            return
        self._portas.mensagens.transicionar(
            decisao.mensagem_id,
            decisao.versao_esperada,
            ESTADO_POR_RESULTADO[decisao.resultado],
            conexao,
        )

    def _mensagens_aprovadas(self, execucao_id: UUID) -> tuple[UUID, ...]:
        """Lista as mensagens aprovadas pelo crítico e por Marina (REVISAO-14).

        A dupla aprovação é verificada de fato, não presumida: o estado `aprovada` prova a
        decisão de Marina (só ela leva a mensagem até lá) e a avaliação da última versão
        prova a do crítico.
        """

        return tuple(
            registro.id
            for registro in self._portas.mensagens.listar_por_execucao(execucao_id)
            if registro.estado is EstadoMensagem.APROVADA
            and self._aprovada_pelo_critico(registro.id)
        )

    def _aprovada_pelo_critico(self, mensagem_id: UUID) -> bool:
        """Informa se a última versão da mensagem tem avaliação crítica aprovada."""

        versao = self._portas.mensagens.obter_versao_atual(mensagem_id)
        if versao is None:
            return False
        avaliacao = self._portas.avaliacoes.obter_por_versao(versao.id)
        return avaliacao is not None and avaliacao.avaliacao.aprovada

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


def _estado_agregado(registros: list[RegistroMensagem]) -> EstadoExecucao:
    """Decide onde a execução para, a partir do estado real de todas as mensagens.

    A ordem das perguntas é a do AD-6, e cada uma é recomputada do que está persistido,
    nunca de um contador acumulado:

    1. alguma mensagem em `gerando`/`criticando` — regeneração humana ativa — mantém a
       execução em `processando_mensagens` e proíbe qualquer conclusão (REVISAO-10);
    2. alguma mensagem ainda em `aguardando_revisao` mantém o lote aberto, porque nem toda
       mensagem revisável foi decidida (REVISAO-10);
    3. sem nenhuma das duas, o desfecho depende do resultado: ao menos uma aprovada leva a
       `aguardando_confirmacao` (REVISAO-14), nenhuma aprovada conclui a execução sem
       simulação (REVISAO-13).

    Itens já terminais de conteúdo (`falhou_conteudo`, `falhou_integracao_ia`) nunca bloqueiam
    a guarda: eles não são revisáveis (REVISAO-10, primeiro Edge Case da spec).
    """

    if any(em_ciclo_de_conteudo(registro.estado) for registro in registros):
        return EstadoExecucao.PROCESSANDO_MENSAGENS
    if any(registro.estado is EstadoMensagem.AGUARDANDO_REVISAO for registro in registros):
        return EstadoExecucao.AGUARDANDO_REVISAO
    if any(registro.estado is EstadoMensagem.APROVADA for registro in registros):
        return EstadoExecucao.AGUARDANDO_CONFIRMACAO
    return EstadoExecucao.CONCLUIDA


def _serializar_decisao(resultado: ResultadoDecisaoLote) -> str:
    """Serializa o desfecho do envio para o corpo guardado na chave idempotente."""

    return json.dumps(
        {
            "execucao_id": str(resultado.execucao_id),
            "aplicadas": [str(item) for item in resultado.aplicadas],
            "recusadas": [
                {"mensagem_id": str(item.mensagem_id), "motivo": item.motivo}
                for item in resultado.recusadas
            ],
            "estado": str(resultado.estado),
            "mensagens_aprovadas": [str(item) for item in resultado.mensagens_aprovadas],
            "regeneracoes_ativas": [str(item) for item in resultado.regeneracoes_ativas],
        }
    )


def _desserializar_decisao(corpo: str) -> ResultadoDecisaoLote:
    """Reconstrói o desfecho registrado de um envio, sem reaplicar nenhuma decisão."""

    dados = cast(dict[str, Any], json.loads(corpo))
    return ResultadoDecisaoLote(
        execucao_id=UUID(str(dados["execucao_id"])),
        aplicadas=tuple(UUID(str(item)) for item in dados["aplicadas"]),
        recusadas=tuple(
            DecisaoRecusada(UUID(str(item["mensagem_id"])), str(item["motivo"]))
            for item in dados["recusadas"]
        ),
        estado=EstadoExecucao(str(dados["estado"])),
        mensagens_aprovadas=tuple(UUID(str(item)) for item in dados["mensagens_aprovadas"]),
        regeneracoes_ativas=tuple(UUID(str(item)) for item in dados["regeneracoes_ativas"]),
    )


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
