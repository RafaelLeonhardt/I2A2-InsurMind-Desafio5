"""Caso de uso da restauração idempotente do conjunto sintético da demonstração."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import cast

from central_preventiva.aplicacao.portas_persistencia import (
    ConflitoIdempotencia,
    ExecucaoAtivaImpedeRestauracao,
    NaoInicializado,
    PortaDadosSinteticos,
    PortaExecucoes,
    PortaIdempotencia,
    ResultadoRestauracao,
)

OPERACAO_RESTAURACAO = "restaurar_dados_sinteticos"
"""Escopo desta operação no armazenamento genérico de chaves de idempotência."""

STATUS_RESTAURACAO = 201
"""Status registrado para a resposta de uma restauração bem-sucedida."""


@dataclass(frozen=True, slots=True)
class PortasRestauracao:
    """Agrupa as portas de que a restauração depende."""

    idempotencia: PortaIdempotencia
    execucoes: PortaExecucoes
    dados: PortaDadosSinteticos


def serializar_resultado(resultado: ResultadoRestauracao) -> str:
    """Serializa o resultado para o corpo guardado na chave de idempotência."""

    return json.dumps(
        {"status": resultado.status, "restaurado_em": resultado.restaurado_em.isoformat()}
    )


def desserializar_resultado(corpo: str) -> ResultadoRestauracao:
    """Reconstrói o resultado a partir do corpo previamente registrado."""

    dados = cast(dict[str, str], json.loads(corpo))
    return ResultadoRestauracao(
        status="restaurado",
        restaurado_em=datetime.fromisoformat(dados["restaurado_em"]),
    )


def restaurar_dados_sinteticos(
    portas: PortasRestauracao,
    chave_idempotencia: str,
    hash_requisicao: str,
) -> ResultadoRestauracao:
    """Repõe o conjunto sintético versionado, uma única vez por chave de idempotência."""

    if not portas.dados.esta_semeado():
        raise NaoInicializado()

    registrada = portas.idempotencia.buscar(chave_idempotencia, OPERACAO_RESTAURACAO)
    if registrada is not None:
        if registrada.hash_requisicao != hash_requisicao:
            raise ConflitoIdempotencia(chave=chave_idempotencia, operacao=OPERACAO_RESTAURACAO)
        return desserializar_resultado(registrada.corpo)

    if portas.execucoes.existe_execucao_nao_terminal():
        raise ExecucaoAtivaImpedeRestauracao()

    portas.dados.restaurar()
    resultado = ResultadoRestauracao(status="restaurado", restaurado_em=datetime.now(UTC))
    portas.idempotencia.registrar(
        chave_idempotencia,
        OPERACAO_RESTAURACAO,
        hash_requisicao,
        STATUS_RESTAURACAO,
        serializar_resultado(resultado),
    )
    return resultado
