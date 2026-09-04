"""Estados canônicos de uma mensagem preventiva e sua classificação terminal.

Mesmo padrão de `estados_execucao.py` (AD-004), aplicado ao segundo diagrama do AD-4:
a execução e a mensagem têm enums distintos e estáveis, e cada mensagem carrega seu
próprio estado de geração, crítica, revisão e simulação.
"""

from enum import StrEnum


class EstadoMensagem(StrEnum):
    """Enumera os estados de uma mensagem definidos no segundo diagrama do ADR AD-4."""

    GERANDO = "gerando"
    CRITICANDO = "criticando"
    AGUARDANDO_REVISAO = "aguardando_revisao"
    APROVADA = "aprovada"
    REJEITADA = "rejeitada"
    EXCLUIDA = "excluida"
    SIMULADA_ENTREGUE = "simulada_entregue"
    FALHOU_CONTEUDO = "falhou_conteudo"
    FALHOU_INTEGRACAO_IA = "falhou_integracao_ia"


ESTADOS_TERMINAIS_MENSAGEM: frozenset[EstadoMensagem] = frozenset(
    {
        EstadoMensagem.REJEITADA,
        EstadoMensagem.EXCLUIDA,
        EstadoMensagem.SIMULADA_ENTREGUE,
        EstadoMensagem.FALHOU_CONTEUDO,
        EstadoMensagem.FALHOU_INTEGRACAO_IA,
    }
)
"""Estados a partir dos quais a mensagem não avança mais (arestas `--> [*]` do AD-4)."""


def eh_terminal_mensagem(estado: EstadoMensagem) -> bool:
    """Informa se o estado encerra o ciclo de vida da mensagem."""

    return estado in ESTADOS_TERMINAIS_MENSAGEM


ESTADOS_EM_CICLO_DE_CONTEUDO: frozenset[EstadoMensagem] = frozenset(
    {EstadoMensagem.GERANDO, EstadoMensagem.CRITICANDO}
)
"""Estados em que a mensagem ainda está produzindo conteúdo (geração ou crítica)."""


ESTADOS_TERMINAIS_DE_CONTEUDO: frozenset[EstadoMensagem] = frozenset(
    {
        EstadoMensagem.AGUARDANDO_REVISAO,
        EstadoMensagem.FALHOU_CONTEUDO,
        EstadoMensagem.FALHOU_INTEGRACAO_IA,
    }
)
"""Os três desfechos em que o ciclo de conteúdo de uma mensagem para (REVISAO-01).

`aguardando_revisao` é o desfecho bom; os outros dois são exceção. Depois deles a mensagem só
avança por decisão humana (3.5), nunca pela automação.
"""


def em_ciclo_de_conteudo(estado: EstadoMensagem) -> bool:
    """Informa se a mensagem ainda está gerando ou sendo criticada.

    É a negação útil de "alcançou um terminal de conteúdo" (REVISAO-01): os estados que vêm
    *depois* da decisão humana (`aprovada`, `rejeitada`, `excluida`, `simulada_entregue`)
    também já passaram pelo ciclo, então perguntar "ainda está no ciclo?" responde
    corretamente tanto na primeira formação do lote quanto no retorno depois de uma
    regeneração humana (REVISAO-10).
    """

    return estado in ESTADOS_EM_CICLO_DE_CONTEUDO
