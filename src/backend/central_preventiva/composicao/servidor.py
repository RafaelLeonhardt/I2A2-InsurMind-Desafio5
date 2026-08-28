"""Ponto de entrada seguro do servidor HTTP local."""

import uvicorn

from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.semeador import SemeadorDadosSinteticos
from central_preventiva.aplicacao.inicializacao import (
    PortasInicializacao,
    verificar_versao_schema,
)
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao, obter_configuracao

PORTA_API = 8000


def conferir_schema(configuracao: Configuracao) -> None:
    """Recusa iniciar o servidor sobre um schema pendente ou mais novo que o código."""

    verificar_versao_schema(
        PortasInicializacao(
            migracoes=ExecutorMigracoes(configuracao.caminho_banco),
            dados=SemeadorDadosSinteticos(configuracao.caminho_banco),
        )
    )


def executar() -> None:
    """Valida a configuração e o schema, e inicia o Uvicorn somente no host permitido."""

    configuracao = obter_configuracao()
    conferir_schema(configuracao)
    aplicacao = criar_aplicacao(configuracao)
    uvicorn.run(aplicacao, host=configuracao.host_api, port=PORTA_API)


if __name__ == "__main__":
    executar()
