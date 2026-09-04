"""Vocabulário da decisão humana sobre uma mensagem do lote (REVISAO-05, AD-6).

Os quatro resultados são fechados por construção: aprovar, rejeitar, excluir do lote ou
solicitar nova geração. Não existe "editar" — o AD-5/AD-6 proíbe qualquer edição manual do
texto gerado, e a ausência do valor no enum é o que torna a proibição estrutural, não apenas
uma regra de interface.

Três dos quatro exigem justificativa (REVISAO-06). A regra mora aqui, junto do vocabulário,
para que a validação da aplicação e a `CHECK` da migração `0013` descrevam a mesma coisa.
"""

from enum import StrEnum


class ResultadoDecisaoHumana(StrEnum):
    """As quatro decisões que Marina pode tomar sobre uma mensagem (REVISAO-05)."""

    APROVAR = "aprovar"
    REJEITAR = "rejeitar"
    EXCLUIR = "excluir"
    REGENERAR = "regenerar"


RESULTADOS_COM_JUSTIFICATIVA_OBRIGATORIA: frozenset[ResultadoDecisaoHumana] = frozenset(
    {
        ResultadoDecisaoHumana.REJEITAR,
        ResultadoDecisaoHumana.EXCLUIR,
        ResultadoDecisaoHumana.REGENERAR,
    }
)
"""Decisões que nunca são aceitas sem justificativa (REVISAO-06)."""


def exige_justificativa(resultado: ResultadoDecisaoHumana) -> bool:
    """Informa se a decisão só é válida acompanhada de justificativa."""

    return resultado in RESULTADOS_COM_JUSTIFICATIVA_OBRIGATORIA
