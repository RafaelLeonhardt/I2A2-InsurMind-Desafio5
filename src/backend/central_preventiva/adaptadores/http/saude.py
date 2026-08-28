"""Rota HTTP de saúde do processo backend."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from central_preventiva.aplicacao.saude import consultar_saude

roteador = APIRouter(tags=["Saúde"])


class RespostaSaude(BaseModel):
    """Resposta pública da disponibilidade do processo backend."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["disponivel"]
    ambiente: Literal["educacional"]


@roteador.get(
    "/saude",
    response_model=RespostaSaude,
    summary="Consultar a saúde do processo",
    description="Confirma somente que o processo local da API está disponível.",
    responses={200: {"description": "Saúde do processo confirmada."}},
)
def obter_saude() -> RespostaSaude:
    """Expõe a saúde mínima, sem antecipar prontidão de dependências futuras."""

    saude = consultar_saude()
    return RespostaSaude(status=saude.status, ambiente=saude.ambiente)
