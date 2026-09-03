"""Testes do agente crítico com dublê do modelo de chat (CRIT-01, CRIT-02, CRIT-03, CRIT-07).

Nenhum teste aqui toca a rede: o modelo é sempre um dublê que registra o que recebeu e
devolve o que o teste mandar, no mesmo formato de `with_structured_output(..., include_raw=True)`.
"""

import asyncio
import inspect
from dataclasses import dataclass
from typing import Any

import pytest
from pydantic import BaseModel

from central_preventiva.adaptadores.ia.agente_critico import (
    AgenteCritico,
    AvaliacaoEstruturada,
    MotivoEstruturado,
)
from central_preventiva.dominio.avaliacao_critica import (
    AvaliacaoCritica,
    CategoriaCritica,
    MotivoCritica,
)
from central_preventiva.dominio.montador_contexto_agente import ContextoAgente
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

CONTEXTO = ContextoAgente(
    evento="chuva_intensa",
    localizacao_aproximada="4314902",
    coberturas_relevantes=("alagamento", "vendaval"),
    canal="whatsapp",
    orientacoes_seguranca=(
        "Evite áreas alagadas e não atravesse ruas com água corrente.",
        "Mantenha documentos e itens essenciais em local elevado.",
    ),
)

MENSAGEM = SaidaCanal(corpo="Chuva forte prevista hoje. Evite áreas alagadas.")

LIMITES_CONFIGURADOS = ("1024", "160", "2000", "78")
"""Os quatro limites de canal de 3.2: nenhum deles pode alcançar o prompt do crítico."""


@dataclass
class InvocacaoFalsa:
    """O que o dublê recebeu em uma chamada: schema pedido e mensagens enviadas."""

    schema: type[BaseModel]
    include_raw: bool
    entrada: Any


class ModeloDeChatFalso:
    """Dublê de `ChatOpenAI`: registra a chamada e devolve a resposta combinada."""

    def __init__(self, resposta: Any = None, erro: Exception | None = None) -> None:
        self._resposta = resposta
        self._erro = erro
        self.invocacoes: list[InvocacaoFalsa] = []

    def with_structured_output(
        self, schema: type[BaseModel], *, include_raw: bool
    ) -> ModeloDeChatFalso:
        self._schema = schema
        self._include_raw = include_raw
        return self

    async def ainvoke(self, input: Any) -> Any:  # noqa: A002
        self.invocacoes.append(InvocacaoFalsa(self._schema, self._include_raw, input))
        if self._erro is not None:
            raise self._erro
        return self._resposta


def critico(modelo: ModeloDeChatFalso) -> AgenteCritico:
    """Monta o crítico sobre o dublê, com os parâmetros de modelo da configuração."""

    return AgenteCritico(
        modelo="gpt-4o-mini",
        temperatura=0.2,
        timeout_segundos=15.0,
        chave="chave-de-teste",
        modelo_de_chat=modelo,
    )


def avaliar(modelo: ModeloDeChatFalso, canal: Canal = Canal.WHATSAPP) -> AvaliacaoCritica | None:
    """Roda uma avaliação sobre o dublê e devolve o que o crítico produziu."""

    return asyncio.run(critico(modelo).avaliar(MENSAGEM, canal, CONTEXTO))


def test_aprovacao_devolve_decisao_estruturada_sem_motivos() -> None:
    """CRIT-03: a saída validada traz a decisão; aprovada não precisa de motivo."""

    modelo = ModeloDeChatFalso(
        {"parsed": AvaliacaoEstruturada(aprovada=True, motivos=[]), "raw": object()}
    )

    avaliacao = avaliar(modelo)

    assert avaliacao == AvaliacaoCritica(aprovada=True, motivos=())
    assert modelo.invocacoes[0].schema is AvaliacaoEstruturada
    assert modelo.invocacoes[0].include_raw is True


@pytest.mark.parametrize(
    ("categoria", "justificativa"),
    [
        (CategoriaCritica.TOM, "O texto usa tom alarmista, não preventivo."),
        (CategoriaCritica.UTILIDADE, "Não há orientação prática de proteção."),
        (CategoriaCritica.CLAREZA, "A instrução é ambígua sobre o que fazer."),
        (CategoriaCritica.SEGURANCA, "A orientação expõe a pessoa a área alagada."),
        (CategoriaCritica.PROMESSA_INDEVIDA, "O texto promete indenização integral."),
        (CategoriaCritica.DISTINCAO_OFICIAL, "Parece um alerta oficial da defesa civil."),
        (CategoriaCritica.ADEQUACAO_CANAL, "O texto não se adapta ao formato do canal."),
    ],
)
def test_reprovacao_por_cada_criterio_devolve_categoria_e_justificativa(
    categoria: CategoriaCritica, justificativa: str
) -> None:
    """CRIT-03: os sete critérios do AC produzem motivos específicos e categorizados."""

    modelo = ModeloDeChatFalso(
        {
            "parsed": AvaliacaoEstruturada(
                aprovada=False,
                motivos=[MotivoEstruturado(categoria=categoria, justificativa=justificativa)],
            ),
            "raw": object(),
        }
    )

    avaliacao = avaliar(modelo)

    assert avaliacao == AvaliacaoCritica(
        aprovada=False,
        motivos=(MotivoCritica(categoria=categoria, justificativa=justificativa),),
    )
    assert critico(modelo).modelo == "gpt-4o-mini"


def test_reprovacao_pode_reunir_varios_criterios_na_mesma_avaliacao() -> None:
    """CRIT-03: a avaliação carrega todos os motivos, não só o primeiro."""

    modelo = ModeloDeChatFalso(
        {
            "parsed": AvaliacaoEstruturada(
                aprovada=False,
                motivos=[
                    MotivoEstruturado(
                        categoria=CategoriaCritica.TOM, justificativa="Tom alarmista."
                    ),
                    MotivoEstruturado(
                        categoria=CategoriaCritica.PROMESSA_INDEVIDA,
                        justificativa="Promete cobertura integral.",
                    ),
                ],
            ),
            "raw": object(),
        }
    )

    avaliacao = avaliar(modelo)

    assert avaliacao is not None
    assert avaliacao.aprovada is False
    assert avaliacao.motivos == (
        MotivoCritica(CategoriaCritica.TOM, "Tom alarmista."),
        MotivoCritica(CategoriaCritica.PROMESSA_INDEVIDA, "Promete cobertura integral."),
    )


def test_as_sete_categorias_fechadas_sao_os_sete_criterios_do_ac() -> None:
    """CRIT-02, CRIT-03: enum fechado nos sete critérios, sem categoria de risco,
    elegibilidade, cobertura ou limite de canal — o crítico não tem como devolver um
    motivo sobre nenhuma dessas quatro decisões."""

    assert {categoria.value for categoria in CategoriaCritica} == {
        "tom",
        "utilidade",
        "clareza",
        "seguranca",
        "promessa_indevida",
        "distincao_oficial",
        "adequacao_canal",
    }
    for proibido in ("risco", "elegibilidade", "cobertura", "limite"):
        assert all(proibido not in categoria.value for categoria in CategoriaCritica)


def test_prompt_leva_a_mensagem_avaliada_e_o_contexto_minimo() -> None:
    """CRIT-01: o crítico recebe a mensagem e o contexto mínimo necessário à avaliação."""

    modelo = ModeloDeChatFalso(
        {"parsed": AvaliacaoEstruturada(aprovada=True, motivos=[]), "raw": object()}
    )
    conteudo = SaidaCanal(corpo="Chuva forte hoje.", assunto="Alerta preventivo")

    asyncio.run(critico(modelo).avaliar(conteudo, Canal.EMAIL, CONTEXTO))

    enviado = str(modelo.invocacoes[0].entrada)
    assert conteudo.corpo in enviado
    assert conteudo.assunto is not None
    assert conteudo.assunto in enviado
    assert Canal.EMAIL.value in enviado
    assert CONTEXTO.evento in enviado
    assert CONTEXTO.localizacao_aproximada in enviado
    for cobertura in CONTEXTO.coberturas_relevantes:
        assert cobertura in enviado
    for orientacao in CONTEXTO.orientacoes_seguranca:
        assert orientacao in enviado


def test_prompt_enumera_os_sete_criterios_de_avaliacao() -> None:
    """CRIT-03: a avaliação considera os sete critérios do AC, não um subconjunto."""

    modelo = ModeloDeChatFalso(
        {"parsed": AvaliacaoEstruturada(aprovada=True, motivos=[]), "raw": object()}
    )

    avaliar(modelo)

    enviado = str(modelo.invocacoes[0].entrada).lower()
    for criterio in (
        "tom preventivo",
        "utilidade",
        "clareza",
        "segurança",
        "promessa",
        "alerta oficial",
        "adequação ao canal",
    ):
        assert criterio in enviado


def test_critico_nao_recebe_limite_de_canal_nem_o_validador_deterministico() -> None:
    """CRIT-02, CRIT-04: o crítico não pode decidir limite de canal porque não conhece
    nenhum — nem por parâmetro de construção, nem pelo prompt."""

    parametros = set(inspect.signature(AgenteCritico.__init__).parameters)
    assert parametros == {
        "self",
        "modelo",
        "temperatura",
        "timeout_segundos",
        "chave",
        "modelo_de_chat",
    }

    modelo = ModeloDeChatFalso(
        {"parsed": AvaliacaoEstruturada(aprovada=True, motivos=[]), "raw": object()}
    )
    avaliar(modelo)

    enviado = str(modelo.invocacoes[0].entrada)
    for limite in LIMITES_CONFIGURADOS:
        assert limite not in enviado


def test_prompt_declara_que_o_critico_nao_decide_risco_elegibilidade_cobertura_nem_limite() -> None:
    """CRIT-02: a instrução do sistema nomeia as quatro decisões que não são do crítico."""

    modelo = ModeloDeChatFalso(
        {"parsed": AvaliacaoEstruturada(aprovada=True, motivos=[]), "raw": object()}
    )

    avaliar(modelo)

    enviado = str(modelo.invocacoes[0].entrada).lower()
    assert "não decide risco, elegibilidade, cobertura nem limite de canal" in enviado
    assert "não reescreve a mensagem" in enviado


def test_resposta_sem_conteudo_estruturado_volta_nula() -> None:
    """CRIT-07: saída não interpretável é falha da tentativa, nunca aprovação."""

    modelo = ModeloDeChatFalso({"parsed": None, "raw": object()})

    assert avaliar(modelo) is None


def test_resposta_fora_do_formato_esperado_volta_nula() -> None:
    """CRIT-07: uma resposta que nem é o envelope de saída estruturada não vira decisão."""

    modelo = ModeloDeChatFalso("resposta em texto livre")

    assert avaliar(modelo) is None


def test_reprovacao_sem_nenhum_motivo_volta_nula() -> None:
    """CRIT-07: reprovação sem motivo específico não é interpretável com segurança
    (CRIT-03/CRIT-06 exigem motivos associados à versão), e nunca vira aprovação."""

    modelo = ModeloDeChatFalso(
        {"parsed": AvaliacaoEstruturada(aprovada=False, motivos=[]), "raw": object()}
    )

    assert avaliar(modelo) is None


def test_motivo_sem_justificativa_volta_nulo() -> None:
    """CRIT-07: um motivo em branco não tem o que exibir no detalhe (CRIT-08)."""

    modelo = ModeloDeChatFalso(
        {
            "parsed": AvaliacaoEstruturada(
                aprovada=False,
                motivos=[MotivoEstruturado(categoria=CategoriaCritica.TOM, justificativa="   ")],
            ),
            "raw": object(),
        }
    )

    assert avaliar(modelo) is None


def test_excecao_de_transporte_propaga_ao_chamador() -> None:
    """O crítico não trata falha de transporte: quem decide tentativas é o wrapper de retry."""

    modelo = ModeloDeChatFalso(erro=TimeoutError("conexão expirou"))

    with pytest.raises(TimeoutError):
        avaliar(modelo)
