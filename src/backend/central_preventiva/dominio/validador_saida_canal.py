"""Validação determinística da saída do agente redator por canal (GERAR-01..03, 07..09).

O modelo nunca decide se a mensagem é válida (AD-5): campo obrigatório e tamanho são
decididos aqui, fora do LLM, contra limites configurados. A unidade de contagem é o
caractere Unicode do texto final já formatado — `len` de uma `str` em Python conta pontos
de código, não bytes nem tokens, que é exatamente a unidade inequívoca que a spec exige.

Os limites entram por `LimitesCanal`, montado a partir da `Configuracao` na composição:
nenhum limite mágico embutido aqui. O motivo devolvido é um código estável com contagens,
nunca o texto recusado (AD-10).
"""

from dataclasses import dataclass
from enum import StrEnum

CAMPO_CORPO = "corpo"
CAMPO_ASSUNTO = "assunto"

MOTIVO_SAIDA_AUSENTE = "saida_ausente"
"""Motivo de uma geração que não devolveu nenhum conteúdo estruturado."""

PREFIXO_CAMPO_AUSENTE = "campo_obrigatorio_ausente"
PREFIXO_LIMITE_EXCEDIDO = "limite_excedido"


class Canal(StrEnum):
    """Canais de comunicação suportados pelo MVP, com os mesmos valores do schema."""

    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SMS = "sms"


@dataclass(frozen=True, slots=True)
class LimitesCanal:
    """Limite de caracteres Unicode de cada canal, vindo da configuração local."""

    whatsapp: int
    sms: int
    assunto_email: int
    corpo_email: int


@dataclass(frozen=True, slots=True)
class SaidaCanal:
    """Conteúdo estruturado devolvido pelo agente redator para um canal.

    `assunto` só existe no canal e-mail; WhatsApp e SMS têm apenas `corpo`.
    """

    corpo: str
    assunto: str | None = None


@dataclass(frozen=True, slots=True)
class ResultadoValidacaoSaida:
    """Veredito determinístico de uma saída: válida, ou o motivo estável da recusa."""

    valida: bool
    motivo: str | None


def _motivo_campo_ausente(campo: str) -> str:
    """Descreve um campo obrigatório ausente ou em branco, citando só o nome do campo."""

    return f"{PREFIXO_CAMPO_AUSENTE}:{campo}"


def _motivo_limite_excedido(campo: str, tamanho: int, limite: int) -> str:
    """Descreve um campo acima do limite citando contagens, nunca o texto recusado."""

    return f"{PREFIXO_LIMITE_EXCEDIDO}:{campo}:{tamanho}:{limite}"


class ValidadorSaidaCanal:
    """Aplica campos obrigatórios e limites de caracteres do canal à saída do redator."""

    def __init__(self, limites: LimitesCanal) -> None:
        """Guarda os limites configurados, únicos valores de tamanho que este validador usa."""

        self._limites = limites

    def limite_corpo(self, canal: Canal) -> int:
        """Limite de caracteres do corpo do canal, aplicável antes da geração (GERAR-02).

        É o mesmo número usado depois por `validar`: o agente redator o recebe para
        instruir o modelo, e a validação posterior o cobra do texto devolvido.
        """

        if canal is Canal.WHATSAPP:
            return self._limites.whatsapp
        if canal is Canal.SMS:
            return self._limites.sms
        return self._limites.corpo_email

    def limite_assunto(self, canal: Canal) -> int | None:
        """Limite do assunto no canal e-mail, ou `None` nos canais que não têm assunto."""

        return self._limites.assunto_email if canal is Canal.EMAIL else None

    def validar(self, canal: Canal, saida: SaidaCanal | None) -> ResultadoValidacaoSaida:
        """Decide se a saída pode seguir à crítica, ou o motivo estável que a impede.

        Saída ausente, campo obrigatório vazio e campo acima do limite configurado são as
        três formas de recusa (GERAR-09). Uma saída estruturalmente válida mas com corpo em
        branco é campo obrigatório ausente, nunca sucesso.
        """

        if saida is None:
            return ResultadoValidacaoSaida(valida=False, motivo=MOTIVO_SAIDA_AUSENTE)

        limite_assunto = self.limite_assunto(canal)
        if limite_assunto is not None:
            assunto = saida.assunto or ""
            if not assunto.strip():
                return ResultadoValidacaoSaida(
                    valida=False, motivo=_motivo_campo_ausente(CAMPO_ASSUNTO)
                )
            if len(assunto) > limite_assunto:
                return ResultadoValidacaoSaida(
                    valida=False,
                    motivo=_motivo_limite_excedido(CAMPO_ASSUNTO, len(assunto), limite_assunto),
                )

        if not saida.corpo.strip():
            return ResultadoValidacaoSaida(
                valida=False, motivo=_motivo_campo_ausente(CAMPO_CORPO)
            )

        limite_corpo = self.limite_corpo(canal)
        if len(saida.corpo) > limite_corpo:
            return ResultadoValidacaoSaida(
                valida=False,
                motivo=_motivo_limite_excedido(CAMPO_CORPO, len(saida.corpo), limite_corpo),
            )

        return ResultadoValidacaoSaida(valida=True, motivo=None)
