"""Estados canônicos da execução preventiva e sua classificação terminal."""

from enum import StrEnum


class EstadoExecucao(StrEnum):
    """Enumera os estados agregados da execução preventiva definidos no ADR AD-4."""

    COLETANDO = "coletando"
    FALHOU_COLETA = "falhou_coleta"
    SEM_RISCO = "sem_risco"
    AVALIANDO_ELEGIBILIDADE = "avaliando_elegibilidade"
    SEM_ELEGIVEIS = "sem_elegiveis"
    AGUARDANDO_GERACAO = "aguardando_geracao"
    FALHOU_PREPARACAO_IA = "falhou_preparacao_ia"
    PROCESSANDO_MENSAGENS = "processando_mensagens"
    AGUARDANDO_REVISAO = "aguardando_revisao"
    AGUARDANDO_CONFIRMACAO = "aguardando_confirmacao"
    SIMULANDO = "simulando"
    FALHOU_SIMULACAO = "falhou_simulacao"
    CONCLUIDA = "concluida"


ESTADOS_TERMINAIS: frozenset[EstadoExecucao] = frozenset(
    {
        EstadoExecucao.FALHOU_COLETA,
        EstadoExecucao.SEM_RISCO,
        EstadoExecucao.SEM_ELEGIVEIS,
        EstadoExecucao.FALHOU_PREPARACAO_IA,
        EstadoExecucao.FALHOU_SIMULACAO,
        EstadoExecucao.CONCLUIDA,
    }
)
"""Estados a partir dos quais a execução preventiva não avança mais."""


def eh_terminal(estado: EstadoExecucao) -> bool:
    """Informa se o estado encerra a execução preventiva."""

    return estado in ESTADOS_TERMINAIS
