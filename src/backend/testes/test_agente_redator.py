"""Testes do agente redator com dublê do modelo de chat (GERAR-07, GERAR-08).

Nenhum teste aqui toca a rede: o modelo é sempre um dublê que registra o que recebeu e
devolve o que o teste mandar, no mesmo formato de `with_structured_output(..., include_raw=True)`.
"""

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest
from pydantic import BaseModel

from central_preventiva.adaptadores.ia.agente_redator import (
    AgenteRedator,
    RespostaRedator,
    SaidaEmail,
    SaidaSMS,
    SaidaWhatsApp,
)
from central_preventiva.dominio.montador_contexto_agente import ContextoAgente
from central_preventiva.dominio.validador_saida_canal import (
    Canal,
    LimitesCanal,
    ValidadorSaidaCanal,
)

LIMITES = LimitesCanal(whatsapp=1024, sms=160, assunto_email=78, corpo_email=2000)

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


class UsoFalso:
    """Resposta bruta do modelo, com os metadados de uso que a versão registra."""

    def __init__(self, entrada: int | None, saida: int | None) -> None:
        self.usage_metadata = (
            None
            if entrada is None or saida is None
            else {"input_tokens": entrada, "output_tokens": saida}
        )


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


def redator(modelo: ModeloDeChatFalso) -> AgenteRedator:
    """Monta o redator sobre o dublê, com os limites de canal padrão."""

    return AgenteRedator(
        validador=ValidadorSaidaCanal(LIMITES),
        modelo="gpt-4o-mini",
        temperatura=0.2,
        timeout_segundos=15.0,
        chave="chave-de-teste",
        modelo_de_chat=modelo,
    )


@pytest.mark.parametrize(
    ("canal", "schema", "estruturada"),
    [
        (
            Canal.WHATSAPP,
            SaidaWhatsApp,
            SaidaWhatsApp(corpo="Chuva forte hoje: evite alagamentos."),
        ),
        (Canal.SMS, SaidaSMS, SaidaSMS(corpo="Chuva forte hoje: evite alagamentos.")),
        (
            Canal.EMAIL,
            SaidaEmail,
            SaidaEmail(assunto="Alerta preventivo", corpo="Chuva forte hoje na sua região."),
        ),
    ],
)
def test_cada_canal_pede_seu_proprio_schema_e_devolve_a_saida(
    canal: Canal, schema: type[BaseModel], estruturada: BaseModel
) -> None:
    """GERAR-07, GERAR-08: um schema Pydantic distinto por canal, com os campos do canal."""

    modelo = ModeloDeChatFalso({"parsed": estruturada, "raw": UsoFalso(120, 45)})

    resposta = asyncio.run(redator(modelo).gerar(CONTEXTO, canal))

    assert modelo.invocacoes[0].schema is schema
    assert resposta.saida is not None
    assert resposta.saida.corpo == estruturada.model_dump()["corpo"]
    assert resposta.saida.assunto == estruturada.model_dump().get("assunto")
    assert resposta.tokens_entrada == 120
    assert resposta.tokens_saida == 45


def test_prompt_leva_os_cinco_campos_do_contexto_minimo_e_nada_mais() -> None:
    """AD-9: só o contexto mínimo de 3.1 alcança o modelo."""

    modelo = ModeloDeChatFalso({"parsed": SaidaWhatsApp(corpo="ok"), "raw": UsoFalso(1, 1)})

    asyncio.run(redator(modelo).gerar(CONTEXTO, Canal.WHATSAPP))

    enviado = str(modelo.invocacoes[0].entrada)
    assert CONTEXTO.evento in enviado
    assert CONTEXTO.localizacao_aproximada in enviado
    for cobertura in CONTEXTO.coberturas_relevantes:
        assert cobertura in enviado
    for orientacao in CONTEXTO.orientacoes_seguranca:
        assert orientacao in enviado


@pytest.mark.parametrize(
    ("canal", "trechos"),
    [
        (Canal.WHATSAPP, ("1024",)),
        (Canal.SMS, ("160",)),
        (Canal.EMAIL, ("2000", "78")),
    ],
)
def test_limite_configurado_do_canal_instrui_a_geracao(
    canal: Canal, trechos: tuple[str, ...]
) -> None:
    """GERAR-02: o limite é aplicado antes da geração, como instrução do prompt."""

    modelo = ModeloDeChatFalso(
        {
            "parsed": SaidaEmail(assunto="a", corpo="b")
            if canal is Canal.EMAIL
            else SaidaWhatsApp(corpo="b"),
            "raw": UsoFalso(1, 1),
        }
    )

    asyncio.run(redator(modelo).gerar(CONTEXTO, canal))

    enviado = str(modelo.invocacoes[0].entrada)
    for trecho in trechos:
        assert trecho in enviado


def test_resposta_sem_conteudo_estruturado_volta_com_saida_nula() -> None:
    """GERAR-09: saída ausente/malformada não levanta exceção — quem decide é o validador."""

    modelo = ModeloDeChatFalso({"parsed": None, "raw": UsoFalso(50, 0)})

    resposta = asyncio.run(redator(modelo).gerar(CONTEXTO, Canal.SMS))

    assert resposta == RespostaRedator(saida=None, tokens_entrada=50, tokens_saida=0)


def test_resposta_sem_metadados_de_uso_registra_tokens_nulos() -> None:
    """As métricas são anuláveis quando a chamada não devolve uso (schema da versão)."""

    modelo = ModeloDeChatFalso({"parsed": SaidaSMS(corpo="ok"), "raw": UsoFalso(None, None)})

    resposta = asyncio.run(redator(modelo).gerar(CONTEXTO, Canal.SMS))

    assert resposta.tokens_entrada is None
    assert resposta.tokens_saida is None
    assert resposta.saida is not None
    assert resposta.saida.corpo == "ok"


def test_excecao_de_transporte_propaga_ao_chamador() -> None:
    """O redator não trata falha de transporte: quem decide tentativas é o wrapper de retry."""

    modelo = ModeloDeChatFalso(erro=TimeoutError("conexão expirou"))

    with pytest.raises(TimeoutError):
        asyncio.run(redator(modelo).gerar(CONTEXTO, Canal.WHATSAPP))
