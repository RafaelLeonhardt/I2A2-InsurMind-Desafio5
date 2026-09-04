"""Caso de uso da geração, da crítica e da regeneração automáticas do lote.

(GERAR-04..06, 10..12; CRIT-05..07; REGEN-01..06)

Para cada item incluído do público elegível, cria a mensagem e roda o grafo, que conduz o
ciclo completo do AD-4 — geração, crítica e, enquanto houver tentativa, regeneração. Nenhuma
ação humana por mensagem: `gerar_lote` recebe a execução inteira e percorre o público
(GERAR-04).

Este módulo implementa `CicloMensagem`, a porta que o grafo chama a cada marco durável. O
grafo decide *quando* cada marco acontece; `CicloPersistenteMensagem` decide *como* ele é
persistido. Os desfechos:

- saída válida: versão com `valida = true`, mensagem avança `gerando` → `criticando`;
- saída inválida: versão com `valida = false` e o motivo; a tentativa foi consumida e o ciclo
  regenera ou esgota (REGEN-01, AD-4);
- crítico aprova: avaliação persistida, mensagem avança para `aguardando_revisao` (CRIT-05) e
  o ciclo encerra imediatamente, sem consumir tentativa extra (REGEN-03);
- crítico reprova: avaliação persistida com os motivos categorizados; a tentativa foi
  consumida e o ciclo regenera ou esgota (CRIT-06, REGEN-01);
- saída do crítico não interpretável: nenhuma avaliação persistida, nunca aprovação (CRIT-07),
  e a tentativa é consumida como qualquer outra reprovação (AD-4);
- terceira reprovação: `falhou_conteudo` com `Exceção` correlacionada por `mensagem_id`, fora
  do lote simulável (REGEN-04);
- transporte esgotado (geração ou crítica, em qualquer tentativa): só a mensagem afetada vai a
  `falhou_integracao_ia`, com `Exceção` própria, e o restante do lote continua (REGEN-05/06,
  AD-8).

Reinvocar `gerar_lote` para uma execução já processada é no-op: a `UNIQUE
(elegibilidade_id, canal)` recusa a segunda criação, o item é pulado antes de qualquer
chamada à OpenAI e nenhuma mensagem é duplicada nem reavaliada (GERAR-11, GERAR-12, AD-010).
"""

from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

from central_preventiva.adaptadores.persistencia.repositorio_contextos_agente import (
    RegistroContextoAgente,
)
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RegistroElegibilidade,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    MensagemJaExiste,
    RegistroMensagem,
    VersaoMensagem,
)
from central_preventiva.aplicacao.grafos.geracao_mensagem import (
    DesfechoCritica,
    DesfechoGeracao,
    EstadoGrafoMensagem,
    ResultadoCritica,
    ResultadoGeracao,
)
from central_preventiva.dominio.avaliacao_critica import MotivoCritica
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.montador_contexto_agente import ContextoAgente
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

TENTATIVA_INICIAL = 1
"""Toda mensagem nova entra em `gerando` na primeira tentativa (AD-4)."""

IMPACTO_ITEM_SEM_MENSAGEM = (
    "Este item do público elegível não recebe mensagem nesta execução; os demais seguem "
    "normalmente."
)
"""Impacto operacional de um item que não pôde ser gerado (AD-8, exceção isolada)."""

IMPACTO_ITEM_FORA_DO_LOTE = (
    "Este item não integra o lote simulável; os demais seguem normalmente."
)
"""Impacto de um item que esgotou as três tentativas de conteúdo (REGEN-04)."""

MOTIVO_SEM_CATEGORIA = "sem_motivo_estruturado"
"""Usado na causa quando a reprovação final não trouxe nenhum motivo categorizado."""


def _causa_contexto_ausente(elegibilidade_id: UUID) -> str:
    """Descreve um item sem contexto mínimo montado (3.1), citando só o identificador."""

    return f"contexto_ausente:{elegibilidade_id}"


def _causa_canal_desconhecido(elegibilidade_id: UUID, canal: str) -> str:
    """Descreve um item cujo canal persistido não é um canal suportado."""

    return f"canal_desconhecido:{elegibilidade_id}:{canal}"


def _causa_integracao(elegibilidade_id: UUID, motivo: str | None) -> str:
    """Descreve a falha de integração de um item, com a causa já sanitizada pelo grafo."""

    return f"falha_integracao_ia:{elegibilidade_id}:{motivo}"


def _causa_integracao_critica(elegibilidade_id: UUID, motivo: str | None) -> str:
    """Descreve a falha de transporte da crítica, distinta da falha da geração."""

    return f"falha_integracao_ia_critica:{elegibilidade_id}:{motivo}"


def _causa_conteudo(elegibilidade_id: UUID, motivos: tuple[MotivoCritica, ...]) -> str:
    """Descreve o esgotamento das três tentativas citando as categorias reprovadas.

    Só as categorias fechadas entram na causa, nunca o texto gerado nem a justificativa
    livre: a `Exceção` é operacional e não carrega conteúdo (AD-10).
    """

    categorias = ",".join(motivo.categoria.value for motivo in motivos)
    return f"falhou_conteudo:{elegibilidade_id}:{categorias or MOTIVO_SEM_CATEGORIA}"


def _causa_falha_tecnica(elegibilidade_id: UUID, erro: BaseException) -> str:
    """Descreve uma falha técnica não prevista de um item, nomeando o tipo do erro."""

    return f"falha_tecnica_item:{elegibilidade_id}:{type(erro).__name__}: {erro}"


class _RepositorioElegibilidades(Protocol):
    """Porta mínima do público elegível preservado pela execução (2.5)."""

    def listar_por_execucao(self, execucao_id: UUID) -> list[RegistroElegibilidade]: ...


class _RepositorioContextosAgente(Protocol):
    """Porta mínima do contexto mínimo montado por item (3.1)."""

    def obter_por_elegibilidade(
        self, elegibilidade_id: UUID
    ) -> RegistroContextoAgente | None: ...


class _RepositorioMensagens(Protocol):
    """Porta mínima de `mensagens`/`versoes_mensagem` de que este caso de uso depende."""

    def criar(self, execucao_id: UUID, elegibilidade_id: UUID, canal: Canal) -> UUID: ...

    def obter(self, mensagem_id: UUID) -> RegistroMensagem | None: ...

    def salvar_versao(
        self,
        mensagem_id: UUID,
        numero_tentativa: int,
        conteudo: SaidaCanal,
        duracao_ms: float,
        modelo: str,
        versao_prompt: str,
        tokens_entrada: int | None,
        tokens_saida: int | None,
        valida: bool,
        motivo_invalidez: str | None,
    ) -> UUID: ...

    def transicionar(
        self, mensagem_id: UUID, versao_esperada: int, novo_estado: EstadoMensagem
    ) -> None: ...

    def incrementar_tentativa(self, mensagem_id: UUID, versao_esperada: int) -> int: ...

    def obter_versao_atual(self, mensagem_id: UUID) -> VersaoMensagem | None: ...


class _RepositorioAvaliacoesCriticas(Protocol):
    """Porta mínima de `avaliacoes_criticas` de que este caso de uso depende."""

    def salvar(
        self,
        versao_mensagem_id: UUID,
        aprovada: bool,
        motivos: tuple[MotivoCritica, ...],
        modelo: str,
        duracao_ms: float,
    ) -> UUID: ...


class _RepositorioExcecoesOperacionais(Protocol):
    """Porta mínima de registro de `Exceção` operacional sanitizada."""

    def registrar(
        self,
        execucao_id: UUID,
        causa: str,
        tentativas: int,
        impacto: str,
        mensagem_id: UUID | None = None,
    ) -> None: ...


class _GrafoGeracao(Protocol):
    """Porta mínima do grafo compilado de geração de uma mensagem."""

    async def ainvoke(self, input: EstadoGrafoMensagem) -> Any: ...  # noqa: A002


@dataclass(frozen=True, slots=True)
class PortasGeracaoMensagens:
    """Agrupa as portas de que a geração do lote depende."""

    elegibilidades: _RepositorioElegibilidades
    contextos: _RepositorioContextosAgente
    mensagens: _RepositorioMensagens
    avaliacoes: _RepositorioAvaliacoesCriticas
    excecoes: _RepositorioExcecoesOperacionais
    grafo: _GrafoGeracao
    versao_prompt: str


class CicloPersistenteMensagem:
    """Persiste cada marco durável do ciclo de uma mensagem, a pedido do grafo.

    Toda operação relê o estado atual da mensagem antes de escrever, e é essa releitura que
    fornece a `versao_esperada` da checagem otimista (AD-008). É também o que torna a
    retomada de 3.4 correta: um marco já gravado antes do reinício continua sendo o ponto de
    partida, sem nenhuma versão de tentativa em memória.
    """

    def __init__(self, portas: PortasGeracaoMensagens) -> None:
        """Guarda as portas de persistência compartilhadas com o caso de uso."""

        self._portas = portas

    def registrar_geracao(
        self, mensagem_id: UUID, tentativa: int, resultado: ResultadoGeracao
    ) -> None:
        """Persiste a versão desta tentativa, ou fecha o item em `falhou_integracao_ia`."""

        registro = self._obter(mensagem_id)
        if resultado.desfecho is DesfechoGeracao.FALHOU_INTEGRACAO_IA:
            self._registrar_excecao(
                registro,
                _causa_integracao(registro.elegibilidade_id, resultado.motivo),
                IMPACTO_ITEM_SEM_MENSAGEM,
            )
            self._portas.mensagens.transicionar(
                mensagem_id, registro.versao, EstadoMensagem.FALHOU_INTEGRACAO_IA
            )
            return

        self._portas.mensagens.salvar_versao(
            mensagem_id=mensagem_id,
            numero_tentativa=tentativa,
            conteudo=resultado.saida if resultado.saida is not None else SaidaCanal(corpo=""),
            duracao_ms=resultado.duracao_ms,
            modelo=resultado.modelo,
            versao_prompt=self._portas.versao_prompt,
            tokens_entrada=resultado.tokens_entrada,
            tokens_saida=resultado.tokens_saida,
            valida=resultado.desfecho is DesfechoGeracao.VALIDA,
            motivo_invalidez=resultado.motivo,
        )
        if resultado.desfecho is DesfechoGeracao.VALIDA:
            self._portas.mensagens.transicionar(
                mensagem_id, registro.versao, EstadoMensagem.CRITICANDO
            )

    def registrar_critica(
        self, mensagem_id: UUID, tentativa: int, critica: ResultadoCritica
    ) -> None:
        """Persiste a avaliação desta tentativa e transiciona conforme a decisão.

        Uma saída do crítico não interpretável não persiste avaliação nem transiciona nada
        (CRIT-07). Uma reprovação persiste os motivos e também não transiciona: quem decide
        entre regenerar e esgotar é o grafo. Só a aprovação avança para `aguardando_revisao`
        (CRIT-05, REGEN-03).
        """

        registro = self._obter(mensagem_id)
        if critica.desfecho is DesfechoCritica.FALHOU_INTEGRACAO_IA:
            self._registrar_excecao(
                registro,
                _causa_integracao_critica(registro.elegibilidade_id, critica.causa),
                IMPACTO_ITEM_SEM_MENSAGEM,
            )
            self._portas.mensagens.transicionar(
                mensagem_id, registro.versao, EstadoMensagem.FALHOU_INTEGRACAO_IA
            )
            return

        if critica.desfecho is DesfechoCritica.SAIDA_INVALIDA:
            return

        versao = self._portas.mensagens.obter_versao_atual(mensagem_id)
        assert versao is not None, f"tentativa {tentativa} da mensagem {mensagem_id} sem versão"
        self._portas.avaliacoes.salvar(
            versao_mensagem_id=versao.id,
            aprovada=critica.desfecho is DesfechoCritica.APROVADA,
            motivos=critica.motivos,
            modelo=critica.modelo,
            duracao_ms=critica.duracao_ms,
        )

        if critica.desfecho is DesfechoCritica.APROVADA:
            self._portas.mensagens.transicionar(
                mensagem_id, registro.versao, EstadoMensagem.AGUARDANDO_REVISAO
            )

    def preparar_regeneracao(self, mensagem_id: UUID) -> int:
        """Reserva a próxima tentativa e devolve a mensagem a `gerando` (REGEN-01).

        O incremento vem antes da transição, e é atômico: reservar a tentativa é a
        pré-condição de reentrar em `gerando` que o AD-4 exige.
        """

        registro = self._obter(mensagem_id)
        proxima = self._portas.mensagens.incrementar_tentativa(mensagem_id, registro.versao)
        reservado = self._obter(mensagem_id)
        self._portas.mensagens.transicionar(
            mensagem_id, reservado.versao, EstadoMensagem.GERANDO
        )
        return proxima

    def esgotar_tentativas(
        self, mensagem_id: UUID, tentativa: int, motivos: tuple[MotivoCritica, ...]
    ) -> None:
        """Fecha a mensagem em `falhou_conteudo` com a `Exceção` própria (REGEN-04)."""

        registro = self._obter(mensagem_id)
        self._registrar_excecao(
            registro,
            _causa_conteudo(registro.elegibilidade_id, motivos),
            IMPACTO_ITEM_FORA_DO_LOTE,
            tentativas=tentativa,
        )
        self._portas.mensagens.transicionar(
            mensagem_id, registro.versao, EstadoMensagem.FALHOU_CONTEUDO
        )

    def _obter(self, mensagem_id: UUID) -> RegistroMensagem:
        """Relê a mensagem persistida, fonte da versão esperada de toda transição."""

        registro = self._portas.mensagens.obter(mensagem_id)
        assert registro is not None, f"mensagem {mensagem_id} não encontrada"
        return registro

    def _registrar_excecao(
        self,
        registro: RegistroMensagem,
        causa: str,
        impacto: str,
        tentativas: int = 1,
    ) -> None:
        """Registra a exceção correlacionada à execução e à mensagem específica."""

        self._portas.excecoes.registrar(
            registro.execucao_id, causa, tentativas, impacto, registro.id
        )


class ServicoGeracaoMensagens:
    """Gera automaticamente uma mensagem por item elegível da execução."""

    def __init__(self, portas: PortasGeracaoMensagens) -> None:
        """Guarda as portas e monta o ciclo persistente que o grafo vai chamar."""

        self._portas = portas
        self._ciclo = CicloPersistenteMensagem(portas)

    async def gerar_lote(self, execucao_id: UUID) -> None:
        """Percorre o público elegível da execução e gera a mensagem de cada item.

        Sequencial por decisão de escopo (uma chamada à OpenAI por vez): o conjunto
        sintético da demonstração é pequeno e paralelizar não é exigido por nenhum AC.
        Uma falha isolada de um item nunca interrompe os demais (REGEN-06, AD-8).
        """

        for registro in self._portas.elegibilidades.listar_por_execucao(execucao_id):
            if not registro.elegivel:
                continue
            await self._gerar_item_isolado(execucao_id, registro)

    async def _gerar_item_isolado(
        self, execucao_id: UUID, registro: RegistroElegibilidade
    ) -> None:
        """Roda a geração de um item convertendo qualquer falha técnica em exceção dele.

        Mesmo padrão de `GerenciadorExecucoes._processar_coleta_e_continuar` (RUNNER-11):
        uma falha de infraestrutura fora do caminho do grafo (conflito de versão, falha de
        conexão do banco) vira uma `Exceção` operacional registrada em vez de abortar o
        restante do lote em silêncio. `gerar_lote` roda como task desacoplada, então uma
        exceção que escapasse daqui não teria quem a observasse.
        """

        try:
            await self._gerar_item(execucao_id, registro)
        except Exception as erro:  # noqa: BLE001 - falha técnica isolada no item (AD-8)
            self._registrar_excecao(execucao_id, _causa_falha_tecnica(registro.id, erro))

    async def _gerar_item(self, execucao_id: UUID, registro: RegistroElegibilidade) -> None:
        """Cria a mensagem do item e roda o ciclo completo do grafo sobre ela."""

        canal = self._canal_de(execucao_id, registro)
        if canal is None:
            return

        contexto = self._portas.contextos.obter_por_elegibilidade(registro.id)
        if contexto is None:
            self._registrar_excecao(execucao_id, _causa_contexto_ausente(registro.id))
            return

        try:
            mensagem_id = self._portas.mensagens.criar(execucao_id, registro.id, canal)
        except MensagemJaExiste:
            return

        await self._executar_grafo(mensagem_id, contexto.contexto, canal)

    async def _executar_grafo(
        self, mensagem_id: UUID, contexto: ContextoAgente, canal: Canal
    ) -> None:
        """Roda o grafo de uma mensagem do início do ciclo até um desfecho terminal.

        Nada volta do grafo para ser persistido depois: cada marco já foi gravado pelo
        `CicloPersistenteMensagem` no instante em que aconteceu (REGEN-08).
        """

        estado: EstadoGrafoMensagem = {
            "contexto": contexto,
            "canal": canal,
            "tentativa": TENTATIVA_INICIAL,
            "mensagem_id": mensagem_id,
            "ciclo": self._ciclo,
        }
        await self._portas.grafo.ainvoke(estado)

    def _canal_de(self, execucao_id: UUID, registro: RegistroElegibilidade) -> Canal | None:
        """Resolve o canal do snapshot, isolando um canal não suportado como exceção."""

        try:
            return Canal(registro.canal)
        except ValueError:
            self._registrar_excecao(
                execucao_id, _causa_canal_desconhecido(registro.id, registro.canal)
            )
            return None

    def _registrar_excecao(self, execucao_id: UUID, causa: str) -> None:
        """Registra a exceção de um item que nunca chegou a ter mensagem criada.

        Sem mensagem, não há `mensagem_id` a correlacionar: a exceção fica escopada só à
        execução, como as de 2.2.
        """

        self._portas.excecoes.registrar(execucao_id, causa, 1, IMPACTO_ITEM_SEM_MENSAGEM)
