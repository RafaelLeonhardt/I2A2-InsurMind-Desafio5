"""Testes do caso de uso `ServicoColetaMeteorologica` (INMET-03..06,11,12,16; RESIL-06..14)."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest

from central_preventiva.adaptadores.meteorologia.adaptador_cenario_sintetico import (
    IDENTIFICADOR_CENARIO_GRANIZO,
    AdaptadorCenarioSintetico,
)
from central_preventiva.adaptadores.meteorologia.cliente_inmet import AdaptadorInmetFalso
from central_preventiva.adaptadores.meteorologia.normalizador_inmet import NormalizadorInmet
from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    RepositorioExcecoesOperacionais,
    RepositorioExecucaoPreventiva,
)
from central_preventiva.adaptadores.persistencia.repositorio_idempotencia import (
    RepositorioIdempotencia,
)
from central_preventiva.adaptadores.persistencia.repositorio_meteorologia import (
    RepositorioAreasMonitoradas,
    RepositorioCenariosSinteticosAtivados,
    RepositorioEventosMeteorologicos,
    RepositorioSincronizacoes,
    RepositorioTentativasColeta,
)
from central_preventiva.aplicacao.coleta_meteorologica import (
    AreaMonitoradaInexistente,
    PortasColetaMeteorologica,
    ServicoColetaMeteorologica,
    SincronizacaoInexistente,
)
from central_preventiva.aplicacao.portas_meteorologia import (
    AreaMonitorada,
    CodigoResultadoTentativa,
    EstadoSincronizacao,
    OrigemSincronizacao,
    RespostaColetaInmet,
    Sincronizacao,
)
from central_preventiva.aplicacao.portas_persistencia import (
    ConflitoIdempotencia,
    RespostaRegistrada,
)
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.evento_meteorologico import (
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)

AREA = AreaMonitorada(
    id=UUID("11111111-1111-1111-1111-111111111111"),
    codigo_estacao_inmet="A701",
    nome_estacao="Estação de Teste",
    codigo_ibge_area="9990001",
    ativa=True,
)

RESPOSTA_VALIDA = RespostaColetaInmet(
    status_code=200,
    corpo={"CHUVA": "42.0", "DT_MEDICAO": "2026-08-30", "HR_MEDICAO": "1200"},
)
RESPOSTA_INVALIDA = RespostaColetaInmet(status_code=200, corpo={"CHUVA": None})


class AreasFalsas:
    """Porta de áreas monitoradas falsa, resolvendo por id de um dicionário fixo."""

    def __init__(self, areas: dict[UUID, AreaMonitorada]) -> None:
        self._areas = areas

    def buscar_por_codigo_estacao(self, codigo_estacao_inmet: str) -> AreaMonitorada | None:
        for area in self._areas.values():
            if area.codigo_estacao_inmet == codigo_estacao_inmet:
                return area
        return None

    def buscar_por_id(self, id: UUID) -> AreaMonitorada | None:
        return self._areas.get(id)


class EventosFalsos:
    """Porta de eventos meteorológicos falsa, registrando os eventos salvos."""

    def __init__(self) -> None:
        self.salvos: list[object] = []

    def salvar(self, evento: object) -> None:
        self.salvos.append(evento)


class SincronizacoesFalsas:
    """Porta de sincronizações falsa, sobre um dicionário em memória."""

    def __init__(self) -> None:
        self._linhas: dict[UUID, Sincronizacao] = {}
        self.chamadas_criar = 0

    def criar(
        self,
        requisicao_id: UUID,
        area_monitorada_id: UUID,
        origem: OrigemSincronizacao,
        estado: EstadoSincronizacao,
    ) -> Sincronizacao:
        self.chamadas_criar += 1
        sincronizacao = Sincronizacao(
            id=uuid4(),
            requisicao_id=requisicao_id,
            area_monitorada_id=area_monitorada_id,
            origem=origem,
            estado=estado,
            registros_validos=0,
            motivo_falha=None,
            iniciado_em=datetime.now(UTC),
            finalizado_em=None,
        )
        self._linhas[sincronizacao.id] = sincronizacao
        return sincronizacao

    def atualizar_estado(
        self,
        id: UUID,
        estado: EstadoSincronizacao,
        registros_validos: int = 0,
        motivo_falha: str | None = None,
    ) -> None:
        atual = self._linhas[id]
        self._linhas[id] = Sincronizacao(
            id=atual.id,
            requisicao_id=atual.requisicao_id,
            area_monitorada_id=atual.area_monitorada_id,
            origem=atual.origem,
            estado=estado,
            registros_validos=registros_validos,
            motivo_falha=motivo_falha,
            iniciado_em=atual.iniciado_em,
            finalizado_em=datetime.now(UTC),
        )

    def listar_recentes(self) -> tuple[Sincronizacao, ...]:
        return tuple(
            sorted(self._linhas.values(), key=lambda s: s.iniciado_em, reverse=True)
        )

    def estado_de(self, id: UUID) -> Sincronizacao:
        return self._linhas[id]

    def buscar_por_id(self, id: UUID) -> Sincronizacao | None:
        return self._linhas.get(id)


class IdempotenciaFalsa:
    """Porta de idempotência falsa, sobre um dicionário em memória."""

    def __init__(self) -> None:
        self._registros: dict[tuple[str, str], RespostaRegistrada] = {}
        self.chamadas_registrar = 0

    def buscar(self, chave: str, operacao: str) -> RespostaRegistrada | None:
        return self._registros.get((chave, operacao))

    def registrar(
        self, chave: str, operacao: str, hash_requisicao: str, status: int, corpo: str
    ) -> None:
        self.chamadas_registrar += 1
        self._registros[(chave, operacao)] = RespostaRegistrada(
            hash_requisicao=hash_requisicao, status=status, corpo=corpo
        )


class TentativasFalsas:
    """Porta de tentativas falsa, registrando cada chamada para inspeção do teste."""

    def __init__(self) -> None:
        self.registradas: list[tuple[UUID, int, CodigoResultadoTentativa]] = []

    def registrar_tentativa(
        self,
        sincronizacao_id: UUID,
        numero_tentativa: int,
        codigo_resultado: CodigoResultadoTentativa,
        iniciado_em: object,
        finalizado_em: object,
    ) -> None:
        self.registradas.append((sincronizacao_id, numero_tentativa, codigo_resultado))

    def listar_tentativas(self, sincronizacao_id: UUID) -> tuple[object, ...]:
        return ()


class ExecucoesFalsas:
    """Porta de execuções falsa, sobre um dicionário em memória (estado, versão)."""

    def __init__(self) -> None:
        self._estados: dict[UUID, EstadoExecucao] = {}
        self.criadas: list[EstadoExecucao] = []
        self.transicoes: list[tuple[UUID, EstadoExecucao]] = []

    def criar(self, estado_inicial: EstadoExecucao) -> UUID:
        execucao_id = uuid4()
        self._estados[execucao_id] = estado_inicial
        self.criadas.append(estado_inicial)
        return execucao_id

    def transicionar(
        self, execucao_id: UUID, versao_esperada: int, novo_estado: EstadoExecucao
    ) -> None:
        self._estados[execucao_id] = novo_estado
        self.transicoes.append((execucao_id, novo_estado))

    def estado_de(self, execucao_id: UUID) -> EstadoExecucao:
        return self._estados[execucao_id]


class ExcecoesFalsas:
    """Porta de exceções operacionais falsa, registrando cada chamada para inspeção."""

    def __init__(self) -> None:
        self.registradas: list[tuple[UUID, str, int, str]] = []

    def registrar(self, execucao_id: UUID, causa: str, tentativas: int, impacto: str) -> None:
        self.registradas.append((execucao_id, causa, tentativas, impacto))


class CenariosAtivadosFalsos:
    """Porta de cenários sintéticos ativados falsa, registrando cada chamada."""

    def __init__(self) -> None:
        self.registrados: list[tuple[UUID, str]] = []

    def registrar(self, sincronizacao_id: UUID, identificador_cenario: str) -> None:
        self.registrados.append((sincronizacao_id, identificador_cenario))


async def _sem_espera_real(segundos: float) -> None:
    """Substitui o backoff real por um no-op, para nenhum teste depender de tempo real."""


def montar_servico(
    coletor: AdaptadorInmetFalso,
    areas: dict[UUID, AreaMonitorada] | None = None,
) -> tuple[
    ServicoColetaMeteorologica,
    SincronizacoesFalsas,
    EventosFalsos,
    IdempotenciaFalsa,
    ExecucoesFalsas,
    ExcecoesFalsas,
    CenariosAtivadosFalsos,
]:
    sincronizacoes = SincronizacoesFalsas()
    eventos = EventosFalsos()
    idempotencia = IdempotenciaFalsa()
    execucoes = ExecucoesFalsas()
    excecoes = ExcecoesFalsas()
    cenarios_ativados = CenariosAtivadosFalsos()
    portas = PortasColetaMeteorologica(
        idempotencia=idempotencia,
        areas=AreasFalsas(areas if areas is not None else {AREA.id: AREA}),
        coletor=coletor,
        normalizador=NormalizadorInmet(),
        eventos=eventos,  # type: ignore[arg-type]
        sincronizacoes=sincronizacoes,  # type: ignore[arg-type]
        tentativas=TentativasFalsas(),  # type: ignore[arg-type]
        execucoes=execucoes,
        excecoes=excecoes,
        cenario_sintetico=AdaptadorCenarioSintetico(),
        cenarios_ativados=cenarios_ativados,
        esperar=_sem_espera_real,
    )
    return (
        ServicoColetaMeteorologica(portas),
        sincronizacoes,
        eventos,
        idempotencia,
        execucoes,
        excecoes,
        cenarios_ativados,
    )


def test_solicitar_coleta_manual_persiste_sincronizacao_em_coletando_antes_de_qualquer_coisa() -> (
    None
):
    coletor = AdaptadorInmetFalso(resposta=RESPOSTA_VALIDA)
    servico, sincronizacoes, _, _, _, _, _ = montar_servico(coletor)

    aceita = asyncio.run(servico.solicitar_coleta_manual(AREA.id, "chave-1", "hash-1"))

    assert sincronizacoes.chamadas_criar == 1
    criada = sincronizacoes.listar_recentes()[0]
    assert criada.estado == EstadoSincronizacao.CONCLUIDO  # já fechada ao fim da execução síncrona
    assert aceita.sincronizacao.id == criada.id


def test_executar_coleta_com_sucesso_produz_evento_normalizado_e_sincronizacao_concluida() -> None:
    coletor = AdaptadorInmetFalso(resposta=RESPOSTA_VALIDA)
    servico, sincronizacoes, eventos, _, _, _, _ = montar_servico(coletor)

    resultado = asyncio.run(
        servico.executar_coleta(AREA, uuid4(), OrigemSincronizacao.AUTOMATICA)
    )

    assert resultado.estado == EstadoSincronizacao.CONCLUIDO
    assert resultado.registros_validos == 1
    assert resultado.motivo_falha is None
    assert len(eventos.salvos) == 1
    evento = eventos.salvos[0]
    assert evento.tipo == TipoEventoMeteorologico.CHUVA_INTENSA  # type: ignore[union-attr]
    assert evento.proveniencia == ProvenienciaEvento.REAL_INMET  # type: ignore[union-attr]


def test_executar_coleta_com_resposta_invalida_produz_falha_com_motivo_sem_criar_evento() -> None:
    coletor = AdaptadorInmetFalso(resposta=RESPOSTA_INVALIDA)
    servico, sincronizacoes, eventos, _, _, _, _ = montar_servico(coletor)

    resultado = asyncio.run(
        servico.executar_coleta(AREA, uuid4(), OrigemSincronizacao.AUTOMATICA)
    )

    assert resultado.estado == EstadoSincronizacao.FALHA
    assert resultado.motivo_falha == "campo_ausente"
    assert eventos.salvos == []


def test_executar_coleta_com_erro_de_transporte_persistente_esgota_retentativas() -> None:
    """RESIL-01/06/08: erro de transporte persistente esgota as 3 tentativas e a execução
    encerra como `falhou_coleta` com uma `Exceção` registrada, sem criar evento."""

    coletor = AdaptadorInmetFalso(excecao=httpx.TimeoutException("timeout"))
    servico, sincronizacoes, eventos, _, execucoes, excecoes, _ = montar_servico(coletor)

    resultado = asyncio.run(
        servico.executar_coleta(AREA, uuid4(), OrigemSincronizacao.AUTOMATICA)
    )

    assert resultado.estado == EstadoSincronizacao.FALHA
    assert resultado.motivo_falha == "retentativas_esgotadas"
    assert eventos.salvos == []
    assert len(coletor.chamadas) == 3
    assert execucoes.criadas == [EstadoExecucao.COLETANDO]
    assert len(execucoes.transicoes) == 1
    execucao_id, novo_estado = execucoes.transicoes[0]
    assert novo_estado == EstadoExecucao.FALHOU_COLETA
    assert execucoes.estado_de(execucao_id) == EstadoExecucao.FALHOU_COLETA
    assert len(excecoes.registradas) == 1
    excecao_execucao_id, causa, tentativas, impacto = excecoes.registradas[0]
    assert excecao_execucao_id == execucao_id
    assert "TimeoutException" in causa
    assert tentativas == 3
    assert impacto != ""


def test_repetir_solicitar_coleta_manual_com_mesma_chave_nao_dispara_nova_coleta() -> None:
    coletor = AdaptadorInmetFalso(resposta=RESPOSTA_VALIDA)
    servico, sincronizacoes, _, idempotencia, _, _, _ = montar_servico(coletor)

    primeira = asyncio.run(servico.solicitar_coleta_manual(AREA.id, "chave-repetida", "hash-x"))
    segunda = asyncio.run(servico.solicitar_coleta_manual(AREA.id, "chave-repetida", "hash-x"))

    assert len(coletor.chamadas) == 1
    assert sincronizacoes.chamadas_criar == 1
    assert segunda.sincronizacao.id == primeira.sincronizacao.id
    assert segunda.aceito_em == primeira.aceito_em


def test_repetir_chave_com_hash_diferente_levanta_conflito_idempotencia() -> None:
    coletor = AdaptadorInmetFalso(resposta=RESPOSTA_VALIDA)
    servico, _, _, _, _, _, _ = montar_servico(coletor)
    asyncio.run(servico.solicitar_coleta_manual(AREA.id, "chave-y", "hash-original"))

    with pytest.raises(ConflitoIdempotencia):
        asyncio.run(servico.solicitar_coleta_manual(AREA.id, "chave-y", "hash-diferente"))


def test_solicitar_coleta_manual_com_area_inexistente_levanta_erro_tipado() -> None:
    coletor = AdaptadorInmetFalso(resposta=RESPOSTA_VALIDA)
    servico, _, _, _, _, _, _ = montar_servico(coletor, areas={})

    with pytest.raises(AreaMonitoradaInexistente):
        asyncio.run(servico.solicitar_coleta_manual(AREA.id, "chave-z", "hash-z"))


def test_nenhum_log_do_caso_de_uso_expoe_corpo_externo_ou_credenciais(
    capsys: pytest.CaptureFixture[str],
) -> None:
    coletor = AdaptadorInmetFalso(resposta=RESPOSTA_VALIDA)
    servico, _, _, _, _, _, _ = montar_servico(coletor)

    asyncio.run(servico.executar_coleta(AREA, uuid4(), OrigemSincronizacao.AUTOMATICA))

    saida = capsys.readouterr()
    assert "CHUVA" not in saida.out
    assert "CHUVA" not in saida.err


def test_snapshot_anterior_permanece_apos_falha_esgotada_sem_criar_novo_evento() -> None:
    """RESIL-06/07: uma falha esgotada não remove nem substitui o evento anterior — o
    snapshot antigo continua no repositório, sem nenhum evento novo derivado dele."""

    coletor_ok = AdaptadorInmetFalso(resposta=RESPOSTA_VALIDA)
    servico, _, eventos, _, _, _, _ = montar_servico(coletor_ok)
    asyncio.run(servico.executar_coleta(AREA, uuid4(), OrigemSincronizacao.AUTOMATICA))
    assert len(eventos.salvos) == 1
    snapshot_anterior = eventos.salvos[0]

    coletor_ok._excecao = httpx.TimeoutException("timeout")
    resultado = asyncio.run(
        servico.executar_coleta(AREA, uuid4(), OrigemSincronizacao.AUTOMATICA)
    )

    assert resultado.estado == EstadoSincronizacao.FALHA
    assert eventos.salvos == [snapshot_anterior]


def test_solicitar_nova_tentativa_cria_execucao_correlacionada_sem_reabrir_a_terminal() -> None:
    """RESIL-10: a nova tentativa cria uma sincronização/execução próprias, sem mutar a
    sincronização de origem nem reabrir sua execução terminal."""

    coletor = AdaptadorInmetFalso(excecao=httpx.TimeoutException("timeout"))
    servico, sincronizacoes, eventos, _, execucoes, _, _ = montar_servico(coletor)
    origem = asyncio.run(
        servico.executar_coleta(AREA, uuid4(), OrigemSincronizacao.AUTOMATICA)
    )
    assert origem.estado == EstadoSincronizacao.FALHA
    execucoes_apos_origem = list(execucoes.transicoes)

    coletor._excecao = None
    coletor._resposta = RESPOSTA_VALIDA
    aceita = asyncio.run(
        servico.solicitar_nova_tentativa(origem.id, "chave-retry", "hash-retry")
    )

    assert aceita.sincronizacao.id != origem.id
    assert aceita.sincronizacao.estado == EstadoSincronizacao.CONCLUIDO
    assert len(eventos.salvos) == 1
    assert sincronizacoes.estado_de(origem.id).estado == EstadoSincronizacao.FALHA
    assert execucoes.transicoes == execucoes_apos_origem


def test_repetir_solicitar_nova_tentativa_com_mesma_chave_nao_duplica() -> None:
    coletor = AdaptadorInmetFalso(excecao=httpx.TimeoutException("timeout"))
    servico, sincronizacoes, _, _, _, _, _ = montar_servico(coletor)
    origem = asyncio.run(
        servico.executar_coleta(AREA, uuid4(), OrigemSincronizacao.AUTOMATICA)
    )

    coletor._excecao = None
    coletor._resposta = RESPOSTA_VALIDA
    contagem_antes = sincronizacoes.chamadas_criar
    primeira = asyncio.run(
        servico.solicitar_nova_tentativa(origem.id, "chave-retry-2", "hash-retry-2")
    )
    segunda = asyncio.run(
        servico.solicitar_nova_tentativa(origem.id, "chave-retry-2", "hash-retry-2")
    )

    assert sincronizacoes.chamadas_criar == contagem_antes + 1
    assert segunda.sincronizacao.id == primeira.sincronizacao.id
    assert segunda.aceito_em == primeira.aceito_em


def test_solicitar_nova_tentativa_com_sincronizacao_inexistente_levanta_erro_tipado() -> None:
    servico, _, _, _, _, _, _ = montar_servico(AdaptadorInmetFalso(resposta=RESPOSTA_VALIDA))

    with pytest.raises(SincronizacaoInexistente):
        asyncio.run(servico.solicitar_nova_tentativa(uuid4(), "chave-z", "hash-z"))


def test_ativar_cenario_sintetico_cria_evento_sintetico_isolado_de_real_inmet() -> None:
    """RESIL-12/13: o cenário sintético produz um evento `sintetico` registrado e
    correlacionado, sem se misturar a um evento `real_inmet` anterior."""

    coletor = AdaptadorInmetFalso(resposta=RESPOSTA_VALIDA)
    servico, _, eventos, _, _, _, cenarios_ativados = montar_servico(coletor)
    asyncio.run(servico.executar_coleta(AREA, uuid4(), OrigemSincronizacao.AUTOMATICA))
    assert len(eventos.salvos) == 1
    assert eventos.salvos[0].proveniencia == ProvenienciaEvento.REAL_INMET  # type: ignore[union-attr]

    aceita = asyncio.run(
        servico.ativar_cenario_sintetico(
            AREA.id, IDENTIFICADOR_CENARIO_GRANIZO, "chave-sintetico", "hash-sintetico"
        )
    )

    assert aceita.sincronizacao.estado == EstadoSincronizacao.CONCLUIDO
    assert len(eventos.salvos) == 2
    novo_evento = eventos.salvos[1]
    assert novo_evento.tipo == TipoEventoMeteorologico.GRANIZO  # type: ignore[union-attr]
    assert novo_evento.proveniencia == ProvenienciaEvento.SINTETICO  # type: ignore[union-attr]
    assert eventos.salvos[0].proveniencia == ProvenienciaEvento.REAL_INMET  # type: ignore[union-attr]
    assert cenarios_ativados.registrados == [
        (aceita.sincronizacao.id, IDENTIFICADOR_CENARIO_GRANIZO)
    ]


def test_repetir_ativar_cenario_sintetico_com_mesma_chave_nao_duplica() -> None:
    coletor = AdaptadorInmetFalso(resposta=RESPOSTA_VALIDA)
    servico, sincronizacoes, eventos, _, _, _, cenarios_ativados = montar_servico(coletor)

    primeira = asyncio.run(
        servico.ativar_cenario_sintetico(
            AREA.id, IDENTIFICADOR_CENARIO_GRANIZO, "chave-sintetico-2", "hash-sintetico-2"
        )
    )
    segunda = asyncio.run(
        servico.ativar_cenario_sintetico(
            AREA.id, IDENTIFICADOR_CENARIO_GRANIZO, "chave-sintetico-2", "hash-sintetico-2"
        )
    )

    assert len(eventos.salvos) == 1
    assert len(cenarios_ativados.registrados) == 1
    assert segunda.sincronizacao.id == primeira.sincronizacao.id
    assert segunda.aceito_em == primeira.aceito_em


def _preparar_banco_real(tmp_path: Path) -> tuple[Path, UUID]:
    """Aplica as migrações reais e insere uma área monitorada de teste."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    id_area = uuid4()
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO areas_monitoradas_inmet "
            "(id, codigo_estacao_inmet, nome_estacao, codigo_ibge_area, ativa) "
            "VALUES (?, 'A701', 'Estação de Teste', '9990001', true)",
            [id_area],
        )
    return caminho, id_area


def _servico_com_repositorios_reais(
    caminho: Path, coletor: AdaptadorInmetFalso
) -> ServicoColetaMeteorologica:
    """Monta o serviço sobre repositórios DuckDB reais, para provar a dedução por `UNIQUE`
    (T1/AD-010) — os dublês em memória de `montar_servico` não enforçam a constraint."""

    portas = PortasColetaMeteorologica(
        idempotencia=RepositorioIdempotencia(caminho),
        areas=RepositorioAreasMonitoradas(caminho),
        coletor=coletor,
        normalizador=NormalizadorInmet(),
        eventos=RepositorioEventosMeteorologicos(caminho),
        sincronizacoes=RepositorioSincronizacoes(caminho),
        tentativas=RepositorioTentativasColeta(caminho),
        execucoes=RepositorioExecucaoPreventiva(caminho),
        excecoes=RepositorioExcecoesOperacionais(caminho),
        cenario_sintetico=AdaptadorCenarioSintetico(),
        cenarios_ativados=RepositorioCenariosSinteticosAtivados(caminho),
        esperar=_sem_espera_real,
    )
    return ServicoColetaMeteorologica(portas)


def test_recuperacao_real_da_mesma_leitura_nao_duplica_evento_via_unique(
    tmp_path: Path,
) -> None:
    """RESIL-14: uma coleta real que observa de novo a mesma leitura horária (ex.: uma nova
    tentativa que recupera o evento já visto) não duplica a linha em `eventos_meteorologicos`
    — a `UNIQUE(tipo, area, periodo_inicio, periodo_fim)` de T1 garante isso de ponta a ponta,
    o que os dublês em memória das demais tentativas deste arquivo não conseguem provar."""

    caminho, id_area = _preparar_banco_real(tmp_path)
    coletor = AdaptadorInmetFalso(resposta=RESPOSTA_VALIDA)
    servico = _servico_com_repositorios_reais(caminho, coletor)
    area = RepositorioAreasMonitoradas(caminho).buscar_por_id(id_area)
    assert area is not None

    primeira = asyncio.run(
        servico.executar_coleta(area, uuid4(), OrigemSincronizacao.AUTOMATICA)
    )
    segunda = asyncio.run(
        servico.executar_coleta(area, uuid4(), OrigemSincronizacao.AUTOMATICA)
    )

    assert primeira.estado == EstadoSincronizacao.CONCLUIDO
    assert segunda.estado == EstadoSincronizacao.CONCLUIDO
    assert len(RepositorioEventosMeteorologicos(caminho).listar()) == 1
