"""Identificadores determinísticos e fictícios do namespace da demonstração."""

from uuid import NAMESPACE_URL, UUID, uuid5

NAMESPACE_DEMONSTRACAO = uuid5(NAMESPACE_URL, "https://central-preventiva.invalid/demonstracao")


def identificador_demonstracao(nome: str) -> UUID:
    """Deriva um identificador determinístico e fictício do namespace da demonstração."""

    return uuid5(NAMESPACE_DEMONSTRACAO, nome)


SEGURADO_PADRAO: UUID = identificador_demonstracao("segurado/chuva-elegivel")
"""Identificador do segurado sintético padrão exibido na visão de Segurado."""
