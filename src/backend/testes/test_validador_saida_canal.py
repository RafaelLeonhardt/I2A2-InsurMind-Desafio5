"""Testes do validador determinístico de saída por canal (GERAR-01, 02, 03, 07, 08, 09).

As fronteiras usadas aqui são exatamente os defaults documentados na spec: WhatsApp 1024,
SMS 160, assunto de e-mail 78 e corpo de e-mail 2000 caracteres. Cada canal é exercitado um
caractere abaixo do limite, exatamente no limite e um caractere acima (GERAR-03).
"""

import pytest

from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.validador_saida_canal import (
    Canal,
    LimitesCanal,
    SaidaCanal,
    ValidadorSaidaCanal,
)

LIMITE_WHATSAPP = 1024
LIMITE_SMS = 160
LIMITE_ASSUNTO_EMAIL = 78
LIMITE_CORPO_EMAIL = 2000

LIMITES_PADRAO = LimitesCanal(
    whatsapp=LIMITE_WHATSAPP,
    sms=LIMITE_SMS,
    assunto_email=LIMITE_ASSUNTO_EMAIL,
    corpo_email=LIMITE_CORPO_EMAIL,
)

ASSUNTO_VALIDO = "Alerta preventivo de chuva intensa"


def validador(limites: LimitesCanal = LIMITES_PADRAO) -> ValidadorSaidaCanal:
    """Monta o validador com os limites informados, sem nenhum valor implícito."""

    return ValidadorSaidaCanal(limites)


def saida(canal: Canal, corpo: str, assunto: str = ASSUNTO_VALIDO) -> SaidaCanal:
    """Monta a saída estruturada do canal: e-mail leva assunto, os demais só corpo."""

    if canal is Canal.EMAIL:
        return SaidaCanal(corpo=corpo, assunto=assunto)
    return SaidaCanal(corpo=corpo)


def test_limites_padrao_da_configuracao_sao_os_documentados_na_spec() -> None:
    """GERAR-01: os limites são configuráveis, com os defaults documentados da demonstração."""

    configuracao = Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        _env_file=None,
    )

    assert configuracao.limite_caracteres_whatsapp == LIMITE_WHATSAPP
    assert configuracao.limite_caracteres_sms == LIMITE_SMS
    assert configuracao.limite_caracteres_assunto_email == LIMITE_ASSUNTO_EMAIL
    assert configuracao.limite_caracteres_corpo_email == LIMITE_CORPO_EMAIL


@pytest.mark.parametrize(
    ("canal", "limite"),
    [
        (Canal.WHATSAPP, LIMITE_WHATSAPP),
        (Canal.SMS, LIMITE_SMS),
        (Canal.EMAIL, LIMITE_CORPO_EMAIL),
    ],
)
def test_corpo_um_caractere_abaixo_do_limite_e_valido(canal: Canal, limite: int) -> None:
    """GERAR-03: fronteira inferior de cada canal."""

    resultado = validador().validar(canal, saida(canal, "a" * (limite - 1)))

    assert resultado.valida is True
    assert resultado.motivo is None


@pytest.mark.parametrize(
    ("canal", "limite"),
    [
        (Canal.WHATSAPP, LIMITE_WHATSAPP),
        (Canal.SMS, LIMITE_SMS),
        (Canal.EMAIL, LIMITE_CORPO_EMAIL),
    ],
)
def test_corpo_exatamente_no_limite_e_valido(canal: Canal, limite: int) -> None:
    """GERAR-03: o limite é inclusivo — exatamente no limite ainda é válido."""

    resultado = validador().validar(canal, saida(canal, "a" * limite))

    assert resultado.valida is True
    assert resultado.motivo is None


@pytest.mark.parametrize(
    ("canal", "limite"),
    [
        (Canal.WHATSAPP, LIMITE_WHATSAPP),
        (Canal.SMS, LIMITE_SMS),
        (Canal.EMAIL, LIMITE_CORPO_EMAIL),
    ],
)
def test_corpo_um_caractere_acima_do_limite_e_invalido_com_motivo(
    canal: Canal, limite: int
) -> None:
    """GERAR-03, GERAR-09: um caractere acima é recusado, com o motivo persistível."""

    resultado = validador().validar(canal, saida(canal, "a" * (limite + 1)))

    assert resultado.valida is False
    assert resultado.motivo == f"limite_excedido:corpo:{limite + 1}:{limite}"


def test_assunto_de_email_um_caractere_abaixo_do_limite_e_valido() -> None:
    """GERAR-03, GERAR-08: o assunto tem fronteira própria, separada do corpo."""

    resultado = validador().validar(
        Canal.EMAIL,
        SaidaCanal(corpo="Corpo válido do e-mail.", assunto="a" * (LIMITE_ASSUNTO_EMAIL - 1)),
    )

    assert resultado.valida is True
    assert resultado.motivo is None


def test_assunto_de_email_exatamente_no_limite_e_valido() -> None:
    """GERAR-03, GERAR-08: fronteira exata do assunto."""

    resultado = validador().validar(
        Canal.EMAIL,
        SaidaCanal(corpo="Corpo válido do e-mail.", assunto="a" * LIMITE_ASSUNTO_EMAIL),
    )

    assert resultado.valida is True
    assert resultado.motivo is None


def test_assunto_de_email_um_caractere_acima_do_limite_e_invalido_com_motivo() -> None:
    """GERAR-03, GERAR-08, GERAR-09: assunto acima do limite não avança."""

    resultado = validador().validar(
        Canal.EMAIL,
        SaidaCanal(corpo="Corpo válido do e-mail.", assunto="a" * (LIMITE_ASSUNTO_EMAIL + 1)),
    )

    assert resultado.valida is False
    assert resultado.motivo == (
        f"limite_excedido:assunto:{LIMITE_ASSUNTO_EMAIL + 1}:{LIMITE_ASSUNTO_EMAIL}"
    )


@pytest.mark.parametrize("canal", [Canal.WHATSAPP, Canal.SMS, Canal.EMAIL])
@pytest.mark.parametrize("corpo", ["", "   ", "\n\t "])
def test_corpo_ausente_ou_em_branco_e_campo_obrigatorio_ausente(canal: Canal, corpo: str) -> None:
    """Edge case da spec: saída estruturalmente válida com corpo em branco nunca é sucesso."""

    resultado = validador().validar(canal, saida(canal, corpo))

    assert resultado.valida is False
    assert resultado.motivo == "campo_obrigatorio_ausente:corpo"


@pytest.mark.parametrize("assunto", ["", "   "])
def test_email_sem_assunto_e_campo_obrigatorio_ausente(assunto: str) -> None:
    """GERAR-08: o e-mail exige assunto e corpo; sem assunto a saída é inválida."""

    resultado = validador().validar(
        Canal.EMAIL, SaidaCanal(corpo="Corpo válido do e-mail.", assunto=assunto)
    )

    assert resultado.valida is False
    assert resultado.motivo == "campo_obrigatorio_ausente:assunto"


def test_email_com_assunto_nulo_e_campo_obrigatorio_ausente() -> None:
    """GERAR-08: assunto nulo (campo não devolvido pelo modelo) é ausência, não sucesso."""

    resultado = validador().validar(Canal.EMAIL, SaidaCanal(corpo="Corpo válido.", assunto=None))

    assert resultado.valida is False
    assert resultado.motivo == "campo_obrigatorio_ausente:assunto"


@pytest.mark.parametrize("canal", [Canal.WHATSAPP, Canal.SMS])
def test_whatsapp_e_sms_validam_apenas_o_corpo(canal: Canal) -> None:
    """GERAR-07: WhatsApp e SMS têm corpo como único campo obrigatório."""

    resultado = validador().validar(canal, SaidaCanal(corpo="Recolha o veículo antes do granizo."))

    assert resultado.valida is True
    assert resultado.motivo is None


@pytest.mark.parametrize("canal", [Canal.WHATSAPP, Canal.SMS, Canal.EMAIL])
def test_saida_ausente_e_invalida_com_motivo_proprio(canal: Canal) -> None:
    """GERAR-09: saída ausente é recusada, com motivo distinto de campo em branco."""

    resultado = validador().validar(canal, None)

    assert resultado.valida is False
    assert resultado.motivo == "saida_ausente"


def test_contagem_e_de_caracteres_unicode_e_nao_de_bytes() -> None:
    """GERAR-01: a unidade é o caractere Unicode do texto final, não o byte.

    160 caracteres acentuados ocupam 320 bytes em UTF-8; contados como bytes, um SMS
    exatamente no limite seria recusado.
    """

    corpo = "á" * LIMITE_SMS

    assert len(corpo.encode("utf-8")) > LIMITE_SMS
    assert validador().validar(Canal.SMS, SaidaCanal(corpo=corpo)).valida is True
    assert validador().validar(Canal.SMS, SaidaCanal(corpo="á" * (LIMITE_SMS + 1))).valida is False


def test_limites_configurados_substituem_os_defaults() -> None:
    """GERAR-01: o limite é configurável — o validador cobra o valor recebido, não 160."""

    limites = LimitesCanal(whatsapp=10, sms=5, assunto_email=4, corpo_email=8)

    assert validador(limites).validar(Canal.SMS, SaidaCanal(corpo="a" * 5)).valida is True
    resultado = validador(limites).validar(Canal.SMS, SaidaCanal(corpo="a" * 6))
    assert resultado.valida is False
    assert resultado.motivo == "limite_excedido:corpo:6:5"


@pytest.mark.parametrize(
    ("canal", "limite_corpo", "limite_assunto"),
    [
        (Canal.WHATSAPP, LIMITE_WHATSAPP, None),
        (Canal.SMS, LIMITE_SMS, None),
        (Canal.EMAIL, LIMITE_CORPO_EMAIL, LIMITE_ASSUNTO_EMAIL),
    ],
)
def test_limite_do_canal_e_consultavel_antes_da_geracao(
    canal: Canal, limite_corpo: int, limite_assunto: int | None
) -> None:
    """GERAR-02: o mesmo limite cobrado depois é exposto antes, para instruir a geração."""

    assert validador().limite_corpo(canal) == limite_corpo
    assert validador().limite_assunto(canal) == limite_assunto
