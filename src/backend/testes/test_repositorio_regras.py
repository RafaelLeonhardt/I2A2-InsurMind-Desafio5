"""Testes do `RepositorioRegras`: leitura da regra ativa por tipo de evento."""

from pathlib import Path
from uuid import uuid4

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_regras import RepositorioRegras
from central_preventiva.dominio.evento_meteorologico import TipoEventoMeteorologico


def preparar_banco(tmp_path: Path) -> Path:
    """Aplica as migrações versionadas em um arquivo temporário, sem semear dados."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def inserir_regra(
    caminho: Path,
    evento_tipo: str,
    limiar: float,
    area_aplicavel: str,
    apolice_tipo: str,
    versao: int = 1,
    estado: str = "ativa",
) -> str:
    """Insere uma regra de teste, fora do fluxo do semeador canônico."""

    id_regra = str(uuid4())
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
            "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
            "VALUES (?, ?, ?, ?, ?, 'cobertura-teste', 24, 'whatsapp', ?, ?)",
            [id_regra, evento_tipo, limiar, area_aplicavel, apolice_tipo, versao, estado],
        )
    return id_regra


def test_obter_ativa_resolve_a_regra_do_tipo_com_estado_ativa(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_regra = inserir_regra(caminho, "chuva_intensa", 50.0, "9990001", "residencial")

    regra = RepositorioRegras(caminho).obter_ativa(TipoEventoMeteorologico.CHUVA_INTENSA)

    assert regra is not None
    assert str(regra.id) == id_regra
    assert regra.limiar_meteorologico == 50.0
    assert regra.area_aplicavel == "9990001"
    assert regra.apolice_tipo == "residencial"
    assert regra.versao == 1


def test_obter_ativa_sem_nenhuma_regra_do_tipo_devolve_none(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    regra = RepositorioRegras(caminho).obter_ativa(TipoEventoMeteorologico.GRANIZO)

    assert regra is None


def test_obter_ativa_ignora_regra_substituida(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    inserir_regra(
        caminho, "granizo", 10.0, "9990002", "automovel", versao=1, estado="substituida"
    )
    id_ativa = inserir_regra(
        caminho, "granizo", 20.0, "9990002", "automovel", versao=2, estado="ativa"
    )

    regra = RepositorioRegras(caminho).obter_ativa(TipoEventoMeteorologico.GRANIZO)

    assert regra is not None
    assert str(regra.id) == id_ativa
    assert regra.versao == 2
