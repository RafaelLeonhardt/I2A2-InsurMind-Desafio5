"""Testes do comando local de inicialização dos dados sintéticos."""

from pathlib import Path

import pytest

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.composicao import inicializador
from central_preventiva.composicao.configuracao import (
    Configuracao,
    ConfiguracaoInvalida,
    obter_configuracao,
)

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[3]
COMANDO_DOCUMENTADO = (
    "uv run --directory src/backend python -m central_preventiva.composicao.inicializador"
)
TABELAS_SEMEADAS = (
    "segurados",
    "apolices",
    "regras",
    "eventos_meteorologicos",
    "elegibilidades_historicas",
)


def configuracao_para(caminho: Path) -> Configuracao:
    """Monta a configuração local apontada ao banco temporário do teste."""

    return Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        caminho_banco=caminho,
    )


def contagens(caminho: Path) -> dict[str, int]:
    """Lê a contagem de linhas de cada tabela semeada."""

    with abrir_conexao(caminho) as conexao:
        contagem: dict[str, int] = {}
        for tabela in TABELAS_SEMEADAS:
            linha = conexao.execute(f"SELECT count(*) FROM {tabela}").fetchone()
            assert linha is not None
            contagem[tabela] = int(linha[0])
    return contagem


def versoes_registradas(caminho: Path) -> list[int]:
    """Lê as versões de migração registradas no banco."""

    with abrir_conexao(caminho) as conexao:
        return [
            int(versao)
            for (versao,) in conexao.execute(
                "SELECT versao FROM schema_migracoes ORDER BY versao"
            ).fetchall()
        ]


def test_inicializacao_em_banco_ausente_cria_schema_e_semeia(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    caminho = tmp_path / "central_preventiva.duckdb"
    monkeypatch.setattr(inicializador, "obter_configuracao", lambda: configuracao_para(caminho))
    assert not caminho.exists()

    inicializador.executar()

    assert versoes_registradas(caminho) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
    assert contagens(caminho) == {
        "segurados": 4,
        "apolices": 4,
        "regras": 2,
        "eventos_meteorologicos": 2,
        "elegibilidades_historicas": 4,
    }
    assert "Dados sintéticos inicializados" in capsys.readouterr().out


def test_reexecucao_relata_ja_preparado_sem_alterar_as_contagens(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    caminho = tmp_path / "central_preventiva.duckdb"
    monkeypatch.setattr(inicializador, "obter_configuracao", lambda: configuracao_para(caminho))
    inicializador.executar()
    capsys.readouterr()
    contagens_iniciais = contagens(caminho)

    inicializador.executar()

    assert capsys.readouterr().out.startswith("Dados já preparados")
    assert contagens(caminho) == contagens_iniciais
    assert versoes_registradas(caminho) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]


def test_configuracao_invalida_interrompe_sem_revelar_valores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    valor_sensivel = "host-invalido-nao-exibir"
    monkeypatch.setenv("CENTRAL_PREVENTIVA_HOST_API", valor_sensivel)
    monkeypatch.delenv("CENTRAL_PREVENTIVA_ORIGEM_FRONTEND", raising=False)
    obter_configuracao.cache_clear()

    try:
        with pytest.raises(ConfiguracaoInvalida) as captura:
            inicializador.executar()
    finally:
        obter_configuracao.cache_clear()

    assert valor_sensivel not in str(captura.value)
    assert "revise o arquivo .env conforme .env.example" in str(captura.value)


def test_readme_documenta_o_comando_reproduzivel_de_inicializacao() -> None:
    documento = (RAIZ_REPOSITORIO / "README.md").read_text(encoding="utf-8")

    assert "## Execução local" in documento
    assert COMANDO_DOCUMENTADO in documento
