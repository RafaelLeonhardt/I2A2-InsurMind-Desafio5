"""Testes dos identificadores determinísticos e fictícios da demonstração."""

from central_preventiva.dominio.identificadores_demonstracao import (
    SEGURADO_PADRAO,
    identificador_demonstracao,
)


def test_mesma_entrada_produz_o_mesmo_identificador() -> None:
    assert identificador_demonstracao("segurado/chuva-elegivel") == identificador_demonstracao(
        "segurado/chuva-elegivel"
    )


def test_entradas_diferentes_produzem_identificadores_diferentes() -> None:
    assert identificador_demonstracao("segurado/chuva-elegivel") != identificador_demonstracao(
        "segurado/chuva-nao-elegivel"
    )


def test_segurado_padrao_corresponde_ao_identificador_de_chuva_elegivel() -> None:
    assert SEGURADO_PADRAO == identificador_demonstracao("segurado/chuva-elegivel")
