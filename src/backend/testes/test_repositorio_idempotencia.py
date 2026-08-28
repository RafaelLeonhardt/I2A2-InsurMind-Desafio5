"""Testes do repositório genérico de chaves de idempotência."""

from pathlib import Path

import duckdb
import pytest

from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_idempotencia import (
    RepositorioIdempotencia,
)
from central_preventiva.aplicacao.portas_persistencia import RespostaRegistrada

CHAVE = "3f2b9c4e-0000-4000-8000-000000000001"
OPERACAO = "restaurar_dados_sinteticos"
CORPO = '{"status": "restaurado", "restaurado_em": "2026-08-28T10:00:00"}'


def criar_repositorio(tmp_path: Path) -> RepositorioIdempotencia:
    """Cria o schema versionado em um arquivo temporário e devolve o repositório."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return RepositorioIdempotencia(caminho)


def test_buscar_retorna_none_para_par_desconhecido(tmp_path: Path) -> None:
    repositorio = criar_repositorio(tmp_path)

    assert repositorio.buscar(CHAVE, OPERACAO) is None


def test_registrar_preserva_hash_status_e_corpo(tmp_path: Path) -> None:
    repositorio = criar_repositorio(tmp_path)

    repositorio.registrar(CHAVE, OPERACAO, "hash-da-requisicao", 201, CORPO)

    assert repositorio.buscar(CHAVE, OPERACAO) == RespostaRegistrada(
        hash_requisicao="hash-da-requisicao",
        status=201,
        corpo=CORPO,
    )


def test_mesma_chave_em_operacoes_distintas_nao_colide(tmp_path: Path) -> None:
    repositorio = criar_repositorio(tmp_path)

    repositorio.registrar(CHAVE, OPERACAO, "hash-restauracao", 201, CORPO)
    repositorio.registrar(CHAVE, "outra_operacao", "hash-outra", 200, '{"status": "outro"}')

    registrada = repositorio.buscar(CHAVE, OPERACAO)
    outra = repositorio.buscar(CHAVE, "outra_operacao")
    assert registrada is not None and registrada.hash_requisicao == "hash-restauracao"
    assert outra is not None and outra.hash_requisicao == "hash-outra"
    assert registrada.status == 201
    assert outra.status == 200


def test_registro_repetido_do_mesmo_par_e_recusado_pela_chave_primaria(tmp_path: Path) -> None:
    repositorio = criar_repositorio(tmp_path)
    repositorio.registrar(CHAVE, OPERACAO, "hash-da-requisicao", 201, CORPO)

    with pytest.raises(duckdb.ConstraintException):
        repositorio.registrar(CHAVE, OPERACAO, "hash-diferente", 500, "{}")

    assert repositorio.buscar(CHAVE, OPERACAO) == RespostaRegistrada(
        hash_requisicao="hash-da-requisicao",
        status=201,
        corpo=CORPO,
    )
