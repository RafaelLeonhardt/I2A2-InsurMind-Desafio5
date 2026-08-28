"""Ponto de entrada seguro do servidor HTTP local."""

import uvicorn

from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import obter_configuracao

PORTA_API = 8000


def executar() -> None:
    """Valida a configuração e inicia o Uvicorn somente no host permitido."""

    configuracao = obter_configuracao()
    aplicacao = criar_aplicacao(configuracao)
    uvicorn.run(aplicacao, host=configuracao.host_api, port=PORTA_API)


if __name__ == "__main__":
    executar()
