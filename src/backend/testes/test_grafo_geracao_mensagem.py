"""Testes do nó `gerar` do grafo de geração de uma mensagem (GERAR-05, GERAR-09).

O grafo compilado é exercitado de ponta a ponta com dublês: o redator é sempre falso, então
nenhum teste aqui chama a OpenAI real.
"""

import asyncio
from typing import Any

from central_preventiva.adaptadores.ia.agente_redator import RespostaRedator
from central_preventiva.aplicacao._retry import MAXIMO_TENTATIVAS
from central_preventiva.aplicacao.grafos.geracao_mensagem import (
    DependenciasGrafo,
    DesfechoGeracao,
    EstadoGrafoMensagem,
    ResultadoGeracao,
    construir_grafo,
)
from central_preventiva.dominio.montador_contexto_agente import ContextoAgente
from central_preventiva.dominio.validador_saida_canal import (
    Canal,
    LimitesCanal,
    SaidaCanal,
    ValidadorSaidaCanal,
)

LIMITES = LimitesCanal(whatsapp=1024, sms=160, assunto_email=78, corpo_email=2000)

CONTEXTO = ContextoAgente(
    evento="chuva_intensa",
    localizacao_aproximada="4314902",
    coberturas_relevantes=("alagamento",),
    canal="sms",
    orientacoes_seguranca=("Evite áreas alagadas.",),
)

CORPO_VALIDO = "Chuva forte prevista na sua região hoje. Evite áreas alagadas."


class RedatorFalso:
    """Dublê do agente redator: devolve respostas combinadas ou levanta erro de transporte."""

    def __init__(
        self, respostas: list[RespostaRedator] | None = None, erro: Exception | None = None
    ) -> None:
        self._respostas = respostas or []
        self._erro = erro
        self.chamadas = 0

    @property
    def modelo(self) -> str:
        return "gpt-4o-mini"

    async def gerar(self, contexto: ContextoAgente, canal: Canal) -> RespostaRedator:
        self.chamadas += 1
        if self._erro is not None:
            raise self._erro
        return self._respostas[min(self.chamadas - 1, len(self._respostas) - 1)]


async def sem_espera(_: float) -> None:
    """Substitui o backoff real para que o teste não durma de fato."""


def executar(redator: RedatorFalso, canal: Canal = Canal.SMS) -> ResultadoGeracao:
    """Roda o grafo compilado uma vez e devolve o resultado do nó `gerar`."""

    grafo = construir_grafo(
        DependenciasGrafo(
            redator=redator, validador=ValidadorSaidaCanal(LIMITES), esperar=sem_espera
        )
    )
    estado: EstadoGrafoMensagem = {"contexto": CONTEXTO, "canal": canal, "tentativa": 1}
    final: Any = asyncio.run(grafo.ainvoke(estado))
    resultado = final["resultado"]
    assert isinstance(resultado, ResultadoGeracao)
    return resultado


def test_sucesso_na_primeira_chamada_com_saida_valida_devolve_desfecho_valido() -> None:
    """GERAR-05: uma chamada de transporte bem-sucedida com saída válida encerra o nó."""

    redator = RedatorFalso([RespostaRedator(SaidaCanal(corpo=CORPO_VALIDO), 120, 40)])

    resultado = executar(redator)

    assert redator.chamadas == 1
    assert resultado.desfecho is DesfechoGeracao.VALIDA
    assert resultado.saida == SaidaCanal(corpo=CORPO_VALIDO)
    assert resultado.motivo is None
    assert resultado.modelo == "gpt-4o-mini"
    assert resultado.tokens_entrada == 120
    assert resultado.tokens_saida == 40
    assert resultado.duracao_ms > 0


def test_falha_de_transporte_esgotada_devolve_falhou_integracao_ia_sem_excecao() -> None:
    """GERAR-05: tentativas de transporte esgotadas viram desfecho, nunca exceção não tratada."""

    redator = RedatorFalso(erro=TimeoutError("conexão expirou"))

    resultado = executar(redator)

    assert redator.chamadas == MAXIMO_TENTATIVAS
    assert resultado.desfecho is DesfechoGeracao.FALHOU_INTEGRACAO_IA
    assert resultado.saida is None
    assert resultado.motivo == "TimeoutError: conexão expirou"
    assert resultado.tokens_entrada is None
    assert resultado.tokens_saida is None


def test_falha_de_transporte_intermitente_ainda_gera_saida_valida() -> None:
    """A política de tentativas é a mesma de 2.2/3.1: falha momentânea não condena a mensagem."""

    class RedatorInstavel(RedatorFalso):
        async def gerar(self, contexto: ContextoAgente, canal: Canal) -> RespostaRedator:
            self.chamadas += 1
            if self.chamadas == 1:
                raise TimeoutError("conexão expirou")
            return RespostaRedator(SaidaCanal(corpo=CORPO_VALIDO), 10, 5)

    redator = RedatorInstavel()

    resultado = executar(redator)

    assert redator.chamadas == 2
    assert resultado.desfecho is DesfechoGeracao.VALIDA


def test_saida_acima_do_limite_devolve_desfecho_invalido_com_motivo() -> None:
    """GERAR-09: saída acima do limite do canal é inválida, com motivo persistível."""

    redator = RedatorFalso([RespostaRedator(SaidaCanal(corpo="a" * 161), 100, 60)])

    resultado = executar(redator)

    assert resultado.desfecho is DesfechoGeracao.INVALIDA
    assert resultado.motivo == "limite_excedido:corpo:161:160"
    assert resultado.tokens_entrada == 100
    assert resultado.tokens_saida == 60


def test_saida_estruturalmente_vazia_devolve_desfecho_invalido_com_motivo() -> None:
    """GERAR-09: corpo em branco é campo obrigatório ausente, não sucesso."""

    redator = RedatorFalso([RespostaRedator(SaidaCanal(corpo="   "), 100, 2)])

    resultado = executar(redator)

    assert resultado.desfecho is DesfechoGeracao.INVALIDA
    assert resultado.motivo == "campo_obrigatorio_ausente:corpo"


def test_saida_ausente_devolve_desfecho_invalido_com_motivo() -> None:
    """GERAR-09: resposta sem conteúdo estruturado é inválida, não falha de integração."""

    redator = RedatorFalso([RespostaRedator(None, 100, 0)])

    resultado = executar(redator)

    assert resultado.desfecho is DesfechoGeracao.INVALIDA
    assert resultado.motivo == "saida_ausente"


def test_email_sem_assunto_devolve_desfecho_invalido() -> None:
    """GERAR-09: o veredito do canal e-mail vale igual dentro do grafo."""

    redator = RedatorFalso([RespostaRedator(SaidaCanal(corpo=CORPO_VALIDO, assunto=""), 1, 1)])

    resultado = executar(redator, Canal.EMAIL)

    assert resultado.desfecho is DesfechoGeracao.INVALIDA
    assert resultado.motivo == "campo_obrigatorio_ausente:assunto"
