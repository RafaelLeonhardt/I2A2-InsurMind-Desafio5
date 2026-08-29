"""Sonda de prontidão do próprio processo backend."""

from central_preventiva.aplicacao.portas_prontidao import ResultadoSonda
from central_preventiva.aplicacao.saude import consultar_saude
from central_preventiva.dominio.estados_prontidao import EstadoProntidao


class SondaBackend:
    """Verifica a prontidão do processo backend, sem qualquer I/O externo."""

    async def verificar(self) -> ResultadoSonda:
        """Confirma a disponibilidade do processo delegando a `consultar_saude`."""

        consultar_saude()
        return ResultadoSonda(estado=EstadoProntidao.DISPONIVEL, causa=None, latencia_ms=None)
