"""Testes do repositório de consulta somente leitura de segurados sintéticos."""

from pathlib import Path
from uuid import uuid4

import pytest

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_segurados import (
    ConflitoVersao,
    RepositorioSegurados,
    SeguradoDetalhado,
)
from central_preventiva.dominio.validador_saida_canal import Canal


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


def inserir_apolice(
    caminho: Path,
    segurado_id: object,
    numero: str,
    criado_em: str = "2026-01-01 00:00:00",
) -> None:
    """Insere uma apólice sintética mínima ligada ao segurado, com `criado_em` controlado
    para testar a dedup por recência de `listar_sinteticos_detalhado`."""

    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO apolices (id, segurado_id, numero, tipo, situacao, "
            "vigencia_inicio, vigencia_fim, coberturas, endereco_risco_sintetico, "
            "codigo_ibge_area, criado_em) VALUES "
            "(?, ?, ?, 'residencial', 'ativa', '2026-01-01', '2026-12-31', "
            "['alagamento'], 'Rua Teste, 123', '9990001', ?)",
            [uuid4(), segurado_id, numero, criado_em],
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
    assert encontrado.versao == 1


def test_buscar_preferencias_por_id_devolve_none_quando_o_id_nao_existe(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)

    encontrado = RepositorioSegurados(caminho).buscar_preferencias_por_id(uuid4())

    assert encontrado is None


def test_atualizar_preferencias_com_versao_correta_persiste_e_incrementa(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    identificador = uuid4()
    inserir_segurado(
        caminho, identificador, "Pessoa Teste", canal_preferido="whatsapp",
        participa_de_alertas=True,
    )

    atualizado = RepositorioSegurados(caminho).atualizar_preferencias(
        identificador,
        versao_esperada=1,
        canal_preferido=Canal.SMS,
        participa_de_alertas=False,
    )

    assert atualizado.canal_preferido == "sms"
    assert atualizado.participa_de_alertas is False
    assert atualizado.versao == 2

    persistido = RepositorioSegurados(caminho).buscar_preferencias_por_id(identificador)
    assert persistido == atualizado


def test_listar_sinteticos_devolve_todos_os_segurados_do_seed_ordenados_por_nome(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    id_b = uuid4()
    id_a = uuid4()
    inserir_segurado(caminho, id_b, "Pessoa Segurada Sintética DEMO-002")
    inserir_segurado(caminho, id_a, "Pessoa Segurada Sintética DEMO-001")

    listados = RepositorioSegurados(caminho).listar_sinteticos()

    assert [segurado.id for segurado in listados] == [id_a, id_b]
    assert [segurado.nome for segurado in listados] == [
        "Pessoa Segurada Sintética DEMO-001",
        "Pessoa Segurada Sintética DEMO-002",
    ]


def test_listar_sinteticos_devolve_lista_vazia_com_seed_ausente(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    listados = RepositorioSegurados(caminho).listar_sinteticos()

    assert listados == []


def test_atualizar_preferencias_com_versao_incorreta_levanta_conflito_sem_mutar(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    identificador = uuid4()
    inserir_segurado(
        caminho, identificador, "Pessoa Teste", canal_preferido="whatsapp",
        participa_de_alertas=True,
    )

    with pytest.raises(ConflitoVersao):
        RepositorioSegurados(caminho).atualizar_preferencias(
            identificador,
            versao_esperada=99,
            canal_preferido=Canal.SMS,
            participa_de_alertas=False,
        )

    inalterado = RepositorioSegurados(caminho).buscar_preferencias_por_id(identificador)
    assert inalterado is not None
    assert inalterado.canal_preferido == "whatsapp"
    assert inalterado.participa_de_alertas is True
    assert inalterado.versao == 1


def test_listar_sinteticos_detalhado_devolve_lista_vazia_com_seed_ausente(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)

    listados = RepositorioSegurados(caminho).listar_sinteticos_detalhado()

    assert listados == []


def test_listar_sinteticos_detalhado_traz_area_canal_e_apolice_do_segurado(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    identificador = uuid4()
    inserir_segurado(caminho, identificador, "Pessoa Teste", canal_preferido="sms")
    inserir_apolice(caminho, identificador, numero="RES-0001")

    listados = RepositorioSegurados(caminho).listar_sinteticos_detalhado()

    assert listados == [
        SeguradoDetalhado(
            id=identificador,
            nome="Pessoa Teste",
            codigo_ibge_area="9990001",
            canal_preferido="sms",
            apolice_numero="RES-0001",
        )
    ]


def test_listar_sinteticos_detalhado_mantem_segurado_sem_apolice_com_numero_nulo(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    identificador = uuid4()
    inserir_segurado(caminho, identificador, "Pessoa Sem Apólice")

    listados = RepositorioSegurados(caminho).listar_sinteticos_detalhado()

    assert len(listados) == 1
    assert listados[0].id == identificador
    assert listados[0].apolice_numero is None


def test_listar_sinteticos_detalhado_com_multiplas_apolices_mantem_so_a_mais_recente(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    identificador = uuid4()
    inserir_segurado(caminho, identificador, "Pessoa Com Renovação")
    inserir_apolice(caminho, identificador, numero="RES-ANTIGA", criado_em="2025-01-01 00:00:00")
    inserir_apolice(caminho, identificador, numero="RES-NOVA", criado_em="2026-06-01 00:00:00")

    listados = RepositorioSegurados(caminho).listar_sinteticos_detalhado()

    assert len(listados) == 1
    assert listados[0].apolice_numero == "RES-NOVA"


def test_listar_sinteticos_detalhado_ordena_por_nome_com_varios_segurados(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    id_b = uuid4()
    id_a = uuid4()
    inserir_segurado(caminho, id_b, "Pessoa Segurada Sintética DEMO-002")
    inserir_segurado(caminho, id_a, "Pessoa Segurada Sintética DEMO-001")

    listados = RepositorioSegurados(caminho).listar_sinteticos_detalhado()

    assert [segurado.id for segurado in listados] == [id_a, id_b]
