"""Caso de uso da simulação local do lote confirmado (SIMUL-04..10).

Nenhum conector real de WhatsApp, e-mail ou SMS existe neste módulo, nem é alcançável a
partir dele: a "apresentação simulada" é uma cópia do conteúdo já aprovado da mensagem (3.2),
e a única escrita externa é a de `entregas_simuladas` (ADR-0009/0013, SIMUL-05).

`confirmar` executa, nesta ordem:

1. reconhecimento explícito da natureza simulada, cobrado no backend como defesa em
   profundidade — o bloqueio do botão é do frontend, mas não é a única guarda (SIMUL-03);
2. reclamação atômica do agregado: `aguardando_confirmacao` → `simulando` sob a versão
   esperada (AD-008). É a instrução que resolve duas confirmações concorrentes: só uma
   vence o `UPDATE ... WHERE versao = ?`, a outra recebe conflito e não reclama nada
   (SIMUL-08);
3. transação 1: uma entrega simulada por mensagem aprovada e a transição de cada mensagem
   para `simulada_entregue`, tudo junto — as mensagens só mudam de estado se a transação
   inteira confirmar (SIMUL-05);
4. `simulando` → `concluida`.

Falha local dentro da transação 1 (SIMUL-09): a transação 1 volta atrás sozinha, deixando
zero entrega e todas as mensagens ainda em `aprovada`; só *depois*, numa **segunda** transação
independente e idempotente, o agregado vai a `falhou_simulacao` com uma `Exceção` sanitizada
local. As duas nunca são a mesma transação: se fossem, o `ROLLBACK` que preserva as mensagens
apagaria também o registro da falha.

A elegibilidade das mensagens é sempre recomputada do estado real persistido, dentro da
transação, e nunca do que a tela exibiu: uma mensagem que era `aprovada` quando Marina abriu o
modal e foi regenerada, rejeitada ou excluída antes do clique fica de fora (SIMUL-04, primeiro
Edge Case da spec). A aprovação exigida é dupla e verificada de fato — o estado `aprovada`
prova a decisão de Marina e a avaliação da última versão prova a do crítico (REVISAO-14).

`solicitar_nova_tentativa` é a terceira aplicação do padrão de execução correlacionada
(2.2 `falhou_coleta`, 3.1 `falhou_preparacao_ia`, agora `falhou_simulacao`): valida os
snapshots da origem antes de criar qualquer registro, cria a nova execução em
`aguardando_geracao` com `execucao_origem_id` próprio e copia as elegibilidades da origem na
mesma transação (AD-012). A origem permanece terminal (AD-009).

SPEC_DEVIATION: o `design.md` escreve
`confirmar(execucao_id, versao_esperada, chave_idempotencia, injecao_falha_teste)` e
`solicitar_nova_tentativa(execucao_origem_id, chave_idempotencia)`. As assinaturas
implementadas acrescentam `reconhecimento` e `hash_requisicao`: o reconhecimento porque a
própria tabela de Error Handling do design exige que o backend recuse o comando sem o campo
marcado, e o hash porque o AD-002 escopa a chave idempotente pelo conteúdo da requisição.
Mesma extensão já feita em `ServicoPreflightIA` (3.1) e `ServicoRevisaoLote` (3.5).
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, cast
from uuid import UUID

from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_criticas import (
    RegistroAvaliacaoCritica,
)
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    ContagemElegibilidade,
    RegistroElegibilidade,
)
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    EntregaSimulada,
    MensagemAprovada,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    SnapshotExecucao,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    RegistroMensagem,
    VersaoMensagem,
)
from central_preventiva.aplicacao.portas_persistencia import (
    ConflitoIdempotencia,
    PortaIdempotencia,
)
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.evento_meteorologico import EventoMeteorologico
from central_preventiva.dominio.validador_saida_canal import Canal

OPERACAO_CONFIRMAR_SIMULACAO = "confirmar_simulacao"
"""Escopo da confirmação no armazenamento genérico de chaves idempotentes (AD-002)."""

OPERACAO_NOVA_TENTATIVA_SIMULACAO = "solicitar_nova_tentativa_simulacao"
"""Escopo da nova tentativa após `falhou_simulacao` (SIMUL-10, AD-002)."""

STATUS_SIMULACAO_ACEITA = 200
"""Status registrado para a resposta de uma simulação já executada."""

MARCO_SIMULACAO_CONCLUIDA = "simulacao_concluida"
"""Marco de sucesso da simulação, correlacionado à execução (RUNNER-02, SIMUL-11)."""

MARCO_FALHOU_SIMULACAO = "falhou_simulacao"
"""Marco da falha local: carrega a causa sanitizada que a interface explica (SIMUL-09)."""

PREFIXO_CAUSA_FALHA_LOCAL = "falha_local_simulacao"
"""Prefixo da causa de toda falha desta etapa.

A causa nomeia o tipo do erro local e nada mais: nunca o conteúdo da mensagem, nunca um
desfecho de provedor externo, que não existe no MVP (SIMUL-09, ADR-0009/0013).
"""

TENTATIVAS_FALHA_LOCAL = 1
"""A simulação local não tem política de retry: a falha é registrada na primeira ocorrência.

Não existe "retry automático de falha de provedor" a contar aqui — a spec proíbe inventar
falha de canal, e a nova tentativa após `falhou_simulacao` é sempre explícita de Marina.
"""

IMPACTO_FALHA_SIMULACAO = (
    "Nenhuma entrega simulada foi registrada nesta execução; as mensagens aprovadas "
    "continuam aprovadas e podem ser simuladas em uma nova tentativa correlacionada."
)
"""Impacto operacional de toda execução que termina em `falhou_simulacao` (SIMUL-09)."""


class ExecucaoInexistente(RuntimeError):
    """Indica que o `execucao_id` informado não corresponde a nenhuma execução (AD-011)."""

    def __init__(self, execucao_id: UUID) -> None:
        """Identifica a execução ausente e monta a mensagem em português."""

        super().__init__(f"A execução '{execucao_id}' não existe.")
        self.execucao_id = execucao_id


class EstadoNaoConfirmavel(RuntimeError):
    """Indica confirmação pedida para execução fora de `aguardando_confirmacao`."""

    def __init__(self, execucao_id: UUID, estado: EstadoExecucao) -> None:
        """Identifica a execução e o estado que impede a confirmação."""

        super().__init__(
            f"A execução '{execucao_id}' está em '{estado}' e não aguarda confirmação de "
            "simulação."
        )
        self.execucao_id = execucao_id
        self.estado = estado


class ReconhecimentoObrigatorio(RuntimeError):
    """Indica confirmação enviada sem o reconhecimento da natureza simulada (SIMUL-03)."""

    def __init__(self, execucao_id: UUID) -> None:
        """Identifica a execução cuja confirmação foi recusada."""

        super().__init__(
            f"A simulação da execução '{execucao_id}' exige o reconhecimento explícito de "
            "que nenhuma comunicação real será enviada."
        )
        self.execucao_id = execucao_id


class NenhumaMensagemAprovada(RuntimeError):
    """Indica confirmação de um lote sem nenhuma aprovada (segundo Edge Case da spec)."""

    def __init__(self, execucao_id: UUID) -> None:
        """Identifica a execução cujo lote não tem o que simular."""

        super().__init__(
            f"A execução '{execucao_id}' não tem nenhuma mensagem aprovada pelo crítico e "
            "por Marina no momento da confirmação. Nenhuma simulação foi criada."
        )
        self.execucao_id = execucao_id


class FalhaLocalSimulacao(RuntimeError):
    """Indica falha local durante a criação das entregas simuladas (SIMUL-09)."""

    def __init__(self, execucao_id: UUID, causa: str) -> None:
        """Identifica a execução e a causa sanitizada, nunca o conteúdo simulado."""

        super().__init__(
            f"A simulação da execução '{execucao_id}' falhou localmente ({causa}). Nenhuma "
            "entrega foi registrada e as mensagens aprovadas continuam aprovadas."
        )
        self.execucao_id = execucao_id
        self.causa = causa


class OrigemNaoRetentavel(RuntimeError):
    """Indica nova tentativa pedida a partir de execução que não falhou na simulação."""

    def __init__(self, execucao_id: UUID, estado: EstadoExecucao) -> None:
        """Identifica a execução de origem e seu estado atual."""

        super().__init__(
            f"A execução '{execucao_id}' está em '{estado}'; a nova tentativa de simulação "
            "só parte de 'falhou_simulacao'."
        )
        self.execucao_id = execucao_id
        self.estado = estado


class SnapshotInvalido(RuntimeError):
    """Indica snapshot incompleto, corrompido ou em versão não suportada (SIMUL-10)."""

    def __init__(self, execucao_origem_id: UUID, motivo: str) -> None:
        """Identifica a origem e o motivo da recusa, sem citar conteúdo do snapshot."""

        super().__init__(
            f"Os snapshots da execução '{execucao_origem_id}' não passaram na validação: "
            f"{motivo}. Nenhuma execução nova foi criada."
        )
        self.execucao_origem_id = execucao_origem_id
        self.motivo = motivo


@dataclass(frozen=True, slots=True)
class ResultadoSimulacao:
    """Desfecho da confirmação: onde o agregado parou e o que a simulação registrou."""

    execucao_id: UUID
    estado: EstadoExecucao
    entregas_criadas: tuple[UUID, ...]
    mensagens_simuladas: tuple[UUID, ...]


@dataclass(frozen=True, slots=True)
class ResumoSimulacao:
    """O que a confirmação precisa mostrar antes, durante e depois da simulação.

    Antes: evento, regra, período, quantidade de destinatários e distribuição pelos três
    canais (SIMUL-01). Depois: as entregas simuladas, sempre rotuladas (SIMUL-06). Sempre: a
    navegação entre a origem e as retentativas, sem mesclar históricos (SIMUL-11).
    """

    execucao_id: UUID
    estado: EstadoExecucao
    versao: int
    evento: EventoMeteorologico | None
    regra_id: UUID | None
    regra_versao: int | None
    total_destinatarios: int
    distribuicao_por_canal: tuple[tuple[Canal, int], ...]
    entregas: tuple[EntregaSimulada, ...]
    execucao_origem_id: UUID | None
    retentativas: tuple[UUID, ...]


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

    def registrar_marco(
        self, execucao_id: UUID, marco: str, causa: str | None = None
    ) -> None: ...

    def listar_correlacionadas(
        self, execucao_origem_id: UUID
    ) -> list[SnapshotExecucao]: ...

    def criar_correlacionada(
        self,
        estado_inicial: EstadoExecucao,
        execucao_origem_id: UUID,
        apos_criar: Callable[[Any, UUID], None] | None = None,
    ) -> UUID: ...


class _RepositorioMensagens(Protocol):
    """Porta mínima de `mensagens`/`versoes_mensagem` (3.2/3.4/3.5)."""

    def listar_por_execucao(
        self, execucao_id: UUID, conexao: Any = None
    ) -> list[RegistroMensagem]: ...

    def obter_versao_atual(self, mensagem_id: UUID) -> VersaoMensagem | None: ...

    def transicionar(
        self,
        mensagem_id: UUID,
        versao_esperada: int,
        novo_estado: EstadoMensagem,
        conexao: Any = None,
    ) -> None: ...


class _RepositorioAvaliacoesCriticas(Protocol):
    """Porta mínima de `avaliacoes_criticas` (3.3)."""

    def obter_por_versao(
        self, versao_mensagem_id: UUID
    ) -> RegistroAvaliacaoCritica | None: ...


class _RepositorioEntregasSimuladas(Protocol):
    """Porta mínima de `entregas_simuladas` (T2)."""

    def criar_lote(
        self,
        execucao_id: UUID,
        mensagens_aprovadas: list[MensagemAprovada],
        conexao: Any = None,
    ) -> list[UUID]: ...

    def listar_por_execucao(self, execucao_id: UUID) -> list[EntregaSimulada]: ...


class _RepositorioExcecoesOperacionais(Protocol):
    """Porta mínima de registro de `Exceção` operacional sanitizada (2.2)."""

    def registrar(
        self,
        execucao_id: UUID,
        causa: str,
        tentativas: int,
        impacto: str,
        mensagem_id: UUID | None = None,
        conexao: Any = None,
    ) -> None: ...


class _RepositorioElegibilidades(Protocol):
    """Porta mínima do público elegível preservado pela execução (2.5, 3.1)."""

    def listar_por_execucao(self, execucao_id: UUID) -> list[RegistroElegibilidade]: ...

    def contar_por_execucao(self, execucao_id: UUID) -> ContagemElegibilidade: ...

    def copiar_para_execucao(
        self, execucao_origem_id: UUID, nova_execucao_id: UUID, conexao: Any = None
    ) -> int: ...


class _RepositorioEventos(Protocol):
    """Porta mínima do evento meteorológico referenciado pelo snapshot (2.2)."""

    def buscar_por_id(self, id: UUID) -> EventoMeteorologico | None: ...  # noqa: A002


class _Transacao(Protocol):
    """Porta da transação única do banco operacional (3.5)."""

    def executar[T](self, operacao: Callable[[Any], T]) -> T: ...


@dataclass(frozen=True, slots=True)
class PortasSimulacao:
    """Agrupa as portas de que a simulação local depende."""

    execucoes: _RepositorioExecucaoPreventiva
    mensagens: _RepositorioMensagens
    avaliacoes: _RepositorioAvaliacoesCriticas
    entregas: _RepositorioEntregasSimuladas
    excecoes: _RepositorioExcecoesOperacionais
    elegibilidades: _RepositorioElegibilidades
    eventos: _RepositorioEventos
    idempotencia: PortaIdempotencia
    transacao: _Transacao


class ServicoSimulacao:
    """Confirma e executa a simulação local, e trata a nova tentativa correlacionada."""

    def __init__(self, portas: PortasSimulacao) -> None:
        """Guarda as portas de leitura e escrita usadas pela simulação."""

        self._portas = portas

    def confirmar(
        self,
        execucao_id: UUID,
        versao_esperada: int,
        reconhecimento: bool,
        chave_idempotencia: str,
        hash_requisicao: str,
        injecao_falha_teste: Callable[[], None] | None = None,
    ) -> ResultadoSimulacao:
        """Reclama o lote aprovado e executa a simulação local (SIMUL-04..09).

        `injecao_falha_teste` existe **apenas para teste** e nunca é fornecido pelo código de
        composição: é o gancho determinístico que força uma falha local dentro da transação 1
        para provar o rollback exigido pelo SIMUL-09, sem depender de uma condição real e
        instável do DuckDB. `adaptadores/http/simulacao.py` nunca o passa.

        Repetir a mesma `Idempotency-Key` devolve a simulação já registrada, sem criar uma
        segunda entrega (SIMUL-07).
        """

        if not reconhecimento:
            raise ReconhecimentoObrigatorio(execucao_id)

        registrada = self._portas.idempotencia.buscar(
            chave_idempotencia, OPERACAO_CONFIRMAR_SIMULACAO
        )
        if registrada is not None:
            if registrada.hash_requisicao != hash_requisicao:
                raise ConflitoIdempotencia(
                    chave=chave_idempotencia, operacao=OPERACAO_CONFIRMAR_SIMULACAO
                )
            return _desserializar_simulacao(registrada.corpo)

        resultado = self._confirmar_agora(execucao_id, versao_esperada, injecao_falha_teste)
        self._portas.idempotencia.registrar(
            chave_idempotencia,
            OPERACAO_CONFIRMAR_SIMULACAO,
            hash_requisicao,
            STATUS_SIMULACAO_ACEITA,
            _serializar_simulacao(resultado),
        )
        return resultado

    def solicitar_nova_tentativa(
        self, execucao_origem_id: UUID, chave_idempotencia: str, hash_requisicao: str
    ) -> UUID:
        """Cria uma execução correlacionada nova a partir de `falhou_simulacao` (SIMUL-10).

        Valida antes a integridade dos snapshots da origem e rejeita sem criar nada se a
        validação falhar. Passando, cria a execução em `aguardando_geracao` com
        `execucao_origem_id` próprio e copia, na mesma transação, todas as elegibilidades da
        origem — incluídas e excluídas (AD-012). A cópia é obrigatória aqui: a origem chegou a
        `simulando`, então já tem um contexto e uma mensagem por elegibilidade, e reusar as
        linhas dela violaria as `UNIQUE` de `contextos_agente` e `mensagens` na primeira
        geração da nova execução. A origem permanece terminal (AD-009) e o replay da chave
        devolve o mesmo `execucao_id`.
        """

        registrada = self._portas.idempotencia.buscar(
            chave_idempotencia, OPERACAO_NOVA_TENTATIVA_SIMULACAO
        )
        if registrada is not None:
            if registrada.hash_requisicao != hash_requisicao:
                raise ConflitoIdempotencia(
                    chave=chave_idempotencia, operacao=OPERACAO_NOVA_TENTATIVA_SIMULACAO
                )
            return UUID(str(cast(dict[str, Any], json.loads(registrada.corpo))["execucao_id"]))

        origem = self._portas.execucoes.buscar(execucao_origem_id)
        if origem is None:
            raise ExecucaoInexistente(execucao_origem_id)
        if origem.estado is not EstadoExecucao.FALHOU_SIMULACAO:
            raise OrigemNaoRetentavel(execucao_origem_id, origem.estado)

        self._validar_snapshots(execucao_origem_id)

        def copiar_elegibilidades(conexao: Any, nova_execucao_id: UUID) -> None:
            """Duplica o público elegível da origem dentro da transação da criação."""

            self._portas.elegibilidades.copiar_para_execucao(
                execucao_origem_id, nova_execucao_id, conexao
            )

        nova_execucao_id = self._portas.execucoes.criar_correlacionada(
            EstadoExecucao.AGUARDANDO_GERACAO, execucao_origem_id, copiar_elegibilidades
        )
        self._portas.idempotencia.registrar(
            chave_idempotencia,
            OPERACAO_NOVA_TENTATIVA_SIMULACAO,
            hash_requisicao,
            STATUS_SIMULACAO_ACEITA,
            json.dumps({"execucao_id": str(nova_execucao_id)}),
        )
        return nova_execucao_id

    def obter_resumo(self, execucao_id: UUID) -> ResumoSimulacao | None:
        """Monta o resumo da simulação da execução, ou `None` se ela não existir (SIMUL-01).

        A resposta é idêntica para execução inexistente e para execução de outro escopo
        (AD-011): quem traduz `None` em `404` é o roteador.

        A contagem de destinatários e a distribuição por canal cobrem o lote simulável — o
        que ainda vai ser simulado (`aprovada`) e o que já foi (`simulada_entregue`) — para
        que o número que Marina viu no modal continue verdadeiro depois da simulação.
        """

        snapshot = self._portas.execucoes.buscar(execucao_id)
        if snapshot is None:
            return None

        elegibilidades = self._portas.elegibilidades.listar_por_execucao(execucao_id)
        evento = (
            None
            if not elegibilidades
            else self._portas.eventos.buscar_por_id(elegibilidades[0].evento_id)
        )
        a_simular = {registro.id for registro, _ in self._mensagens_a_simular(execucao_id)}
        canais = [
            registro.canal
            for registro in self._portas.mensagens.listar_por_execucao(execucao_id)
            if registro.id in a_simular
            or registro.estado is EstadoMensagem.SIMULADA_ENTREGUE
        ]
        return ResumoSimulacao(
            execucao_id=execucao_id,
            estado=snapshot.estado,
            versao=snapshot.versao,
            evento=evento,
            regra_id=elegibilidades[0].regra_id if elegibilidades else None,
            regra_versao=elegibilidades[0].regra_versao if elegibilidades else None,
            total_destinatarios=len(canais),
            distribuicao_por_canal=tuple(
                (canal, canais.count(canal)) for canal in Canal
            ),
            entregas=tuple(self._portas.entregas.listar_por_execucao(execucao_id)),
            execucao_origem_id=snapshot.execucao_origem_id,
            retentativas=tuple(
                correlacionada.id
                for correlacionada in self._portas.execucoes.listar_correlacionadas(execucao_id)
            ),
        )

    def _confirmar_agora(
        self,
        execucao_id: UUID,
        versao_esperada: int,
        injecao_falha_teste: Callable[[], None] | None,
    ) -> ResultadoSimulacao:
        """Executa a simulação de fato, já resolvida a idempotência do comando."""

        snapshot = self._portas.execucoes.buscar(execucao_id)
        if snapshot is None:
            raise ExecucaoInexistente(execucao_id)
        if snapshot.estado is not EstadoExecucao.AGUARDANDO_CONFIRMACAO:
            raise EstadoNaoConfirmavel(execucao_id, snapshot.estado)
        if not self._mensagens_a_simular(execucao_id):
            raise NenhumaMensagemAprovada(execucao_id)

        self._portas.execucoes.transicionar(
            execucao_id, versao_esperada, EstadoExecucao.SIMULANDO
        )
        versao_simulando = self._versao_atual(execucao_id)

        try:
            entregas, simuladas = self._portas.transacao.executar(
                lambda conexao: self._simular(conexao, execucao_id, injecao_falha_teste)
            )
        except Exception as erro:
            causa = self._registrar_falha_local(execucao_id, erro)
            raise FalhaLocalSimulacao(execucao_id, causa) from erro

        self._portas.execucoes.transicionar(
            execucao_id, versao_simulando, EstadoExecucao.CONCLUIDA
        )
        self._portas.execucoes.registrar_marco(execucao_id, MARCO_SIMULACAO_CONCLUIDA)
        return ResultadoSimulacao(
            execucao_id=execucao_id,
            estado=EstadoExecucao.CONCLUIDA,
            entregas_criadas=tuple(entregas),
            mensagens_simuladas=tuple(simuladas),
        )

    def _simular(
        self,
        conexao: Any,
        execucao_id: UUID,
        injecao_falha_teste: Callable[[], None] | None,
    ) -> tuple[list[UUID], list[UUID]]:
        """Cria as entregas e transiciona as mensagens na transação 1 (SIMUL-05).

        A elegibilidade é recomputada aqui dentro, do estado real persistido: o que a tela
        exibiu não entra nesta decisão em nenhum momento.
        """

        prontas = self._mensagens_a_simular(execucao_id, conexao)
        if not prontas:
            raise NenhumaMensagemAprovada(execucao_id)

        entregas = self._portas.entregas.criar_lote(
            execucao_id,
            [
                MensagemAprovada(registro.id, registro.canal, versao.conteudo)
                for registro, versao in prontas
            ],
            conexao,
        )
        for registro, _ in prontas:
            self._portas.mensagens.transicionar(
                registro.id, registro.versao, EstadoMensagem.SIMULADA_ENTREGUE, conexao
            )
        if injecao_falha_teste is not None:
            injecao_falha_teste()
        return entregas, [registro.id for registro, _ in prontas]

    def _registrar_falha_local(self, execucao_id: UUID, erro: BaseException) -> str:
        """Move o agregado a `falhou_simulacao` na segunda transação (SIMUL-09).

        Roda depois do `ROLLBACK` da transação 1, nunca junto dela: as mensagens já voltaram a
        `aprovada` e nenhuma entrega parcial existe quando esta transação começa.

        É idempotente por leitura do estado real: se o agregado já está em `falhou_simulacao`,
        não transiciona de novo (o terminal nunca reabre, AD-009) nem grava uma segunda
        `Exceção`. A causa nomeia só o tipo do erro local — nunca conteúdo de mensagem, nunca
        um desfecho de canal que não aconteceu.
        """

        causa = f"{PREFIXO_CAUSA_FALHA_LOCAL}:{type(erro).__name__}"
        snapshot = self._portas.execucoes.buscar(execucao_id)
        if snapshot is None or snapshot.estado is EstadoExecucao.FALHOU_SIMULACAO:
            return causa

        def falhar(conexao: Any) -> None:
            """Transição e `Exceção` sanitizada na mesma segunda transação."""

            self._portas.execucoes.transicionar(
                execucao_id, snapshot.versao, EstadoExecucao.FALHOU_SIMULACAO, conexao
            )
            self._portas.excecoes.registrar(
                execucao_id,
                causa,
                TENTATIVAS_FALHA_LOCAL,
                IMPACTO_FALHA_SIMULACAO,
                conexao=conexao,
            )

        self._portas.transacao.executar(falhar)
        self._portas.execucoes.registrar_marco(execucao_id, MARCO_FALHOU_SIMULACAO, causa)
        return causa

    def _mensagens_a_simular(
        self, execucao_id: UUID, conexao: Any = None
    ) -> list[tuple[RegistroMensagem, VersaoMensagem]]:
        """Lista as mensagens realmente simuláveis, do estado persistido (SIMUL-04).

        Entra só quem tem as duas aprovações: o estado `aprovada`, que apenas a decisão de
        Marina alcança (3.5), e a avaliação crítica aprovada da última versão (3.3). Rejeitada,
        excluída, em exceção ou de volta ao ciclo de conteúdo fica de fora por construção.
        """

        prontas: list[tuple[RegistroMensagem, VersaoMensagem]] = []
        for registro in self._portas.mensagens.listar_por_execucao(execucao_id, conexao):
            if registro.estado is not EstadoMensagem.APROVADA:
                continue
            versao = self._portas.mensagens.obter_versao_atual(registro.id)
            if versao is None:
                continue
            avaliacao = self._portas.avaliacoes.obter_por_versao(versao.id)
            if avaliacao is None or not avaliacao.avaliacao.aprovada:
                continue
            prontas.append((registro, versao))
        return prontas

    def _versao_atual(self, execucao_id: UUID) -> int:
        """Relê a versão de concorrência otimista do agregado depois da reclamação."""

        snapshot = self._portas.execucoes.buscar(execucao_id)
        assert snapshot is not None, f"execução {execucao_id} desapareceu após a reclamação"
        return snapshot.versao

    def _validar_snapshots(self, execucao_origem_id: UUID) -> None:
        """Recusa a nova tentativa se algum snapshot da origem estiver incompleto (SIMUL-10).

        Mesma validação que 3.1 aplica antes de uma retentativa de preparação: público
        preservado, regra versionada resolvível e suportada, critérios e canal preenchidos, e
        evento de referência ainda existente. Nada é criado antes de tudo isso passar.
        """

        contagem = self._portas.elegibilidades.contar_por_execucao(execucao_origem_id)
        total = contagem.incluidos + contagem.excluidos
        if total == 0:
            raise SnapshotInvalido(
                execucao_origem_id, "a execução de origem não preservou nenhuma elegibilidade"
            )

        registros = self._portas.elegibilidades.listar_por_execucao(execucao_origem_id)
        if len(registros) != total:
            raise SnapshotInvalido(
                execucao_origem_id, "há elegibilidade sem a regra versionada de referência"
            )

        for registro in registros:
            if registro.regra_versao < 1:
                raise SnapshotInvalido(
                    execucao_origem_id, "há elegibilidade com versão de regra não suportada"
                )
            if not registro.criterios:
                raise SnapshotInvalido(
                    execucao_origem_id, "há elegibilidade sem snapshot de critérios"
                )
            if not registro.canal.strip() or not registro.nome_segurado.strip():
                raise SnapshotInvalido(
                    execucao_origem_id, "há elegibilidade com snapshot incompleto"
                )
            if self._portas.eventos.buscar_por_id(registro.evento_id) is None:
                raise SnapshotInvalido(
                    execucao_origem_id, "há elegibilidade cujo evento de referência não existe"
                )


def _serializar_simulacao(resultado: ResultadoSimulacao) -> str:
    """Serializa o desfecho da simulação para o corpo guardado na chave idempotente."""

    return json.dumps(
        {
            "execucao_id": str(resultado.execucao_id),
            "estado": str(resultado.estado),
            "entregas_criadas": [str(item) for item in resultado.entregas_criadas],
            "mensagens_simuladas": [str(item) for item in resultado.mensagens_simuladas],
        }
    )


def _desserializar_simulacao(corpo: str) -> ResultadoSimulacao:
    """Reconstrói o desfecho registrado de uma simulação, sem repetir nenhum efeito."""

    dados = cast(dict[str, Any], json.loads(corpo))
    return ResultadoSimulacao(
        execucao_id=UUID(str(dados["execucao_id"])),
        estado=EstadoExecucao(str(dados["estado"])),
        entregas_criadas=tuple(UUID(str(item)) for item in dados["entregas_criadas"]),
        mensagens_simuladas=tuple(UUID(str(item)) for item in dados["mensagens_simuladas"]),
    )
