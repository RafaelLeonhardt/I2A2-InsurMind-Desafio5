"""Caso de uso da coleta e normalização meteorológica do INMET."""

import asyncio
import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

import httpx

from central_preventiva.adaptadores.meteorologia.normalizador_inmet import NormalizadorInmet
from central_preventiva.aplicacao.portas_meteorologia import (
    AreaMonitorada,
    CodigoResultadoTentativa,
    ColetorMeteorologico,
    EstadoSincronizacao,
    OrigemSincronizacao,
    RepositorioAreasMonitoradas,
    RepositorioEventosMeteorologicos,
    RepositorioSincronizacoes,
    RepositorioTentativasColeta,
    RespostaColetaInmet,
    Sincronizacao,
)
from central_preventiva.aplicacao.portas_persistencia import ConflitoIdempotencia, PortaIdempotencia

MAXIMO_TENTATIVAS_COLETA = 3
"""Número total de tentativas de uma coleta com retry, incluindo a primeira (RESIL-01)."""

BACKOFF_SEGUNDOS_COLETA: tuple[float, ...] = (1.0, 2.0, 4.0)
"""Espera exponencial com jitter nulo entre tentativas: 1s após a 1ª falha, 2s após a 2ª."""


class RetentativasEsgotadas(Exception):
    """Indica que as `MAXIMO_TENTATIVAS_COLETA` tentativas de uma coleta se esgotaram.

    Carrega a última causa observada — a exceção de transporte/timeout da última tentativa,
    ou a última resposta com status de erro — para o chamador decidir o `motivo_falha`.
    """

    def __init__(
        self,
        tentativas: int,
        ultimo_erro: BaseException | None,
        ultima_resposta: RespostaColetaInmet | None,
    ) -> None:
        """Registra quantas tentativas ocorreram e a última causa de falha observada."""

        super().__init__(f"Esgotadas {tentativas} tentativas de coleta meteorológica.")
        self.tentativas = tentativas
        self.ultimo_erro = ultimo_erro
        self.ultima_resposta = ultima_resposta


class ColetorComRetry:
    """Envolve um `ColetorMeteorologico` de tentativa única com retry limitado (RESIL-01..05).

    Repete até `MAXIMO_TENTATIVAS_COLETA` vezes, aguardando `BACKOFF_SEGUNDOS_COLETA` entre
    falhas, registrando cada tentativa individual antes de decidir a próxima ação. Levanta
    `RetentativasEsgotadas` quando todas as tentativas falham; nunca retenta depois de uma
    resposta HTTP 200 (o conteúdo, se inválido, é rejeitado pelo normalizador — não é um
    caso de retry desta camada).
    """

    def __init__(
        self,
        delegado: ColetorMeteorologico,
        tentativas: RepositorioTentativasColeta,
        sincronizacao_id: UUID,
        esperar: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        """Guarda o coletor delegado, o repositório de tentativas e o relógio injetável."""

        self._delegado = delegado
        self._tentativas = tentativas
        self._sincronizacao_id = sincronizacao_id
        self._esperar = esperar

    async def coletar(self, area: AreaMonitorada) -> RespostaColetaInmet:
        """Tenta coletar até `MAXIMO_TENTATIVAS_COLETA` vezes, com backoff entre falhas."""

        ultimo_erro: BaseException | None = None
        ultima_resposta: RespostaColetaInmet | None = None

        for numero in range(1, MAXIMO_TENTATIVAS_COLETA + 1):
            inicio = datetime.now(UTC)
            try:
                resposta = await self._delegado.coletar(area)
            except httpx.TimeoutException as erro:
                self._registrar(numero, CodigoResultadoTentativa.TIMEOUT, inicio)
                ultimo_erro, ultima_resposta = erro, None
            except httpx.TransportError as erro:
                self._registrar(numero, CodigoResultadoTentativa.ERRO_TRANSPORTE, inicio)
                ultimo_erro, ultima_resposta = erro, None
            else:
                if resposta.status_code == 200:
                    self._registrar(numero, CodigoResultadoTentativa.SUCESSO, inicio)
                    return resposta
                self._registrar(numero, CodigoResultadoTentativa.STATUS_ERRO, inicio)
                ultimo_erro, ultima_resposta = None, resposta

            if numero < MAXIMO_TENTATIVAS_COLETA:
                await self._esperar(BACKOFF_SEGUNDOS_COLETA[numero - 1])

        raise RetentativasEsgotadas(MAXIMO_TENTATIVAS_COLETA, ultimo_erro, ultima_resposta)

    def _registrar(
        self, numero: int, codigo: CodigoResultadoTentativa, iniciado_em: datetime
    ) -> None:
        """Persiste a tentativa recém-concluída, imediatamente após seu término."""

        self._tentativas.registrar_tentativa(
            self._sincronizacao_id, numero, codigo, iniciado_em, datetime.now(UTC)
        )

OPERACAO_COLETA_MANUAL = "solicitar_coleta_manual"
"""Escopo desta operação no armazenamento genérico de chaves de idempotência (AD-002)."""

STATUS_COLETA_ACEITA = 202
"""Status registrado para o ack de uma coleta manual aceita."""

MOTIVO_ERRO_TRANSPORTE = "erro_transporte_ou_timeout"
"""Motivo de falha registrado quando o `ColetorMeteorologico` propaga timeout/erro de rede."""


class AreaMonitoradaInexistente(RuntimeError):
    """Indica que o `area_id` informado não corresponde a nenhuma área monitorada."""

    def __init__(self, area_id: UUID) -> None:
        """Identifica a área ausente e monta a mensagem em português."""

        super().__init__(f"A área monitorada '{area_id}' não existe.")
        self.area_id = area_id


@dataclass(frozen=True, slots=True)
class SincronizacaoAceita:
    """Resposta pública de uma solicitação de coleta manual aceita."""

    sincronizacao: Sincronizacao
    aceito_em: datetime


@dataclass(frozen=True, slots=True)
class PortasColetaMeteorologica:
    """Agrupa as portas de que o caso de uso de coleta meteorológica depende."""

    idempotencia: PortaIdempotencia
    areas: RepositorioAreasMonitoradas
    coletor: ColetorMeteorologico
    normalizador: NormalizadorInmet
    eventos: RepositorioEventosMeteorologicos
    sincronizacoes: RepositorioSincronizacoes


def _serializar_ack(sincronizacao: Sincronizacao, aceito_em: datetime) -> str:
    """Serializa a sincronização aceita para o corpo guardado na chave de idempotência."""

    return json.dumps(
        {
            "id": str(sincronizacao.id),
            "requisicao_id": str(sincronizacao.requisicao_id),
            "area_monitorada_id": str(sincronizacao.area_monitorada_id),
            "origem": str(sincronizacao.origem),
            "estado": str(sincronizacao.estado),
            "registros_validos": sincronizacao.registros_validos,
            "motivo_falha": sincronizacao.motivo_falha,
            "iniciado_em": sincronizacao.iniciado_em.isoformat(),
            "finalizado_em": (
                sincronizacao.finalizado_em.isoformat()
                if sincronizacao.finalizado_em is not None
                else None
            ),
            "aceito_em": aceito_em.isoformat(),
        }
    )


def _desserializar_ack(corpo: str) -> SincronizacaoAceita:
    """Reconstrói a sincronização aceita a partir do corpo previamente registrado."""

    dados = cast(dict[str, str | int | None], json.loads(corpo))
    sincronizacao = Sincronizacao(
        id=UUID(cast(str, dados["id"])),
        requisicao_id=UUID(cast(str, dados["requisicao_id"])),
        area_monitorada_id=UUID(cast(str, dados["area_monitorada_id"])),
        origem=OrigemSincronizacao(cast(str, dados["origem"])),
        estado=EstadoSincronizacao(cast(str, dados["estado"])),
        registros_validos=cast(int, dados["registros_validos"]),
        motivo_falha=cast(str | None, dados["motivo_falha"]),
        iniciado_em=datetime.fromisoformat(cast(str, dados["iniciado_em"])),
        finalizado_em=(
            datetime.fromisoformat(cast(str, dados["finalizado_em"]))
            if dados["finalizado_em"] is not None
            else None
        ),
    )
    return SincronizacaoAceita(
        sincronizacao=sincronizacao,
        aceito_em=datetime.fromisoformat(cast(str, dados["aceito_em"])),
    )


class ServicoColetaMeteorologica:
    """Orquestra uma tentativa de coleta meteorológica manual ou automática."""

    def __init__(self, portas: PortasColetaMeteorologica) -> None:
        """Guarda as portas de que este caso de uso depende."""

        self._portas = portas

    async def solicitar_coleta_manual(
        self, area_id: UUID, chave_idempotencia: str, hash_requisicao: str
    ) -> SincronizacaoAceita:
        """Aceita uma solicitação manual, idempotente por `chave_idempotencia` (AD-002).

        Repetir a mesma chave com o mesmo `hash_requisicao` devolve a resposta já
        registrada sem disparar nova coleta; hash diferente levanta `ConflitoIdempotencia`.
        A sincronização é persistida em `coletando` antes de qualquer coleta HTTP real.
        """

        registrada = self._portas.idempotencia.buscar(chave_idempotencia, OPERACAO_COLETA_MANUAL)
        if registrada is not None:
            if registrada.hash_requisicao != hash_requisicao:
                raise ConflitoIdempotencia(
                    chave=chave_idempotencia, operacao=OPERACAO_COLETA_MANUAL
                )
            return _desserializar_ack(registrada.corpo)

        area = self._portas.areas.buscar_por_id(area_id)
        if area is None:
            raise AreaMonitoradaInexistente(area_id)

        requisicao_id = uuid4()
        sincronizacao = await self.executar_coleta(area, requisicao_id, OrigemSincronizacao.MANUAL)
        aceito_em = datetime.now(UTC)
        self._portas.idempotencia.registrar(
            chave_idempotencia,
            OPERACAO_COLETA_MANUAL,
            hash_requisicao,
            STATUS_COLETA_ACEITA,
            _serializar_ack(sincronizacao, aceito_em),
        )
        return SincronizacaoAceita(sincronizacao=sincronizacao, aceito_em=aceito_em)

    async def executar_coleta(
        self, area: AreaMonitorada, requisicao_id: UUID, origem: OrigemSincronizacao
    ) -> Sincronizacao:
        """Executa uma tentativa de coleta completa: persiste, coleta, normaliza, fecha.

        Usada tanto pela coleta manual (após a reserva de idempotência) quanto pelo
        agendador automático. Nenhum log expõe o corpo íntegro da resposta do INMET
        nem credenciais (AD-10) — só o motivo de falha tipado é persistido.
        """

        sincronizacao = self._portas.sincronizacoes.criar(
            requisicao_id, area.id, origem, EstadoSincronizacao.COLETANDO
        )

        try:
            bruta = await self._portas.coletor.coletar(area)
        except (httpx.TimeoutException, httpx.TransportError):
            return self._fechar(sincronizacao, EstadoSincronizacao.FALHA, 0, MOTIVO_ERRO_TRANSPORTE)

        resultado = self._portas.normalizador.normalizar(bruta, area)
        if resultado.evento is not None:
            self._portas.eventos.salvar(resultado.evento)
            return self._fechar(sincronizacao, EstadoSincronizacao.CONCLUIDO, 1, None)

        return self._fechar(
            sincronizacao, EstadoSincronizacao.FALHA, 0, str(resultado.motivo_rejeicao)
        )

    def _fechar(
        self,
        sincronizacao: Sincronizacao,
        estado: EstadoSincronizacao,
        registros_validos: int,
        motivo_falha: str | None,
    ) -> Sincronizacao:
        """Fecha a sincronização com o estado terminal informado e devolve o registro final."""

        self._portas.sincronizacoes.atualizar_estado(
            sincronizacao.id, estado, registros_validos, motivo_falha
        )
        return replace(
            sincronizacao,
            estado=estado,
            registros_validos=registros_validos,
            motivo_falha=motivo_falha,
            finalizado_em=datetime.now(UTC),
        )
