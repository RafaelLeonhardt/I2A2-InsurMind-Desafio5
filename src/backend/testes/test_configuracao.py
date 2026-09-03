"""Testes da configuração segura e restrita à interface local."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from central_preventiva.composicao import configuracao as modulo_configuracao
from central_preventiva.composicao.configuracao import (
    RAIZ_PROJETO,
    Configuracao,
    ConfiguracaoInvalida,
    obter_configuracao,
)


def test_aceita_configuracao_local() -> None:
    configuracao = Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
    )

    assert configuracao.host_api == "127.0.0.1"
    assert configuracao.origem_frontend == "http://127.0.0.1:5173"


def test_recusa_configuracao_estrutural_ausente() -> None:
    with pytest.raises(ValidationError):
        Configuracao(_env_file=None)


@pytest.mark.parametrize(
    ("host", "origem"),
    [
        ("0.0.0.0", "http://127.0.0.1:5173"),
        ("127.0.0.1", "http://localhost:5173"),
        ("127.0.0.1", "https://127.0.0.1:5173"),
        ("127.0.0.1", "http://127.0.0.1:5173/caminho"),
        ("127.0.0.1", "http://127.0.0.1"),
        ("127.0.0.1", "http://127.0.0.1:9999"),
        ("127.0.0.1", " http://127.0.0.1:5173"),
    ],
)
def test_recusa_configuracao_fora_do_loopback(host: str, origem: str) -> None:
    with pytest.raises(ValidationError):
        Configuracao(
            host_api=host,
            origem_frontend=origem,
        )


def test_caminho_do_banco_padrao_fica_no_diretorio_local_ignorado_pelo_git(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CENTRAL_PREVENTIVA_CAMINHO_BANCO", raising=False)

    configuracao = Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        _env_file=None,
    )

    assert configuracao.caminho_banco == RAIZ_PROJETO / "var" / "central_preventiva.duckdb"


def test_aceita_caminho_do_banco_relativo_resolvido_na_raiz_do_projeto() -> None:
    configuracao = Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        caminho_banco=Path("var/demonstracao.duckdb"),
    )

    assert configuracao.caminho_banco == RAIZ_PROJETO / "var" / "demonstracao.duckdb"


def test_preserva_caminho_do_banco_absoluto(tmp_path: Path) -> None:
    caminho = tmp_path / "central_preventiva.duckdb"

    configuracao = Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        caminho_banco=caminho,
    )

    assert configuracao.caminho_banco == caminho


@pytest.mark.parametrize(
    "caminho",
    ["", "   ", "var/", "var/central_preventiva.txt", "var/central_preventiva"],
)
def test_recusa_caminho_do_banco_invalido(caminho: str) -> None:
    with pytest.raises(ValidationError):
        Configuracao(
            host_api="127.0.0.1",
            origem_frontend="http://127.0.0.1:5173",
            caminho_banco=Path(caminho),
        )


def test_erro_de_configuracao_nao_revela_o_caminho_do_banco(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    caminho_sensivel = "/caminho/interno/nao-exibir"
    monkeypatch.setenv("CENTRAL_PREVENTIVA_HOST_API", "127.0.0.1")
    monkeypatch.setenv("CENTRAL_PREVENTIVA_ORIGEM_FRONTEND", "http://127.0.0.1:5173")
    monkeypatch.setenv("CENTRAL_PREVENTIVA_CAMINHO_BANCO", caminho_sensivel)
    obter_configuracao.cache_clear()

    with pytest.raises(ConfiguracaoInvalida) as captura:
        obter_configuracao()

    assert caminho_sensivel not in str(captura.value)
    obter_configuracao.cache_clear()


def test_erro_de_configuracao_nao_revela_valores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    valor_sensivel = "host-invalido-nao-exibir"
    monkeypatch.setenv("CENTRAL_PREVENTIVA_HOST_API", valor_sensivel)
    monkeypatch.delenv("CENTRAL_PREVENTIVA_ORIGEM_FRONTEND", raising=False)
    obter_configuracao.cache_clear()

    with pytest.raises(ConfiguracaoInvalida) as captura:
        obter_configuracao()

    assert valor_sensivel not in str(captura.value)
    obter_configuracao.cache_clear()


def test_aceita_chave_openai_ausente() -> None:
    configuracao = Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        _env_file=None,
    )

    assert configuracao.chave_openai is None


def test_chave_openai_nunca_aparece_no_repr_nem_no_str() -> None:
    chave_sintetica = "sk-teste-nao-deve-vazar-98765"

    configuracao = Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        chave_openai=chave_sintetica,
        _env_file=None,
    )

    assert chave_sintetica not in repr(configuracao)
    assert chave_sintetica not in str(configuracao)


def test_url_base_inmet_tem_padrao_vazio_quando_ausente() -> None:
    configuracao = Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        _env_file=None,
    )

    assert configuracao.url_base_inmet == ""


def test_url_base_inmet_aceita_valor_configurado() -> None:
    configuracao = Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        url_base_inmet="https://exemplo-inmet.invalido/api",
        _env_file=None,
    )

    assert configuracao.url_base_inmet == "https://exemplo-inmet.invalido/api"


@pytest.mark.parametrize("tipo_erro", [OSError, UnicodeError])
def test_erro_de_leitura_do_env_e_sanitizado(
    monkeypatch: pytest.MonkeyPatch,
    tipo_erro: type[Exception],
) -> None:
    detalhe_interno = "conteúdo interno que não pode aparecer"

    def falhar_leitura() -> Configuracao:
        raise tipo_erro(detalhe_interno)

    obter_configuracao.cache_clear()
    monkeypatch.setattr(modulo_configuracao, "Configuracao", falhar_leitura)

    with pytest.raises(ConfiguracaoInvalida) as captura:
        obter_configuracao()

    assert detalhe_interno not in str(captura.value)
    obter_configuracao.cache_clear()


def test_parametros_da_producao_agentica_tem_padroes_documentados_e_validos() -> None:
    """PREFL-05: modelo, temperatura, versão de prompt e limite operacional são
    configuráveis, com padrão válido quando o `.env` não os define."""

    configuracao = Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        _env_file=None,
    )

    assert configuracao.modelo_openai == "gpt-4o-mini"
    assert configuracao.temperatura_openai == 0.2
    assert configuracao.versao_prompt == "v1"
    assert configuracao.timeout_openai_segundos == 15.0


def test_parametros_da_producao_agentica_aceitam_valores_configurados() -> None:
    configuracao = Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        modelo_openai="gpt-4.1-mini",
        temperatura_openai=0.7,
        versao_prompt="v3",
        timeout_openai_segundos=30.0,
        _env_file=None,
    )

    assert configuracao.modelo_openai == "gpt-4.1-mini"
    assert configuracao.temperatura_openai == 0.7
    assert configuracao.versao_prompt == "v3"
    assert configuracao.timeout_openai_segundos == 30.0


@pytest.mark.parametrize(
    ("campo", "valor"),
    [
        ("modelo_openai", ""),
        ("modelo_openai", "   "),
        ("modelo_openai", "modelo com espaco"),
        ("modelo_openai", "-comeca-com-hifen"),
        ("temperatura_openai", -0.1),
        ("temperatura_openai", 2.1),
        ("versao_prompt", ""),
        ("versao_prompt", "1"),
        ("versao_prompt", "versao-1"),
        ("timeout_openai_segundos", 0.0),
        ("timeout_openai_segundos", -5.0),
    ],
)
def test_recusa_configuracao_estrutural_malformada_da_producao_agentica(
    campo: str, valor: object
) -> None:
    """PREFL-06: configuração estrutural malformada impede o backend de subir."""

    with pytest.raises(ValidationError):
        Configuracao(
            host_api="127.0.0.1",
            origem_frontend="http://127.0.0.1:5173",
            _env_file=None,
            **{campo: valor},
        )


def test_erro_de_configuracao_agentica_nao_revela_o_valor_recebido(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PREFL-06: o erro que bloqueia a inicialização é sanitizado."""

    valor_sensivel = "modelo interno que nao pode aparecer"
    monkeypatch.setenv("CENTRAL_PREVENTIVA_HOST_API", "127.0.0.1")
    monkeypatch.setenv("CENTRAL_PREVENTIVA_ORIGEM_FRONTEND", "http://127.0.0.1:5173")
    monkeypatch.setenv("CENTRAL_PREVENTIVA_MODELO_OPENAI", valor_sensivel)
    obter_configuracao.cache_clear()

    with pytest.raises(ConfiguracaoInvalida) as captura:
        obter_configuracao()

    assert valor_sensivel not in str(captura.value)
    obter_configuracao.cache_clear()


def test_documentacao_do_env_descreve_os_parametros_da_producao_agentica() -> None:
    """PREFL-05: os parâmetros novos são documentados junto dos demais no `.env.example`."""

    documento = (RAIZ_PROJETO / ".env.example").read_text(encoding="utf-8")

    for chave in (
        "CENTRAL_PREVENTIVA_MODELO_OPENAI",
        "CENTRAL_PREVENTIVA_TEMPERATURA_OPENAI",
        "CENTRAL_PREVENTIVA_VERSAO_PROMPT",
        "CENTRAL_PREVENTIVA_TIMEOUT_OPENAI_SEGUNDOS",
        "OPENAI_API_KEY",
    ):
        assert chave in documento
