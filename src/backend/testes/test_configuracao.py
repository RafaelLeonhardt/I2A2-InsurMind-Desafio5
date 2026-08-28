"""Testes da configuração segura e restrita à interface local."""

import pytest
from pydantic import ValidationError

from central_preventiva.composicao import configuracao as modulo_configuracao
from central_preventiva.composicao.configuracao import (
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
