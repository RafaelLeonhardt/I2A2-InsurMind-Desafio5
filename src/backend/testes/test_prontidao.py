"""Testes do caso de uso de prontidão das dependências (caminho GET)."""

import asyncio

from central_preventiva.aplicacao.portas_prontidao import ResultadoSonda
from central_preventiva.aplicacao.prontidao import (
    CAUSA_CREDENCIAL_AUSENTE,
    CAUSA_FALHA_INESPERADA,
    PortasProntidao,
    RegistroProntidao,
    consultar_prontidao,
)
from central_preventiva.dominio.estados_prontidao import EstadoProntidao


class SondaFalsa:
    """Sonda dublê que devolve um resultado fixo ou levanta uma exceção informada."""

    def __init__(
        self, resultado: ResultadoSonda | None = None, excecao: Exception | None = None
    ) -> None:
        self._resultado = resultado
        self._excecao = excecao
        self.chamadas = 0

    async def verificar(self) -> ResultadoSonda:
        self.chamadas += 1
        if self._excecao is not None:
            raise self._excecao
        assert self._resultado is not None
        return self._resultado


class SondaQueFalhaSeChamada:
    """Sonda dublê que falha o teste se `verificar` for chamado."""

    async def verificar(self) -> ResultadoSonda:
        raise AssertionError("esta sonda não deveria ser chamada")


def _disponivel(latencia_ms: float | None = None) -> ResultadoSonda:
    return ResultadoSonda(estado=EstadoProntidao.DISPONIVEL, causa=None, latencia_ms=latencia_ms)


async def _aguardar_tarefas_pendentes() -> None:
    """Aguarda as tarefas de fundo disparadas por `asyncio.create_task` no teste."""

    pendentes = [tarefa for tarefa in asyncio.all_tasks() if tarefa is not asyncio.current_task()]
    if pendentes:
        await asyncio.gather(*pendentes)


def test_primeira_chamada_backend_e_banco_dados_terminais_inmet_e_openai_verificando() -> None:
    async def cenario() -> tuple[object, ...]:
        portas = PortasProntidao(
            backend=SondaFalsa(_disponivel()),
            banco_dados=SondaFalsa(_disponivel()),
            inmet=SondaFalsa(_disponivel()),
            openai=SondaFalsa(_disponivel()),
        )
        registro = RegistroProntidao()
        resultado = await consultar_prontidao(portas, registro)
        await _aguardar_tarefas_pendentes()
        return resultado

    backend, banco_dados, inmet, openai = asyncio.run(cenario())

    assert backend.estado == EstadoProntidao.DISPONIVEL
    assert backend.verificado_em is not None
    assert banco_dados.estado == EstadoProntidao.DISPONIVEL
    assert banco_dados.verificado_em is not None
    assert inmet.estado == EstadoProntidao.VERIFICANDO
    assert inmet.verificado_em is None
    assert openai.estado == EstadoProntidao.VERIFICANDO
    assert openai.verificado_em is None


def test_get_nao_bloqueia_nem_chama_sondas_externas_de_forma_sincrona() -> None:
    async def cenario() -> tuple[int, int]:
        sonda_inmet = SondaFalsa(_disponivel())
        sonda_openai = SondaFalsa(_disponivel())
        portas = PortasProntidao(
            backend=SondaFalsa(_disponivel()),
            banco_dados=SondaFalsa(_disponivel()),
            inmet=sonda_inmet,
            openai=sonda_openai,
        )
        registro = RegistroProntidao()

        await consultar_prontidao(portas, registro)
        chamadas_no_retorno = (sonda_inmet.chamadas, sonda_openai.chamadas)

        await _aguardar_tarefas_pendentes()
        return chamadas_no_retorno

    chamadas_inmet, chamadas_openai = asyncio.run(cenario())

    assert chamadas_inmet == 0
    assert chamadas_openai == 0


def test_chamada_seguinte_apos_conclusao_reflete_estado_terminal_sem_novo_disparo() -> None:
    async def cenario() -> tuple[object, object, int]:
        sonda_inmet = SondaFalsa(_disponivel(latencia_ms=42.0))
        portas = PortasProntidao(
            backend=SondaFalsa(_disponivel()),
            banco_dados=SondaFalsa(_disponivel()),
            inmet=sonda_inmet,
            openai=SondaFalsa(_disponivel()),
        )
        registro = RegistroProntidao()

        primeira = await consultar_prontidao(portas, registro)
        await _aguardar_tarefas_pendentes()
        segunda = await consultar_prontidao(portas, registro)

        return primeira[2], segunda[2], sonda_inmet.chamadas

    inmet_primeira, inmet_segunda, chamadas = asyncio.run(cenario())

    assert inmet_primeira.estado == EstadoProntidao.VERIFICANDO
    assert inmet_segunda.estado == EstadoProntidao.DISPONIVEL
    assert inmet_segunda.verificado_em is not None
    assert chamadas == 1


def test_sonda_com_excecao_nao_mapeada_resulta_em_indisponivel_generico() -> None:
    async def cenario() -> object:
        portas = PortasProntidao(
            backend=SondaFalsa(_disponivel()),
            banco_dados=SondaFalsa(_disponivel()),
            inmet=SondaFalsa(excecao=RuntimeError("falha simulada não mapeada")),
            openai=SondaFalsa(_disponivel()),
        )
        registro = RegistroProntidao()

        await consultar_prontidao(portas, registro)
        await _aguardar_tarefas_pendentes()
        return registro.obter("inmet")

    inmet = asyncio.run(cenario())

    assert inmet is not None
    assert inmet.estado == EstadoProntidao.INDISPONIVEL
    assert inmet.causa == CAUSA_FALHA_INESPERADA
    assert "falha simulada" not in str(inmet.causa)


def test_backend_e_banco_dados_sao_computados_sem_depender_das_sondas_externas() -> None:
    async def cenario() -> tuple[object, object]:
        portas = PortasProntidao(
            backend=SondaFalsa(_disponivel()),
            banco_dados=SondaFalsa(_disponivel()),
            inmet=SondaQueFalhaSeChamada(),
            openai=SondaQueFalhaSeChamada(),
        )
        registro = RegistroProntidao()

        backend, banco_dados, _inmet, _openai = await consultar_prontidao(portas, registro)
        return backend, banco_dados

    backend, banco_dados = asyncio.run(cenario())

    assert backend.estado == EstadoProntidao.DISPONIVEL
    assert banco_dados.estado == EstadoProntidao.DISPONIVEL


def test_openai_sem_sonda_configurada_fica_indisponivel_sem_chamada_de_rede() -> None:
    async def cenario() -> object:
        portas = PortasProntidao(
            backend=SondaFalsa(_disponivel()),
            banco_dados=SondaFalsa(_disponivel()),
            inmet=SondaFalsa(_disponivel()),
            openai=None,
        )
        registro = RegistroProntidao()

        _backend, _banco_dados, _inmet, openai = await consultar_prontidao(portas, registro)
        await _aguardar_tarefas_pendentes()
        return openai

    openai = asyncio.run(cenario())

    assert openai.estado == EstadoProntidao.INDISPONIVEL
    assert openai.causa == CAUSA_CREDENCIAL_AUSENTE
    assert openai.verificado_em is not None
