"""Testes do repositório de leitura da apólice sintética (APOLICE-01, 5.3)."""

from pathlib import Path
from uuid import UUID, uuid4

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_apolices import (
    RepositorioApolices,
)

AREA = "9990001"


def preparar_banco(tmp_path: Path) -> Path:
    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def inserir_segurado(caminho: Path) -> str:
    id_segurado = str(uuid4())
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO segurados (id, nome, codigo_ibge_area, canal_preferido, "
            "participa_de_alertas) VALUES (?, 'Pessoa Teste', ?, 'whatsapp', true)",
            [id_segurado, AREA],
        )
    return id_segurado


def inserir_apolice(
    caminho: Path,
    segurado_id: str,
    numero: str = "RES-0001",
    tipo: str = "residencial",
    situacao: str = "ativa",
    coberturas: tuple[str, ...] = ("alagamento",),
    vigencia_inicio: str = "2026-01-01",
    vigencia_fim: str = "2026-12-31",
) -> str:
    id_apolice = str(uuid4())
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO apolices (id, segurado_id, numero, tipo, situacao, "
            "vigencia_inicio, vigencia_fim, coberturas, endereco_risco_sintetico, "
            "codigo_ibge_area) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Rua Teste, 123', ?)",
            [
                id_apolice, segurado_id, numero, tipo, situacao, vigencia_inicio,
                vigencia_fim, list(coberturas), AREA,
            ],
        )
    return id_apolice


def test_buscar_por_segurado_encontra_a_apolice_do_segurado(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_segurado = inserir_segurado(caminho)
    id_apolice = inserir_apolice(caminho, id_segurado)

    encontrada = RepositorioApolices(caminho).buscar_por_segurado(UUID(id_segurado))

    assert encontrada is not None
    assert str(encontrada.id) == id_apolice
    assert encontrada.numero == "RES-0001"
    assert encontrada.tipo == "residencial"
    assert encontrada.situacao == "ativa"
    assert encontrada.coberturas == ("alagamento",)
    assert encontrada.endereco_risco_sintetico == "Rua Teste, 123"
    assert encontrada.codigo_ibge_area == AREA
    assert str(encontrada.vigencia_inicio) == "2026-01-01"
    assert str(encontrada.vigencia_fim) == "2026-12-31"


def test_buscar_por_segurado_devolve_none_sem_nenhuma_apolice(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_segurado = inserir_segurado(caminho)

    encontrada = RepositorioApolices(caminho).buscar_por_segurado(
        UUID(id_segurado)
    )

    assert encontrada is None


def test_buscar_por_segurado_resolve_a_mais_recente_quando_ha_mais_de_uma(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    id_segurado = inserir_segurado(caminho)
    inserir_apolice(caminho, id_segurado, numero="ANTIGA")
    id_recente = inserir_apolice(caminho, id_segurado, numero="RECENTE")
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "UPDATE apolices SET criado_em = '2020-01-01 00:00:00' WHERE numero = 'ANTIGA'"
        )
        conexao.execute(
            "UPDATE apolices SET criado_em = '2030-01-01 00:00:00' WHERE numero = 'RECENTE'"
        )

    encontrada = RepositorioApolices(caminho).buscar_por_segurado(
        UUID(id_segurado)
    )

    assert encontrada is not None
    assert str(encontrada.id) == id_recente


def test_buscar_por_id_encontra_a_apolice(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_segurado = inserir_segurado(caminho)
    id_apolice = inserir_apolice(caminho, id_segurado)

    encontrada = RepositorioApolices(caminho).buscar_por_id(
        UUID(id_apolice)
    )

    assert encontrada is not None
    assert str(encontrada.id) == id_apolice


def test_buscar_por_id_devolve_none_para_id_inexistente(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    encontrada = RepositorioApolices(caminho).buscar_por_id(uuid4())

    assert encontrada is None
