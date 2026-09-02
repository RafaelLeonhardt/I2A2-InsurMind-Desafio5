"""Testes do `RepositorioRegras`: leitura e escrita versionada de `regras` (2.3/2.4)."""

from pathlib import Path
from uuid import UUID, uuid4

import pytest

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_regras import (
    ConflitoVersao,
    RepositorioRegras,
)
from central_preventiva.dominio.evento_meteorologico import TipoEventoMeteorologico
from central_preventiva.dominio.validador_regra import DadosRegra


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


DADOS_NOVA_VERSAO_CHUVA = DadosRegra(
    evento_tipo="chuva_intensa",
    limiar_meteorologico=60.0,
    area_aplicavel="9990001",
    apolice_tipo="residencial",
    cobertura_exigida="alagamento",
    antecedencia_horas=48,
    canal="email",
)


def test_criar_nova_versao_com_versao_esperada_correta_substitui_a_anterior(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    id_anterior = inserir_regra(caminho, "chuva_intensa", 50.0, "9990001", "residencial")

    nova = RepositorioRegras(caminho).criar_nova_versao(
        UUID(id_anterior), versao_esperada=1, dados=DADOS_NOVA_VERSAO_CHUVA
    )

    assert nova.versao == 2
    assert nova.estado == "ativa"
    assert nova.limiar_meteorologico == 60.0
    assert nova.canal == "email"

    anterior = RepositorioRegras(caminho).obter_por_id(UUID(id_anterior))
    assert anterior is not None
    assert anterior.estado == "substituida"

    ativa = RepositorioRegras(caminho).obter_ativa(TipoEventoMeteorologico.CHUVA_INTENSA)
    assert ativa is not None
    assert ativa.id == nova.id
    assert ativa.versao == 2


def test_criar_nova_versao_com_versao_esperada_incorreta_levanta_conflito_sem_mutar(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    id_anterior = inserir_regra(caminho, "chuva_intensa", 50.0, "9990001", "residencial")

    with pytest.raises(ConflitoVersao):
        RepositorioRegras(caminho).criar_nova_versao(
            UUID(id_anterior), versao_esperada=99, dados=DADOS_NOVA_VERSAO_CHUVA
        )

    anterior = RepositorioRegras(caminho).obter_por_id(UUID(id_anterior))
    assert anterior is not None
    assert anterior.estado == "ativa"
    assert anterior.versao == 1
    assert len(RepositorioRegras(caminho).listar()) == 1


def test_listar_retorna_versoes_anteriores_inalteradas(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_substituida = inserir_regra(
        caminho, "granizo", 10.0, "9990002", "automovel", versao=1, estado="substituida"
    )
    id_ativa = inserir_regra(
        caminho, "granizo", 20.0, "9990002", "automovel", versao=2, estado="ativa"
    )

    regras = RepositorioRegras(caminho).listar(TipoEventoMeteorologico.GRANIZO)

    ids = {str(regra.id) for regra in regras}
    assert ids == {id_substituida, id_ativa}
    substituida = next(r for r in regras if str(r.id) == id_substituida)
    assert substituida.estado == "substituida"
    assert substituida.limiar_meteorologico == 10.0


def test_obter_por_id_de_regra_inexistente_devolve_none(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    assert RepositorioRegras(caminho).obter_por_id(uuid4()) is None
