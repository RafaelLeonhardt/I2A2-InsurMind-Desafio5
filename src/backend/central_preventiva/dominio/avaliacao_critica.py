"""Vocabulário da avaliação crítica de conteúdo: categorias fechadas e decisão (CRIT-03).

As sete categorias são exatamente os sete critérios que o CRIT-03 lista. Um enum fechado
(em vez de texto livre) é o que torna os motivos consultáveis e filtráveis na interface, e é
também o que impede, por construção, que o crítico devolva um motivo sobre risco,
elegibilidade, cobertura ou limite de canal: não existe categoria para isso (CRIT-02).

Mesma separação já adotada em 3.2 entre `SaidaCanal` (domínio) e os schemas Pydantic por canal
(adaptador): aqui o domínio define o vocabulário, e `adaptadores/ia/agente_critico.py` define o
schema que o modelo preenche.
"""

from dataclasses import dataclass
from enum import StrEnum


class CategoriaCritica(StrEnum):
    """Os sete critérios avaliados pelo crítico, como categorias fechadas (CRIT-03)."""

    TOM = "tom"
    UTILIDADE = "utilidade"
    CLAREZA = "clareza"
    SEGURANCA = "seguranca"
    PROMESSA_INDEVIDA = "promessa_indevida"
    DISTINCAO_OFICIAL = "distincao_oficial"
    ADEQUACAO_CANAL = "adequacao_canal"


@dataclass(frozen=True, slots=True)
class MotivoCritica:
    """Um motivo específico da decisão: a categoria avaliada e a justificativa dela."""

    categoria: CategoriaCritica
    justificativa: str


@dataclass(frozen=True, slots=True)
class AvaliacaoCritica:
    """Decisão do crítico sobre uma versão de mensagem, com os motivos que a sustentam.

    Uma aprovação vem com `motivos` vazio; uma reprovação sempre carrega ao menos um motivo
    específico (CRIT-06). Uma saída que não satisfaz isso não vira `AvaliacaoCritica`: ela é
    falha da tentativa, nunca aprovação nem reprovação estruturada (CRIT-07).
    """

    aprovada: bool
    motivos: tuple[MotivoCritica, ...]
