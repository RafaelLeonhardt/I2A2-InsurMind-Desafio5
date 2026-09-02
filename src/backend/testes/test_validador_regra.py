"""Testes do `ValidadorRegra`: cada classe de invalidez produz um erro específico (REGRA-05/06)."""

from central_preventiva.dominio.validador_regra import DadosRegra, validar

DADOS_CHUVA_VALIDOS = DadosRegra(
    evento_tipo="chuva_intensa",
    limiar_meteorologico=50.0,
    area_aplicavel="9990001",
    apolice_tipo="residencial",
    cobertura_exigida="alagamento",
    antecedencia_horas=24,
    canal="whatsapp",
)


def test_configuracao_valida_nao_produz_erro() -> None:
    resultado = validar(DADOS_CHUVA_VALIDOS)

    assert resultado.valida is True
    assert resultado.erros == ()


def test_configuracao_valida_de_granizo_nao_produz_erro() -> None:
    dados = DadosRegra(
        evento_tipo="granizo",
        limiar_meteorologico=20.0,
        area_aplicavel="9990002",
        apolice_tipo="automovel",
        cobertura_exigida="granizo",
        antecedencia_horas=12,
        canal="sms",
    )

    resultado = validar(dados)

    assert resultado.valida is True
    assert resultado.erros == ()


def test_tipo_de_evento_invalido_produz_erro_no_campo_evento_tipo() -> None:
    from dataclasses import replace

    dados = replace(DADOS_CHUVA_VALIDOS, evento_tipo="vendaval")

    resultado = validar(dados)

    assert resultado.valida is False
    assert any(erro.campo == "evento_tipo" for erro in resultado.erros)


def test_tipo_de_apolice_invalido_produz_erro_no_campo_apolice_tipo() -> None:
    from dataclasses import replace

    dados = replace(DADOS_CHUVA_VALIDOS, apolice_tipo="vida")

    resultado = validar(dados)

    assert resultado.valida is False
    assert any(erro.campo == "apolice_tipo" for erro in resultado.erros)


def test_limiar_meteorologico_com_tipo_python_errado_produz_erro() -> None:
    from dataclasses import replace

    dados = replace(DADOS_CHUVA_VALIDOS, limiar_meteorologico="cinquenta")  # type: ignore[arg-type]

    resultado = validar(dados)

    assert resultado.valida is False
    assert any(erro.campo == "limiar_meteorologico" for erro in resultado.erros)


def test_antecedencia_horas_com_tipo_python_errado_produz_erro() -> None:
    from dataclasses import replace

    dados = replace(DADOS_CHUVA_VALIDOS, antecedencia_horas=24.5)  # type: ignore[arg-type]

    resultado = validar(dados)

    assert resultado.valida is False
    assert any(erro.campo == "antecedencia_horas" for erro in resultado.erros)


def test_limiar_meteorologico_zero_ou_negativo_produz_erro_de_faixa() -> None:
    from dataclasses import replace

    dados = replace(DADOS_CHUVA_VALIDOS, limiar_meteorologico=0.0)

    resultado = validar(dados)

    assert resultado.valida is False
    assert any(
        erro.campo == "limiar_meteorologico" and "maior que zero" in erro.motivo
        for erro in resultado.erros
    )


def test_antecedencia_horas_fora_da_faixa_produz_erro() -> None:
    from dataclasses import replace

    dados = replace(DADOS_CHUVA_VALIDOS, antecedencia_horas=200)

    resultado = validar(dados)

    assert resultado.valida is False
    assert any(erro.campo == "antecedencia_horas" for erro in resultado.erros)


def test_antecedencia_horas_imediatamente_abaixo_e_acima_da_fronteira_produz_erro() -> None:
    """REGRA-02: exemplos imediatamente abaixo (0) e acima (169) da fronteira [1, 168]."""

    from dataclasses import replace

    dados_abaixo = replace(DADOS_CHUVA_VALIDOS, antecedencia_horas=0)
    dados_acima = replace(DADOS_CHUVA_VALIDOS, antecedencia_horas=169)

    assert validar(dados_abaixo).valida is False
    assert any(erro.campo == "antecedencia_horas" for erro in validar(dados_abaixo).erros)
    assert validar(dados_acima).valida is False
    assert any(erro.campo == "antecedencia_horas" for erro in validar(dados_acima).erros)


def test_antecedencia_horas_no_limite_inferior_e_superior_e_valida() -> None:
    from dataclasses import replace

    dados_minimo = replace(DADOS_CHUVA_VALIDOS, antecedencia_horas=1)
    dados_maximo = replace(DADOS_CHUVA_VALIDOS, antecedencia_horas=168)

    assert validar(dados_minimo).valida is True
    assert validar(dados_maximo).valida is True


def test_area_aplicavel_vazia_produz_erro_de_combinacao_obrigatoria() -> None:
    from dataclasses import replace

    dados = replace(DADOS_CHUVA_VALIDOS, area_aplicavel="   ")

    resultado = validar(dados)

    assert resultado.valida is False
    assert any(erro.campo == "area_aplicavel" for erro in resultado.erros)


def test_cobertura_exigida_vazia_produz_erro_de_combinacao_obrigatoria() -> None:
    from dataclasses import replace

    dados = replace(DADOS_CHUVA_VALIDOS, cobertura_exigida="")

    resultado = validar(dados)

    assert resultado.valida is False
    assert any(erro.campo == "cobertura_exigida" for erro in resultado.erros)


def test_canal_fora_do_conjunto_valido_produz_erro() -> None:
    from dataclasses import replace

    dados = replace(DADOS_CHUVA_VALIDOS, canal="pombo-correio")

    resultado = validar(dados)

    assert resultado.valida is False
    assert any(erro.campo == "canal" for erro in resultado.erros)


def test_granizo_associado_a_apolice_residencial_produz_erro_de_coerencia() -> None:
    from dataclasses import replace

    dados = replace(
        DADOS_CHUVA_VALIDOS, evento_tipo="granizo", apolice_tipo="residencial", canal="sms"
    )

    resultado = validar(dados)

    assert resultado.valida is False
    erro_coerencia = next(erro for erro in resultado.erros if erro.campo == "apolice_tipo")
    assert "residencial" in erro_coerencia.motivo
    assert "automovel" in erro_coerencia.motivo


def test_chuva_intensa_associada_a_apolice_automovel_produz_erro_de_coerencia() -> None:
    from dataclasses import replace

    dados = replace(DADOS_CHUVA_VALIDOS, apolice_tipo="automovel")

    resultado = validar(dados)

    assert resultado.valida is False
    assert any(erro.campo == "apolice_tipo" for erro in resultado.erros)


def test_multiplos_erros_sao_todos_reportados_de_uma_vez() -> None:
    dados = DadosRegra(
        evento_tipo="vendaval",
        limiar_meteorologico=-5.0,
        area_aplicavel="",
        apolice_tipo="vida",
        cobertura_exigida="",
        antecedencia_horas=999,
        canal="pombo-correio",
    )

    resultado = validar(dados)

    campos_com_erro = {erro.campo for erro in resultado.erros}
    assert resultado.valida is False
    assert campos_com_erro == {
        "evento_tipo",
        "apolice_tipo",
        "limiar_meteorologico",
        "area_aplicavel",
        "cobertura_exigida",
        "antecedencia_horas",
        "canal",
    }
