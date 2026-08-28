"""Caso de uso da inicialização do schema versionado e do conjunto sintético."""

from dataclasses import dataclass

from central_preventiva.aplicacao.portas_persistencia import (
    MigracoesPendentes,
    PortaDadosSinteticos,
    PortaMigracoes,
    ResultadoInicializacao,
    VersaoSchemaFutura,
)


@dataclass(frozen=True, slots=True)
class PortasInicializacao:
    """Agrupa as portas de que a inicialização depende."""

    migracoes: PortaMigracoes
    dados: PortaDadosSinteticos


def inicializar_dados_sinteticos(portas: PortasInicializacao) -> ResultadoInicializacao:
    """Aplica as migrações pendentes e semeia o conjunto sintético quando ausente."""

    migracao = portas.migracoes.aplicar_pendentes()

    semeado_agora = False
    if not portas.dados.esta_semeado():
        portas.dados.semear()
        semeado_agora = True

    preparou = bool(migracao.versoes_aplicadas) or semeado_agora
    return ResultadoInicializacao(
        estado="inicializado" if preparou else "ja_preparado",
        versoes_aplicadas=migracao.versoes_aplicadas,
        semeado_agora=semeado_agora,
    )


def verificar_versao_schema(portas: PortasInicializacao) -> None:
    """Confere a versão do schema sem aplicar qualquer mutação ao banco."""

    registrada = portas.migracoes.versao_registrada()
    conhecida = portas.migracoes.versao_conhecida()

    if registrada is not None and registrada > conhecida:
        raise VersaoSchemaFutura(versao_registrada=registrada, versao_conhecida=conhecida)
    if registrada is None or registrada < conhecida:
        raise MigracoesPendentes(versao_registrada=registrada, versao_conhecida=conhecida)
