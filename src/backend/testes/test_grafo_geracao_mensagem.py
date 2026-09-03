"""Testes dos nós `gerar` (3.2) e `criticar` (3.3) do grafo de uma mensagem.

O grafo compilado é exercitado de ponta a ponta com dublês: redator e crítico são sempre
falsos, então nenhum teste aqui chama a OpenAI real.
"""

import asyncio
from typing import Any

from central_preventiva.adaptadores.ia.agente_redator import RespostaRedator
from central_preventiva.aplicacao._retry import MAXIMO_TENTATIVAS
from central_preventiva.aplicacao.grafos.geracao_mensagem import (
    CAUSA_SAIDA_CRITICA_INVALIDA,
    DependenciasGrafo,
    DesfechoCritica,
    DesfechoGeracao,
    EstadoGrafoMensagem,
    ResultadoCritica,
    ResultadoGeracao,
    construir_grafo,
)
from central_preventiva.dominio.avaliacao_critica import (
    AvaliacaoCritica,
    CategoriaCritica,
    MotivoCritica,
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


class CriticoFalso:
    """Dublê do agente crítico: devolve avaliações combinadas ou erro de transporte."""

    def __init__(
        self,
        avaliacoes: list[AvaliacaoCritica | None] | None = None,
        erro: Exception | None = None,
    ) -> None:
        self._avaliacoes: list[AvaliacaoCritica | None] = (
            avaliacoes if avaliacoes is not None else [AvaliacaoCritica(True, ())]
        )
        self._erro = erro
        self.chamadas = 0
        self.conteudos: list[SaidaCanal] = []
        self.contextos: list[ContextoAgente] = []

    @property
    def modelo(self) -> str:
        return "gpt-4o-mini"

    async def avaliar(
        self, conteudo: SaidaCanal, canal: Canal, contexto: ContextoAgente
    ) -> AvaliacaoCritica | None:
        self.chamadas += 1
        self.conteudos.append(conteudo)
        self.contextos.append(contexto)
        if self._erro is not None:
            raise self._erro
        return self._avaliacoes[min(self.chamadas - 1, len(self._avaliacoes) - 1)]


async def sem_espera(_: float) -> None:
    """Substitui o backoff real para que o teste não durma de fato."""


def rodar(
    redator: RedatorFalso, critico: CriticoFalso, canal: Canal = Canal.SMS
) -> dict[str, Any]:
    """Roda o grafo compilado uma vez e devolve o estado final completo."""

    grafo = construir_grafo(
        DependenciasGrafo(
            redator=redator,
            validador=ValidadorSaidaCanal(LIMITES),
            critico=critico,
            esperar=sem_espera,
        )
    )
    estado: EstadoGrafoMensagem = {"contexto": CONTEXTO, "canal": canal, "tentativa": 1}
    final: Any = asyncio.run(grafo.ainvoke(estado))
    return final


def executar(redator: RedatorFalso, canal: Canal = Canal.SMS) -> ResultadoGeracao:
    """Roda o grafo compilado uma vez e devolve o resultado do nó `gerar`."""

    resultado = rodar(redator, CriticoFalso(), canal)["resultado"]
    assert isinstance(resultado, ResultadoGeracao)
    return resultado


def criticar(
    critico: CriticoFalso, corpo: str = CORPO_VALIDO, canal: Canal = Canal.SMS
) -> ResultadoCritica:
    """Roda o grafo com uma geração válida e devolve o resultado do nó `criticar`."""

    redator = RedatorFalso([RespostaRedator(SaidaCanal(corpo=corpo), 120, 40)])
    resultado = rodar(redator, critico, canal)["resultado_critica"]
    assert isinstance(resultado, ResultadoCritica)
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


def test_saida_aprovada_pelo_critico_devolve_desfecho_aprovado_sem_motivos() -> None:
    """CRIT-05: aprovação do crítico é um desfecho próprio, com motivos vazios."""

    critico = CriticoFalso([AvaliacaoCritica(aprovada=True, motivos=())])

    resultado = criticar(critico)

    assert critico.chamadas == 1
    assert resultado.desfecho is DesfechoCritica.APROVADA
    assert resultado.motivos == ()
    assert resultado.causa is None
    assert resultado.modelo == "gpt-4o-mini"
    assert resultado.duracao_ms > 0


def test_saida_reprovada_devolve_motivos_estruturados_por_categoria() -> None:
    """CRIT-06: a reprovação carrega os motivos categorizados, não só a decisão."""

    critico = CriticoFalso(
        [
            AvaliacaoCritica(
                aprovada=False,
                motivos=(
                    MotivoCritica(CategoriaCritica.TOM, "O texto usa tom alarmista."),
                    MotivoCritica(
                        CategoriaCritica.PROMESSA_INDEVIDA, "Promete indenização integral."
                    ),
                ),
            )
        ]
    )

    resultado = criticar(critico)

    assert resultado.desfecho is DesfechoCritica.REPROVADA
    assert resultado.motivos == (
        MotivoCritica(CategoriaCritica.TOM, "O texto usa tom alarmista."),
        MotivoCritica(CategoriaCritica.PROMESSA_INDEVIDA, "Promete indenização integral."),
    )
    assert resultado.causa is None


def test_saida_do_critico_nao_interpretavel_e_falha_da_tentativa_nunca_aprovacao() -> None:
    """CRIT-07: saída inválida não vira aprovação nem reprovação estruturada."""

    critico = CriticoFalso([None])

    resultado = criticar(critico)

    assert resultado.desfecho is DesfechoCritica.SAIDA_INVALIDA
    assert resultado.desfecho is not DesfechoCritica.APROVADA
    assert resultado.motivos == ()
    assert resultado.causa == CAUSA_SAIDA_CRITICA_INVALIDA


def test_falha_de_transporte_da_critica_esgotada_devolve_falhou_integracao_ia() -> None:
    """Edge case da spec: falha de transporte do crítico segue o padrão de 3.2, sem
    terminal novo, e nunca é confundida com uma saída inválida de conteúdo."""

    critico = CriticoFalso(erro=TimeoutError("conexão expirou"))

    resultado = criticar(critico)

    assert critico.chamadas == MAXIMO_TENTATIVAS
    assert resultado.desfecho is DesfechoCritica.FALHOU_INTEGRACAO_IA
    assert resultado.motivos == ()
    assert resultado.causa == "TimeoutError: conexão expirou"


def test_falha_de_transporte_intermitente_da_critica_ainda_produz_avaliacao() -> None:
    """A política de tentativas do crítico é a mesma do redator: falha momentânea não
    condena a avaliação."""

    class CriticoInstavel(CriticoFalso):
        async def avaliar(
            self, conteudo: SaidaCanal, canal: Canal, contexto: ContextoAgente
        ) -> AvaliacaoCritica | None:
            self.chamadas += 1
            if self.chamadas == 1:
                raise TimeoutError("conexão expirou")
            return AvaliacaoCritica(aprovada=True, motivos=())

    critico = CriticoInstavel()

    resultado = criticar(critico)

    assert critico.chamadas == 2
    assert resultado.desfecho is DesfechoCritica.APROVADA


def test_grafo_nao_invoca_o_critico_para_saida_invalida_do_redator() -> None:
    """CRIT-04: uma mensagem já reprovada deterministicamente por 3.2 nunca chega ao
    crítico — o modelo não tem como sobrepor a validação objetiva, porque não é chamado."""

    redator = RedatorFalso([RespostaRedator(SaidaCanal(corpo="a" * 161), 100, 60)])
    critico = CriticoFalso([AvaliacaoCritica(aprovada=True, motivos=())])

    final = rodar(redator, critico)

    assert final["resultado"].desfecho is DesfechoGeracao.INVALIDA
    assert critico.chamadas == 0
    assert "resultado_critica" not in final


def test_grafo_nao_invoca_o_critico_quando_a_geracao_falha_por_transporte() -> None:
    """CRIT-04: sem saída gerada não há conteúdo a avaliar; o crítico não é chamado."""

    redator = RedatorFalso(erro=TimeoutError("conexão expirou"))
    critico = CriticoFalso()

    final = rodar(redator, critico)

    assert final["resultado"].desfecho is DesfechoGeracao.FALHOU_INTEGRACAO_IA
    assert critico.chamadas == 0
    assert "resultado_critica" not in final


def test_critico_recebe_exatamente_o_texto_gerado_e_o_contexto_minimo() -> None:
    """CRIT-01: o crítico recebe a mensagem validada e o mesmo contexto mínimo de 3.1."""

    critico = CriticoFalso()

    criticar(critico, corpo=CORPO_VALIDO)

    assert critico.conteudos == [SaidaCanal(corpo=CORPO_VALIDO)]
    assert critico.contextos == [CONTEXTO]
