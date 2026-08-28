"""Testes do semeador reproduzível de dados sintéticos."""

import re
from dataclasses import replace
from pathlib import Path

import duckdb
import pytest

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.semeador import (
    MARCADOR_DEMONSTRACAO,
    ConjuntoSintetico,
    SemeadorDadosSinteticos,
    dataset_sintetico_v1,
    identificador_demonstracao,
)

PADRAO_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PADRAO_TELEFONE = re.compile(r"\+?\d{2}[\s(-]*\d{2}[\s)-]*\d{4,5}-?\d{4}")
PADRAO_CPF_CNPJ = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}|\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")
PADRAO_URL = re.compile(r"https?://")


def preparar_banco(tmp_path: Path) -> Path:
    """Cria o schema versionado em um arquivo temporário e devolve seu caminho."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def elegibilidades(caminho: Path) -> list[tuple[str, bool]]:
    """Lê o par tipo de evento/elegibilidade de cada elegibilidade histórica semeada."""

    with abrir_conexao(caminho) as conexao:
        return [
            (str(tipo), bool(elegivel))
            for tipo, elegivel in conexao.execute(
                "SELECT e.tipo, h.elegivel FROM elegibilidades_historicas h "
                "JOIN eventos_meteorologicos e ON e.id = h.evento_id"
            ).fetchall()
        ]


def contagens(caminho: Path) -> dict[str, int]:
    """Conta as linhas de cada tabela do conjunto sintético."""

    with abrir_conexao(caminho) as conexao:
        return {
            tabela.nome: int(
                (conexao.execute(f"SELECT count(*) FROM {tabela.nome}").fetchone() or (0,))[0]
            )
            for tabela in dataset_sintetico_v1().tabelas
        }


def textos_do_dataset() -> list[str]:
    """Extrai todos os valores textuais do conjunto sintético canônico."""

    return [
        str(valor)
        for tabela in dataset_sintetico_v1().tabelas
        for linha in tabela.linhas
        for celula in linha
        for valor in (celula if isinstance(celula, list) else [celula])
        if isinstance(valor, str)
    ]


def test_esta_semeado_e_falso_antes_e_verdadeiro_depois_de_semear(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    semeador = SemeadorDadosSinteticos(caminho)

    assert semeador.esta_semeado() is False

    semeador.semear()

    assert semeador.esta_semeado() is True


def test_esta_semeado_e_falso_sem_schema_aplicado(tmp_path: Path) -> None:
    semeador = SemeadorDadosSinteticos(tmp_path / "central_preventiva.duckdb")

    assert semeador.esta_semeado() is False


def test_semeia_casos_elegiveis_e_nao_elegiveis_para_chuva_e_granizo(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    SemeadorDadosSinteticos(caminho).semear()

    registradas = elegibilidades(caminho)
    assert ("chuva_intensa", True) in registradas
    assert ("chuva_intensa", False) in registradas
    assert ("granizo", True) in registradas
    assert ("granizo", False) in registradas


def test_identificadores_semeados_sao_inequivocamente_ficticios(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    SemeadorDadosSinteticos(caminho).semear()

    with abrir_conexao(caminho) as conexao:
        numeros = [
            str(numero) for (numero,) in conexao.execute("SELECT numero FROM apolices").fetchall()
        ]
        nomes = [str(nome) for (nome,) in conexao.execute("SELECT nome FROM segurados").fetchall()]
        identificadores = {
            str(identificador)
            for (identificador,) in conexao.execute("SELECT id FROM segurados").fetchall()
        }

    assert numeros and all(numero.startswith(MARCADOR_DEMONSTRACAO) for numero in numeros)
    assert nomes and all(MARCADOR_DEMONSTRACAO in nome for nome in nomes)
    assert str(identificador_demonstracao("segurado/chuva-elegivel")) in identificadores


def test_dataset_nao_contem_dado_pessoal_credencial_ou_contato_utilizavel() -> None:
    textos = textos_do_dataset()

    assert textos
    for texto in textos:
        assert PADRAO_EMAIL.search(texto) is None
        assert PADRAO_TELEFONE.search(texto) is None
        assert PADRAO_CPF_CNPJ.search(texto) is None
        assert PADRAO_URL.search(texto) is None


def test_restaurar_repoe_linha_alterada_no_conteudo_canonico(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    semeador = SemeadorDadosSinteticos(caminho)
    semeador.semear()
    contagens_originais = contagens(caminho)
    with abrir_conexao(caminho) as conexao:
        conexao.execute("UPDATE segurados SET nome = 'alterado localmente'")

    semeador.restaurar()

    with abrir_conexao(caminho) as conexao:
        nomes = [str(nome) for (nome,) in conexao.execute("SELECT nome FROM segurados").fetchall()]
    assert "alterado localmente" not in nomes
    assert "Pessoa Segurada Sintética DEMO-001" in nomes
    assert contagens(caminho) == contagens_originais


def test_restaurar_nao_duplica_registros(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    semeador = SemeadorDadosSinteticos(caminho)
    semeador.semear()
    contagens_originais = contagens(caminho)

    semeador.restaurar()
    semeador.restaurar()

    assert contagens(caminho) == contagens_originais


def test_falha_no_meio_da_restauracao_preserva_o_conjunto_anterior(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    SemeadorDadosSinteticos(caminho).semear()
    contagens_originais = contagens(caminho)
    with abrir_conexao(caminho) as conexao:
        nomes_originais = sorted(
            str(nome) for (nome,) in conexao.execute("SELECT nome FROM segurados").fetchall()
        )

    canonico = dataset_sintetico_v1()
    corrompida = replace(
        canonico.tabelas[1],
        linhas=(
            tuple(
                "situacao_invalida" if valor == "ativa" else valor
                for valor in canonico.tabelas[1].linhas[0]
            ),
        ),
    )
    defeituoso = SemeadorDadosSinteticos(
        caminho,
        ConjuntoSintetico(tabelas=(canonico.tabelas[0], corrompida) + canonico.tabelas[2:]),
    )

    with pytest.raises(duckdb.Error):
        defeituoso.restaurar()

    assert contagens(caminho) == contagens_originais
    with abrir_conexao(caminho) as conexao:
        preservados = sorted(
            str(nome) for (nome,) in conexao.execute("SELECT nome FROM segurados").fetchall()
        )
    assert preservados == nomes_originais


def test_semear_e_restaurar_compartilham_o_mesmo_conjunto_canonico(tmp_path: Path) -> None:
    caminho_semeado = preparar_banco(tmp_path / "a")
    caminho_restaurado = preparar_banco(tmp_path / "b")
    SemeadorDadosSinteticos(caminho_semeado).semear()
    semeador_restaurado = SemeadorDadosSinteticos(caminho_restaurado)
    semeador_restaurado.semear()

    semeador_restaurado.restaurar()

    with abrir_conexao(caminho_semeado) as conexao:
        semeado = conexao.execute("SELECT id, nome FROM segurados ORDER BY nome").fetchall()
    with abrir_conexao(caminho_restaurado) as conexao:
        restaurado = conexao.execute("SELECT id, nome FROM segurados ORDER BY nome").fetchall()
    assert semeado == restaurado
