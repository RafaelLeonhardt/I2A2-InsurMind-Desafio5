"""Testes do caso de uso da preparação agêntica (PREFL-01..04, PREFL-08..10, PREFL-15)."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest

from central_preventiva.adaptadores.ia.verificador_disponibilidade_openai import (
    ResultadoDisponibilidade,
)
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_contextos_agente import (
    RegistroContextoAgente,
    RepositorioContextosAgente,
)
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    ContagemElegibilidade,
    RegistroElegibilidade,
    RepositorioElegibilidades,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    RepositorioExcecoesOperacionais,
    RepositorioExecucaoPreventiva,
    SnapshotExecucao,
)
from central_preventiva.adaptadores.persistencia.repositorio_idempotencia import (
    RepositorioIdempotencia,
)
from central_preventiva.adaptadores.persistencia.repositorio_meteorologia import (
    RepositorioEventosMeteorologicos,
)
from central_preventiva.aplicacao.portas_persistencia import (
    ConflitoIdempotencia,
    RespostaRegistrada,
)
from central_preventiva.aplicacao.preflight_ia import (
    IMPACTO_ITEM_SEM_CONTEXTO,
    IMPACTO_PREPARACAO_IA,
    EstadoNaoPreparavel,
    ExecucaoInexistente,
    OrigemNaoRetentavel,
    PortasPreflightIA,
    ServicoPreflightIA,
    SnapshotInvalido,
)
from central_preventiva.dominio.avaliador_elegibilidade import (
    OPERANDO_AREA_AFETADA,
    OPERANDO_COBERTURA_EXIGIDA,
)
from central_preventiva.dominio.avaliador_risco import Criterio
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)
from central_preventiva.dominio.montador_contexto_agente import (
    CATEGORIAS_NAO_UTILIZADAS,
    CATEGORIAS_UTILIZADAS,
    ORIENTACOES_POR_EVENTO,
    ContextoAgente,
    MontadorContextoAgente,
)

EXECUCAO_ID = UUID("11111111-1111-1111-1111-111111111111")
EVENTO_ID = UUID("22222222-2222-2222-2222-222222222222")
REGRA_ID = UUID("33333333-3333-3333-3333-333333333333")
CHAVE = "chave-idempotente-1"
HASH = "hash-1"

EVENTO = EventoMeteorologico(
    id=EVENTO_ID,
    tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
    area="9990001",
    periodo_inicio=datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
    periodo_fim=datetime(2026, 9, 3, 18, 0, tzinfo=UTC),
    intensidade=62.5,
    proveniencia=ProvenienciaEvento.REAL_INMET,
    instante_observado=datetime(2026, 9, 3, 18, 0, tzinfo=UTC),
)

DISPONIVEL = ResultadoDisponibilidade(disponivel=True, causa=None)
INDISPONIVEL = ResultadoDisponibilidade(
    disponivel=False, causa="A credencial da OpenAI foi recusada."
)


def criterios_validos() -> tuple[Criterio, ...]:
    """Snapshot de critérios com área e coberturas, como 2.5 persiste um incluído."""

    return (
        Criterio(OPERANDO_AREA_AFETADA, "9990001", True, "Área corresponde."),
        Criterio(OPERANDO_COBERTURA_EXIGIDA, "alagamento, vendaval", True, "Possui cobertura."),
    )


def registro(
    elegivel: bool = True,
    criterios: tuple[Criterio, ...] | None = None,
    canal: str = "sms",
    evento_id: UUID = EVENTO_ID,
    regra_versao: int = 1,
    nome_segurado: str = "Pessoa Teste",
    id_registro: UUID | None = None,
    execucao_id: UUID = EXECUCAO_ID,
) -> RegistroElegibilidade:
    """Monta uma linha de elegibilidade já persistida, no formato que 2.5 devolve."""

    return RegistroElegibilidade(
        id=id_registro if id_registro is not None else uuid4(),
        execucao_id=execucao_id,
        evento_id=evento_id,
        regra_id=REGRA_ID,
        regra_versao=regra_versao,
        segurado_id=uuid4(),
        nome_segurado=nome_segurado,
        apolice_id=uuid4(),
        codigo_ibge_area="9990001",
        elegivel=elegivel,
        criterios=criterios if criterios is not None else criterios_validos(),
        canal=canal,
        justificativa="Atende integralmente aos critérios da regra ativa.",
        criado_em=datetime(2026, 9, 3, 19, 0, tzinfo=UTC),
    )


class VerificadorFalso:
    """Verificador dublê: devolve os resultados programados, repetindo o último."""

    def __init__(self, *resultados: ResultadoDisponibilidade) -> None:
        self._resultados = list(resultados)
        self.chamadas = 0

    async def verificar(self) -> ResultadoDisponibilidade:
        self.chamadas += 1
        if len(self._resultados) > 1:
            return self._resultados.pop(0)
        return self._resultados[0]


class ExecucoesFalsas:
    """Repositório de execuções dublê, com transições e criação correlacionada."""

    def __init__(self, snapshots: dict[UUID, SnapshotExecucao] | None = None) -> None:
        self.snapshots: dict[UUID, SnapshotExecucao] = dict(snapshots or {})
        self.transicoes: list[tuple[UUID, int, EstadoExecucao]] = []
        self.criadas: list[tuple[UUID, UUID, EstadoExecucao]] = []
        self.conexoes_da_transacao: list[object] = []

    def buscar(self, execucao_id: UUID) -> SnapshotExecucao | None:
        return self.snapshots.get(execucao_id)

    def transicionar(
        self, execucao_id: UUID, versao_esperada: int, novo_estado: EstadoExecucao
    ) -> None:
        self.transicoes.append((execucao_id, versao_esperada, novo_estado))
        atual = self.snapshots[execucao_id]
        self.snapshots[execucao_id] = SnapshotExecucao(
            id=atual.id,
            estado=novo_estado,
            versao=atual.versao + 1,
            execucao_origem_id=atual.execucao_origem_id,
        )

    def criar_correlacionada(
        self,
        estado_inicial: EstadoExecucao,
        execucao_origem_id: UUID,
        apos_criar: Any = None,
    ) -> UUID:
        nova = uuid4()
        conexao = object()
        if apos_criar is not None:
            apos_criar(conexao, nova)
            self.conexoes_da_transacao.append(conexao)
        self.snapshots[nova] = SnapshotExecucao(
            id=nova, estado=estado_inicial, versao=1, execucao_origem_id=execucao_origem_id
        )
        self.criadas.append((nova, execucao_origem_id, estado_inicial))
        return nova


class ExcecoesEspias:
    """Repositório de exceções dublê: guarda cada registro para inspeção do teste."""

    def __init__(self) -> None:
        self.registradas: list[tuple[UUID, str, int, str]] = []

    def registrar(self, execucao_id: UUID, causa: str, tentativas: int, impacto: str) -> None:
        self.registradas.append((execucao_id, causa, tentativas, impacto))


class ElegibilidadesFalsas:
    """Repositório de elegibilidades dublê, com registro das cópias solicitadas."""

    def __init__(self, registros: list[RegistroElegibilidade] | None = None) -> None:
        self.registros = list(registros or [])
        self.copias: list[tuple[UUID, UUID, object]] = []
        self.contagem_forcada: ContagemElegibilidade | None = None

    def listar_por_execucao(self, execucao_id: UUID) -> list[RegistroElegibilidade]:
        return [item for item in self.registros if item.execucao_id == execucao_id]

    def contar_por_execucao(self, execucao_id: UUID) -> ContagemElegibilidade:
        if self.contagem_forcada is not None:
            return self.contagem_forcada
        proprios = self.listar_por_execucao(execucao_id)
        return ContagemElegibilidade(
            incluidos=sum(1 for item in proprios if item.elegivel),
            excluidos=sum(1 for item in proprios if not item.elegivel),
        )

    def copiar_para_execucao(
        self, execucao_origem_id: UUID, nova_execucao_id: UUID, conexao: Any = None
    ) -> int:
        origem = self.listar_por_execucao(execucao_origem_id)
        self.copias.append((execucao_origem_id, nova_execucao_id, conexao))
        return len(origem)


class ContextosEspias:
    """Repositório de contextos dublê: guarda o que foi salvo, por item."""

    def __init__(self) -> None:
        self.salvos: list[tuple[UUID, UUID, ContextoAgente, tuple[str, ...], tuple[str, ...]]] = []

    def salvar(
        self,
        execucao_id: UUID,
        elegibilidade_id: UUID,
        contexto: ContextoAgente,
        categorias_usadas: tuple[str, ...],
        categorias_nao_usadas: tuple[str, ...],
    ) -> UUID:
        self.salvos.append(
            (execucao_id, elegibilidade_id, contexto, categorias_usadas, categorias_nao_usadas)
        )
        return uuid4()

    def listar_por_execucao(self, execucao_id: UUID) -> list[RegistroContextoAgente]:
        return [
            RegistroContextoAgente(
                id=uuid4(),
                execucao_id=execucao_id,
                elegibilidade_id=salvo[1],
                contexto=salvo[2],
                categorias_usadas=salvo[3],
                categorias_nao_usadas=salvo[4],
            )
            for salvo in self.salvos
            if salvo[0] == execucao_id
        ]


class EventosFalsos:
    """Repositório de eventos dublê, resolvendo apenas os eventos programados."""

    def __init__(self, *eventos: EventoMeteorologico) -> None:
        self._eventos = {evento.id: evento for evento in eventos}

    def buscar_por_id(self, id: UUID) -> EventoMeteorologico | None:
        return self._eventos.get(id)


class IdempotenciaFalsa:
    """Armazenamento de idempotência dublê, com a mesma semântica do repositório real."""

    def __init__(self) -> None:
        self.registros: dict[tuple[str, str], RespostaRegistrada] = {}

    def buscar(self, chave: str, operacao: str) -> RespostaRegistrada | None:
        return self.registros.get((chave, operacao))

    def registrar(
        self, chave: str, operacao: str, hash_requisicao: str, status: int, corpo: str
    ) -> None:
        self.registros[(chave, operacao)] = RespostaRegistrada(
            hash_requisicao=hash_requisicao, status=status, corpo=corpo
        )


class EsperaEspia:
    """Relógio dublê: registra os intervalos aguardados, sem nenhuma espera real."""

    def __init__(self) -> None:
        self.esperas: list[float] = []

    async def __call__(self, segundos: float) -> None:
        self.esperas.append(segundos)


class Cenario:
    """Reúne o caso de uso e todos os seus dublês, para inspeção direta nos testes."""

    def __init__(
        self,
        disponibilidade: tuple[ResultadoDisponibilidade, ...] = (DISPONIVEL,),
        registros: list[RegistroElegibilidade] | None = None,
        estado: EstadoExecucao = EstadoExecucao.AGUARDANDO_GERACAO,
        eventos: tuple[EventoMeteorologico, ...] = (EVENTO,),
        execucao_id: UUID = EXECUCAO_ID,
    ) -> None:
        self.verificador = VerificadorFalso(*disponibilidade)
        self.execucoes = ExecucoesFalsas(
            {execucao_id: SnapshotExecucao(id=execucao_id, estado=estado, versao=1)}
        )
        self.elegibilidades = ElegibilidadesFalsas(registros)
        self.excecoes = ExcecoesEspias()
        self.contextos = ContextosEspias()
        self.eventos = EventosFalsos(*eventos)
        self.idempotencia = IdempotenciaFalsa()
        self.espera = EsperaEspia()
        self.servico = ServicoPreflightIA(
            PortasPreflightIA(
                verificador=self.verificador,
                montador=MontadorContextoAgente(),
                execucoes=self.execucoes,
                excecoes=self.excecoes,
                elegibilidades=self.elegibilidades,
                contextos=self.contextos,
                eventos=self.eventos,
                idempotencia=self.idempotencia,
                esperar=self.espera,
            )
        )

    def preparar(
        self, execucao_id: UUID = EXECUCAO_ID, chave: str = CHAVE, hash_requisicao: str = HASH
    ):
        """Executa o preflight da execução informada, com a chave idempotente do teste."""

        return asyncio.run(self.servico.preparar(execucao_id, 1, chave, hash_requisicao))

    def nova_tentativa(
        self, origem_id: UUID = EXECUCAO_ID, chave: str = CHAVE, hash_requisicao: str = HASH
    ) -> UUID:
        """Solicita a nova tentativa a partir da execução de origem informada."""

        return asyncio.run(
            self.servico.solicitar_nova_tentativa(origem_id, chave, hash_requisicao)
        )


def test_disponibilidade_confirmada_transiciona_para_processando_mensagens() -> None:
    """PREFL-02: preflight bem-sucedido leva a execução a `processando_mensagens`."""

    incluido = registro()
    cenario = Cenario(registros=[incluido])

    resultado = cenario.preparar()

    assert resultado.estado == EstadoExecucao.PROCESSANDO_MENSAGENS
    assert resultado.causa is None
    assert resultado.contextos_montados == 1
    assert resultado.itens_em_excecao == ()
    assert cenario.execucoes.transicoes == [
        (EXECUCAO_ID, 1, EstadoExecucao.PROCESSANDO_MENSAGENS)
    ]
    assert cenario.execucoes.snapshots[EXECUCAO_ID].estado == (
        EstadoExecucao.PROCESSANDO_MENSAGENS
    )
    assert cenario.excecoes.registradas == []


def test_contexto_salvo_traz_os_cinco_campos_e_as_duas_listas_de_categorias() -> None:
    """PREFL-11, PREFL-13: o item preparado persiste contexto mínimo e proveniência."""

    incluido = registro()
    cenario = Cenario(registros=[incluido])

    cenario.preparar()

    assert len(cenario.contextos.salvos) == 1
    execucao_id, elegibilidade_id, contexto, usadas, nao_usadas = cenario.contextos.salvos[0]
    assert execucao_id == EXECUCAO_ID
    assert elegibilidade_id == incluido.id
    assert contexto == ContextoAgente(
        evento="chuva_intensa",
        localizacao_aproximada="9990001",
        coberturas_relevantes=("alagamento", "vendaval"),
        canal="sms",
        orientacoes_seguranca=ORIENTACOES_POR_EVENTO[TipoEventoMeteorologico.CHUVA_INTENSA],
    )
    assert usadas == CATEGORIAS_UTILIZADAS
    assert nao_usadas == CATEGORIAS_NAO_UTILIZADAS


def test_item_excluido_do_publico_nao_recebe_contexto() -> None:
    cenario = Cenario(registros=[registro(elegivel=False)])

    resultado = cenario.preparar()

    assert resultado.contextos_montados == 0
    assert cenario.contextos.salvos == []
    assert resultado.estado == EstadoExecucao.PROCESSANDO_MENSAGENS


def test_indisponibilidade_esgotada_transiciona_para_falhou_preparacao_ia() -> None:
    """PREFL-03, PREFL-04: terminal com exceção sanitizada e nenhum contexto montado."""

    cenario = Cenario(disponibilidade=(INDISPONIVEL,), registros=[registro()])

    resultado = cenario.preparar()

    assert resultado.estado == EstadoExecucao.FALHOU_PREPARACAO_IA
    assert resultado.causa == INDISPONIVEL.causa
    assert resultado.contextos_montados == 0
    assert cenario.verificador.chamadas == 3
    assert cenario.espera.esperas == [1.0, 2.0]
    assert cenario.execucoes.transicoes == [
        (EXECUCAO_ID, 1, EstadoExecucao.FALHOU_PREPARACAO_IA)
    ]
    assert cenario.excecoes.registradas == [
        (EXECUCAO_ID, INDISPONIVEL.causa, 3, IMPACTO_PREPARACAO_IA)
    ]
    assert cenario.contextos.salvos == []


def test_disponibilidade_confirmada_na_terceira_tentativa_nao_falha_a_execucao() -> None:
    """PREFL-01: uma indisponibilidade momentânea não condena a execução."""

    cenario = Cenario(
        disponibilidade=(INDISPONIVEL, INDISPONIVEL, DISPONIVEL), registros=[registro()]
    )

    resultado = cenario.preparar()

    assert resultado.estado == EstadoExecucao.PROCESSANDO_MENSAGENS
    assert cenario.verificador.chamadas == 3
    assert cenario.espera.esperas == [1.0, 2.0]
    assert cenario.excecoes.registradas == []


def test_item_com_contexto_invalido_isola_a_excecao_sem_afetar_os_demais() -> None:
    """PREFL-15: só o item inconsistente alcança o terminal de exceção."""

    valido = registro()
    invalido = registro(criterios=(Criterio(OPERANDO_AREA_AFETADA, "9990001", True, "ok"),))
    outro_valido = registro()
    cenario = Cenario(registros=[valido, invalido, outro_valido])

    resultado = cenario.preparar()

    assert resultado.estado == EstadoExecucao.PROCESSANDO_MENSAGENS
    assert resultado.contextos_montados == 2
    assert resultado.itens_em_excecao == (invalido.id,)
    assert [salvo[1] for salvo in cenario.contextos.salvos] == [valido.id, outro_valido.id]
    # Nenhuma solicitação parcial vai à OpenAI: a única chamada externa é a verificação
    # de disponibilidade, feita uma vez antes da montagem, nunca por item.
    assert cenario.verificador.chamadas == 1
    assert cenario.excecoes.registradas == [
        (
            EXECUCAO_ID,
            f"contexto_invalido:{invalido.id}:coberturas_relevantes",
            1,
            IMPACTO_ITEM_SEM_CONTEXTO,
        )
    ]


def test_item_cujo_evento_nao_existe_mais_isola_a_excecao_sem_afetar_os_demais() -> None:
    valido = registro()
    orfao = registro(evento_id=uuid4())
    cenario = Cenario(registros=[valido, orfao])

    resultado = cenario.preparar()

    assert resultado.contextos_montados == 1
    assert resultado.itens_em_excecao == (orfao.id,)
    assert cenario.excecoes.registradas == [
        (
            EXECUCAO_ID,
            f"evento_inexistente:{orfao.id}:{orfao.evento_id}",
            1,
            IMPACTO_ITEM_SEM_CONTEXTO,
        )
    ]


def test_execucao_ja_em_processando_mensagens_e_no_op_idempotente() -> None:
    """PREFL-02: a transição é idempotente — repetir não reverifica nem retransiciona."""

    cenario = Cenario(estado=EstadoExecucao.PROCESSANDO_MENSAGENS, registros=[registro()])

    resultado = cenario.preparar()

    assert resultado.estado == EstadoExecucao.PROCESSANDO_MENSAGENS
    assert cenario.verificador.chamadas == 0
    assert cenario.execucoes.transicoes == []
    assert cenario.contextos.salvos == []


@pytest.mark.parametrize(
    "estado",
    [
        EstadoExecucao.COLETANDO,
        EstadoExecucao.SEM_RISCO,
        EstadoExecucao.FALHOU_PREPARACAO_IA,
        EstadoExecucao.CONCLUIDA,
    ],
)
def test_execucao_fora_de_aguardando_geracao_nao_e_preparavel(
    estado: EstadoExecucao,
) -> None:
    """PREFL-01: só uma execução exclusivamente em `aguardando_geracao` é preparada."""

    cenario = Cenario(estado=estado, registros=[registro()])

    with pytest.raises(EstadoNaoPreparavel) as excecao:
        cenario.preparar()

    assert excecao.value.estado == estado
    assert cenario.verificador.chamadas == 0
    assert cenario.execucoes.transicoes == []


def test_preflight_de_execucao_inexistente_e_recusado() -> None:
    cenario = Cenario(registros=[registro()])
    inexistente = uuid4()

    with pytest.raises(ExecucaoInexistente) as excecao:
        cenario.preparar(execucao_id=inexistente)

    assert excecao.value.execucao_id == inexistente
    assert cenario.verificador.chamadas == 0


def test_repetir_a_chave_idempotente_devolve_a_resposta_sem_novo_preflight() -> None:
    """AD-002: replay do comando não dispara uma segunda verificação nem nova transição."""

    cenario = Cenario(registros=[registro()])
    primeiro = cenario.preparar()

    segundo = cenario.preparar()

    assert segundo == primeiro
    assert cenario.verificador.chamadas == 1
    assert len(cenario.execucoes.transicoes) == 1
    assert len(cenario.contextos.salvos) == 1


def test_mesma_chave_com_requisicao_diferente_e_conflito() -> None:
    cenario = Cenario(registros=[registro()])
    cenario.preparar()

    with pytest.raises(ConflitoIdempotencia):
        cenario.preparar(hash_requisicao="outro-hash")


def test_nova_tentativa_cria_execucao_correlacionada_sem_reabrir_a_origem() -> None:
    """PREFL-09: nova execução em `aguardando_geracao`, origem permanece terminal."""

    cenario = Cenario(
        estado=EstadoExecucao.FALHOU_PREPARACAO_IA,
        registros=[registro(), registro(elegivel=False)],
    )

    nova_id = cenario.nova_tentativa()

    assert nova_id != EXECUCAO_ID
    nova = cenario.execucoes.snapshots[nova_id]
    assert nova.estado == EstadoExecucao.AGUARDANDO_GERACAO
    assert nova.execucao_origem_id == EXECUCAO_ID
    assert cenario.execucoes.snapshots[EXECUCAO_ID].estado == EstadoExecucao.FALHOU_PREPARACAO_IA
    assert cenario.execucoes.transicoes == []


def test_nova_tentativa_copia_as_elegibilidades_da_origem_na_mesma_transacao() -> None:
    """AD-012: a cópia roda na conexão da transação que cria a execução correlacionada."""

    cenario = Cenario(
        estado=EstadoExecucao.FALHOU_PREPARACAO_IA,
        registros=[registro(), registro(elegivel=False)],
    )

    nova_id = cenario.nova_tentativa()

    assert len(cenario.elegibilidades.copias) == 1
    origem_copiada, destino_copiado, conexao = cenario.elegibilidades.copias[0]
    assert origem_copiada == EXECUCAO_ID
    assert destino_copiado == nova_id
    assert conexao is not None
    assert conexao in cenario.execucoes.conexoes_da_transacao


def test_replay_da_nova_tentativa_devolve_a_mesma_execucao_sem_criar_outra() -> None:
    """PREFL-09: o replay do comando não duplica execução nem efeito."""

    cenario = Cenario(
        estado=EstadoExecucao.FALHOU_PREPARACAO_IA, registros=[registro()]
    )
    primeira = cenario.nova_tentativa()

    segunda = cenario.nova_tentativa()

    assert segunda == primeira
    assert len(cenario.execucoes.criadas) == 1
    assert len(cenario.elegibilidades.copias) == 1


def test_nova_tentativa_com_a_mesma_chave_e_requisicao_diferente_e_conflito() -> None:
    cenario = Cenario(
        estado=EstadoExecucao.FALHOU_PREPARACAO_IA, registros=[registro()]
    )
    cenario.nova_tentativa()

    with pytest.raises(ConflitoIdempotencia):
        cenario.nova_tentativa(hash_requisicao="outro-hash")


@pytest.mark.parametrize(
    "estado",
    [EstadoExecucao.AGUARDANDO_GERACAO, EstadoExecucao.PROCESSANDO_MENSAGENS],
)
def test_nova_tentativa_so_parte_de_falhou_preparacao_ia(estado: EstadoExecucao) -> None:
    cenario = Cenario(estado=estado, registros=[registro()])

    with pytest.raises(OrigemNaoRetentavel):
        cenario.nova_tentativa()

    assert cenario.execucoes.criadas == []
    assert cenario.elegibilidades.copias == []


def test_nova_tentativa_de_execucao_inexistente_e_recusada() -> None:
    cenario = Cenario(estado=EstadoExecucao.FALHOU_PREPARACAO_IA, registros=[registro()])

    with pytest.raises(ExecucaoInexistente):
        cenario.nova_tentativa(origem_id=uuid4())

    assert cenario.execucoes.criadas == []


def test_origem_sem_nenhuma_elegibilidade_preservada_rejeita_a_nova_tentativa() -> None:
    """PREFL-08: validação falha, comando rejeitado, nenhuma execução criada."""

    cenario = Cenario(estado=EstadoExecucao.FALHOU_PREPARACAO_IA, registros=[])

    with pytest.raises(SnapshotInvalido):
        cenario.nova_tentativa()

    assert cenario.execucoes.criadas == []
    assert cenario.elegibilidades.copias == []


@pytest.mark.parametrize(
    ("linha", "motivo_esperado"),
    [
        (registro(regra_versao=0), "versão de regra não suportada"),
        (registro(criterios=()), "sem snapshot de critérios"),
        (registro(canal="  "), "snapshot incompleto"),
        (registro(nome_segurado=" "), "snapshot incompleto"),
        (registro(evento_id=uuid4()), "evento de referência não existe"),
    ],
)
def test_snapshot_corrompido_rejeita_a_nova_tentativa_sem_criar_execucao(
    linha: RegistroElegibilidade, motivo_esperado: str
) -> None:
    """PREFL-07, PREFL-08: referências versionadas incompletas bloqueiam o comando."""

    cenario = Cenario(estado=EstadoExecucao.FALHOU_PREPARACAO_IA, registros=[linha])

    with pytest.raises(SnapshotInvalido) as excecao:
        cenario.nova_tentativa()

    assert excecao.value.execucao_origem_id == EXECUCAO_ID
    assert motivo_esperado in excecao.value.motivo
    assert cenario.execucoes.criadas == []
    assert cenario.elegibilidades.copias == []


def test_elegibilidade_sem_regra_versionada_resolvivel_rejeita_a_nova_tentativa() -> None:
    """A listagem enriquecida perde a linha cuja regra sumiu; a contagem crua não."""

    cenario = Cenario(estado=EstadoExecucao.FALHOU_PREPARACAO_IA, registros=[registro()])
    cenario.elegibilidades.contagem_forcada = ContagemElegibilidade(incluidos=2, excluidos=0)

    with pytest.raises(SnapshotInvalido) as excecao:
        cenario.nova_tentativa()

    assert "regra versionada" in excecao.value.motivo
    assert cenario.execucoes.criadas == []


def preparar_banco(tmp_path: Path) -> Path:
    """Aplica as migrações versionadas em um banco temporário do teste."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def inserir_elegibilidade_real(
    caminho: Path, execucao_id: UUID, evento_id: UUID, regra_id: UUID, elegivel: bool
) -> UUID:
    """Insere uma linha de elegibilidade real, com o mesmo formato que 2.5 grava."""

    from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
    from central_preventiva.adaptadores.persistencia.serializacao_criterios import (
        serializar_criterios,
    )

    id_registro = uuid4()
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO elegibilidades_historicas "
            "(id, execucao_id, evento_id, regra_id, segurado_id, apolice_id, elegivel, "
            "criterios, canal, nome_segurado, justificativa) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'sms', 'Pessoa Teste', 'justificativa')",
            [
                id_registro,
                execucao_id,
                evento_id,
                regra_id,
                uuid4(),
                uuid4(),
                elegivel,
                serializar_criterios(criterios_validos()),
            ],
        )
    return id_registro


def test_retentativa_de_origem_com_contextos_monta_os_da_copia_sem_violar_a_unique(
    tmp_path: Path,
) -> None:
    """AD-012, cenário integrado: a origem já tem `contextos_agente`; a nova execução monta
    contextos para as elegibilidades copiadas, sem colidir na `UNIQUE (elegibilidade_id)`."""

    from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao

    caminho = preparar_banco(tmp_path)
    execucoes = RepositorioExecucaoPreventiva(caminho)
    elegibilidades = RepositorioElegibilidades(caminho)
    contextos = RepositorioContextosAgente(caminho)
    eventos = RepositorioEventosMeteorologicos(caminho)
    eventos.salvar(EVENTO)

    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
            "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
            "VALUES (?, 'chuva_intensa', 50.0, '9990001', 'residencial', 'alagamento', 24, "
            "'sms', 1, 'ativa')",
            [REGRA_ID],
        )

    origem_id = execucoes.criar(EstadoExecucao.AGUARDANDO_GERACAO)
    incluida = inserir_elegibilidade_real(caminho, origem_id, EVENTO.id, REGRA_ID, True)
    inserir_elegibilidade_real(caminho, origem_id, EVENTO.id, REGRA_ID, False)

    servico = ServicoPreflightIA(
        PortasPreflightIA(
            verificador=VerificadorFalso(DISPONIVEL),
            montador=MontadorContextoAgente(),
            execucoes=execucoes,
            excecoes=RepositorioExcecoesOperacionais(caminho),
            elegibilidades=elegibilidades,
            contextos=contextos,
            eventos=eventos,
            idempotencia=RepositorioIdempotencia(caminho),
            esperar=EsperaEspia(),
        )
    )

    primeiro = asyncio.run(servico.preparar(origem_id, 1, "chave-preflight-origem", HASH))
    assert primeiro.estado == EstadoExecucao.PROCESSANDO_MENSAGENS
    assert contextos.obter_por_elegibilidade(incluida) is not None

    execucoes.transicionar(origem_id, 2, EstadoExecucao.FALHOU_PREPARACAO_IA)
    nova_id = asyncio.run(
        servico.solicitar_nova_tentativa(origem_id, "chave-nova-tentativa", HASH)
    )

    copiadas = elegibilidades.listar_por_execucao(nova_id)
    assert len(copiadas) == 2
    assert {linha.elegivel for linha in copiadas} == {True, False}
    assert incluida not in {linha.id for linha in copiadas}
    assert execucoes.buscar(nova_id) is not None
    assert execucoes.buscar(nova_id).execucao_origem_id == origem_id  # type: ignore[union-attr]

    segundo = asyncio.run(servico.preparar(nova_id, 1, "chave-preflight-nova", HASH))

    assert segundo.estado == EstadoExecucao.PROCESSANDO_MENSAGENS
    assert segundo.contextos_montados == 1
    assert segundo.itens_em_excecao == ()
    assert len(contextos.listar_por_execucao(nova_id)) == 1
    assert len(contextos.listar_por_execucao(origem_id)) == 1


def test_nova_tentativa_nao_cria_nada_quando_a_copia_falha(tmp_path: Path) -> None:
    """AD-012: criação e cópia são atômicas — a falha da cópia não deixa execução órfã."""

    caminho = preparar_banco(tmp_path)
    execucoes = RepositorioExecucaoPreventiva(caminho)

    def falhar(_conexao: object, _nova_id: UUID) -> None:
        raise RuntimeError("falha sintética na cópia")

    origem_id = execucoes.criar(EstadoExecucao.AGUARDANDO_GERACAO)
    with pytest.raises(RuntimeError):
        execucoes.criar_correlacionada(
            EstadoExecucao.AGUARDANDO_GERACAO, origem_id, falhar
        )

    assert execucoes.listar_correlacionadas(origem_id) == []
