"""Configuração local, estrita e sanitizada da API."""

import re
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

RAIZ_PROJETO = Path(__file__).resolve().parents[4]
CAMINHO_BANCO_PADRAO = RAIZ_PROJETO / "var" / "central_preventiva.duckdb"
SUFIXO_BANCO = ".duckdb"

PADRAO_MODELO_OPENAI = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
"""Forma estrutural de um identificador de modelo: uma palavra, sem espaço nem vazio."""

PADRAO_VERSAO_PROMPT = re.compile(r"v\d+")
"""Forma estrutural da versão de prompt registrada em cada geração: `v1`, `v2`, ..."""

TEMPERATURA_MINIMA = 0.0
TEMPERATURA_MAXIMA = 2.0
"""Faixa de temperatura aceita pela API de chat da OpenAI."""


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
    caminho_banco: Path = Field(
        default=CAMINHO_BANCO_PADRAO,
        validation_alias="CENTRAL_PREVENTIVA_CAMINHO_BANCO",
    )
    chave_openai: SecretStr | None = Field(
        default=None,
        validation_alias="OPENAI_API_KEY",
    )
    url_base_inmet: str = Field(
        default="",
        validation_alias="CENTRAL_PREVENTIVA_URL_BASE_INMET",
    )
    modelo_openai: str = Field(
        default="gpt-4o-mini",
        validation_alias="CENTRAL_PREVENTIVA_MODELO_OPENAI",
    )
    temperatura_openai: float = Field(
        default=0.2,
        validation_alias="CENTRAL_PREVENTIVA_TEMPERATURA_OPENAI",
    )
    versao_prompt: str = Field(
        default="v1",
        validation_alias="CENTRAL_PREVENTIVA_VERSAO_PROMPT",
    )
    timeout_openai_segundos: float = Field(
        default=15.0,
        validation_alias="CENTRAL_PREVENTIVA_TIMEOUT_OPENAI_SEGUNDOS",
    )
    limite_caracteres_whatsapp: int = Field(
        default=1024,
        validation_alias="CENTRAL_PREVENTIVA_LIMITE_CARACTERES_WHATSAPP",
    )
    limite_caracteres_sms: int = Field(
        default=160,
        validation_alias="CENTRAL_PREVENTIVA_LIMITE_CARACTERES_SMS",
    )
    limite_caracteres_assunto_email: int = Field(
        default=78,
        validation_alias="CENTRAL_PREVENTIVA_LIMITE_CARACTERES_ASSUNTO_EMAIL",
    )
    limite_caracteres_corpo_email: int = Field(
        default=2000,
        validation_alias="CENTRAL_PREVENTIVA_LIMITE_CARACTERES_CORPO_EMAIL",
    )

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

    @field_validator("caminho_banco")
    @classmethod
    def validar_caminho_banco(cls, valor: Path) -> Path:
        """Exige um arquivo `.duckdb` nomeado e o resolve a partir da raiz do projeto."""

        if not valor.name.strip() or valor.suffix != SUFIXO_BANCO:
            raise ValueError("caminho do banco operacional inválido")
        return valor if valor.is_absolute() else RAIZ_PROJETO / valor

    @field_validator("modelo_openai")
    @classmethod
    def validar_modelo_openai(cls, valor: str) -> str:
        """Exige um identificador de modelo em uma só palavra, não vazio (PREFL-06).

        Um modelo malformado é configuração estrutural inválida e bloqueia a
        inicialização do backend; um modelo bem formado que não existe no catálogo da
        OpenAI é caso de preflight em tempo de execução, não falha de inicialização.
        """

        if not PADRAO_MODELO_OPENAI.fullmatch(valor):
            raise ValueError("identificador de modelo da OpenAI inválido")
        return valor

    @field_validator("temperatura_openai")
    @classmethod
    def validar_temperatura_openai(cls, valor: float) -> float:
        """Exige temperatura dentro da faixa aceita pela OpenAI (PREFL-05, PREFL-06)."""

        if not TEMPERATURA_MINIMA <= valor <= TEMPERATURA_MAXIMA:
            raise ValueError("temperatura fora da faixa suportada")
        return valor

    @field_validator("versao_prompt")
    @classmethod
    def validar_versao_prompt(cls, valor: str) -> str:
        """Exige a versão de prompt no formato `vN` (PREFL-05, PREFL-06)."""

        if not PADRAO_VERSAO_PROMPT.fullmatch(valor):
            raise ValueError("versão de prompt inválida")
        return valor

    @field_validator("timeout_openai_segundos")
    @classmethod
    def validar_timeout_openai(cls, valor: float) -> float:
        """Exige um limite operacional positivo para a chamada à OpenAI (AD-8)."""

        if valor <= 0:
            raise ValueError("limite de tempo da OpenAI inválido")
        return valor

    @field_validator(
        "limite_caracteres_whatsapp",
        "limite_caracteres_sms",
        "limite_caracteres_assunto_email",
        "limite_caracteres_corpo_email",
    )
    @classmethod
    def validar_limite_de_caracteres(cls, valor: int) -> int:
        """Exige um limite de canal positivo (GERAR-01).

        Um limite zero ou negativo tornaria toda mensagem daquele canal inválida por
        construção; é configuração estrutural inválida, não caso de execução.
        """

        if valor <= 0:
            raise ValueError("limite de caracteres do canal inválido")
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
