"""Configuração local, estrita e sanitizada da API."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ_PROJETO = Path(__file__).resolve().parents[4]


class ConfiguracaoInvalida(RuntimeError):
    """Indica configuração ausente ou insegura sem revelar o valor recebido."""


class Configuracao(BaseSettings):
    """Define os únicos endereços permitidos para a execução local do MVP."""

    model_config = SettingsConfigDict(
        env_file=RAIZ_PROJETO / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    host_api: str = Field(validation_alias="CENTRAL_PREVENTIVA_HOST_API")
    origem_frontend: str = Field(validation_alias="CENTRAL_PREVENTIVA_ORIGEM_FRONTEND")

    @field_validator("host_api")
    @classmethod
    def validar_host_api(cls, valor: str) -> str:
        """Aceita somente o endereço IPv4 explícito da interface de loopback."""

        if valor != "127.0.0.1":
            raise ValueError("host fora da interface de loopback")
        return valor

    @field_validator("origem_frontend")
    @classmethod
    def validar_origem_frontend(cls, valor: str) -> str:
        """Aceita somente a origem canônica do frontend local."""

        if valor != "http://127.0.0.1:5173":
            raise ValueError("origem fora da interface de loopback")
        return valor


@lru_cache
def obter_configuracao() -> Configuracao:
    """Carrega e valida a configuração, substituindo detalhes por erro seguro."""

    try:
        return Configuracao()  # pyright: ignore[reportCallIssue]
    except (ValidationError, OSError, UnicodeError):
        raise ConfiguracaoInvalida(
            "Configuração local ausente ou inválida; revise o arquivo .env conforme .env.example."
        ) from None
