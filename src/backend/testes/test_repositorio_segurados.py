"""Testes do repositório de consulta somente leitura de segurados sintéticos."""

from pathlib import Path
from uuid import uuid4

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_segurados import (
    RepositorioSegurados,
)


def preparar_banco(tmp_path: Path) -> Path:
    """Cria o schema versionado em um arquivo temporário e devolve seu caminho."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def inserir_segurado(
    caminho: Path,
    id: object,
    nome: str,
    canal_preferido: str = "whatsapp",
    participa_de_alertas: bool = True,
) -> None:
    """Insere um segurado sintético mínimo para os testes do repositório."""

    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO segurados (id, nome, codigo_ibge_area, canal_preferido, "
            "participa_de_alertas) VALUES (?, ?, ?, ?, ?)",
            [id, nome, "9990001", canal_preferido, participa_de_alertas],
        )


def test_buscar_por_id_encontra_o_segurado_existente(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    identificador = uuid4()
    inserir_segurado(caminho, identificador, "Pessoa Segurada Sintética DEMO-001")

    encontrado = RepositorioSegurados(caminho).buscar_por_id(identificador)

    assert encontrado is not None
    assert encontrado.id == identificador
    assert encontrado.nome == "Pessoa Segurada Sintética DEMO-001"


def test_buscar_por_id_devolve_none_quando_o_id_nao_existe(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    encontrado = RepositorioSegurados(caminho).buscar_por_id(uuid4())

    assert encontrado is None


def test_buscar_por_id_devolve_none_com_tabela_vazia(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    encontrado = RepositorioSegurados(caminho).buscar_por_id(uuid4())

    assert encontrado is None


def test_buscar_preferencias_por_id_encontra_canal_e_participacao(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    identificador = uuid4()
    inserir_segurado(
        caminho, identificador, "Pessoa Teste", canal_preferido="sms",
        participa_de_alertas=False,
    )

    encontrado = RepositorioSegurados(caminho).buscar_preferencias_por_id(identificador)

    assert encontrado is not None
    assert encontrado.canal_preferido == "sms"
    assert encontrado.participa_de_alertas is False


def test_buscar_preferencias_por_id_devolve_none_quando_o_id_nao_existe(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)

    encontrado = RepositorioSegurados(caminho).buscar_preferencias_por_id(uuid4())

    assert encontrado is None
