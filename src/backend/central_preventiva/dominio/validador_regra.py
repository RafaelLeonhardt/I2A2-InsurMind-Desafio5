"""Validação de configuração de regra preventiva antes de testar ou ativar (REGRA-05/06)."""

from dataclasses import dataclass

LIMIAR_ANTECEDENCIA_MINIMA_HORAS = 1
LIMIAR_ANTECEDENCIA_MAXIMA_HORAS = 168
"""Faixa aceita de antecedência: de 1 hora a 7 dias (168h), suficiente para o alerta preventivo."""

CANAIS_VALIDOS = ("whatsapp", "email", "sms")
"""Mesmo conjunto de `segurados.canal_preferido` (schema Épico 1) — um só canal por regra."""

PRODUTO_ESPERADO_POR_EVENTO_TIPO: dict[str, str] = {
    "chuva_intensa": "residencial",
    "granizo": "automovel",
}
"""Coerência evento↔produto (AD-013): chuva intensa é residencial, granizo é automóvel."""

TIPOS_EVENTO_VALIDOS = tuple(PRODUTO_ESPERADO_POR_EVENTO_TIPO.keys())
TIPOS_APOLICE_VALIDOS = ("residencial", "automovel")


@dataclass(frozen=True, slots=True)
class DadosRegra:
    """Configuração de regra proposta, ainda não validada nem persistida."""

    evento_tipo: str
    limiar_meteorologico: float
    area_aplicavel: str
    apolice_tipo: str
    cobertura_exigida: str
    antecedencia_horas: int
    canal: str


@dataclass(frozen=True, slots=True)
class ErroValidacaoRegra:
    """Um erro de validação localizado a um campo específico, em português brasileiro."""

    campo: str
    motivo: str


@dataclass(frozen=True, slots=True)
class ResultadoValidacaoRegra:
    """Resultado da validação: válida, ou lista de erros por campo."""

    valida: bool
    erros: tuple[ErroValidacaoRegra, ...]


def _validar_tipos(dados: DadosRegra) -> list[ErroValidacaoRegra]:
    """Classe 'tipo': valores fora do conjunto ou do tipo Python esperado por campo."""

    erros: list[ErroValidacaoRegra] = []
    if dados.evento_tipo not in TIPOS_EVENTO_VALIDOS:
        erros.append(
            ErroValidacaoRegra(
                "evento_tipo",
                f"Tipo de evento inválido: aceita apenas {', '.join(TIPOS_EVENTO_VALIDOS)}.",
            )
        )
    if dados.apolice_tipo not in TIPOS_APOLICE_VALIDOS:
        erros.append(
            ErroValidacaoRegra(
                "apolice_tipo",
                f"Tipo de apólice inválido: aceita apenas {', '.join(TIPOS_APOLICE_VALIDOS)}.",
            )
        )
    if isinstance(dados.limiar_meteorologico, bool) or not isinstance(
        dados.limiar_meteorologico,  # pyright: ignore[reportUnnecessaryIsInstance]
        int | float,
    ):
        erros.append(
            ErroValidacaoRegra("limiar_meteorologico", "Limiar meteorológico deve ser numérico.")
        )
    if isinstance(dados.antecedencia_horas, bool) or not isinstance(
        dados.antecedencia_horas,  # pyright: ignore[reportUnnecessaryIsInstance]
        int,
    ):
        erros.append(
            ErroValidacaoRegra("antecedencia_horas", "Antecedência deve ser um número inteiro.")
        )
    return erros


def _validar_faixas(dados: DadosRegra) -> list[ErroValidacaoRegra]:
    """Classe 'faixa': valores numericamente fora do limite aceito."""

    erros: list[ErroValidacaoRegra] = []
    limiar_numerico = isinstance(
        dados.limiar_meteorologico,  # pyright: ignore[reportUnnecessaryIsInstance]
        int | float,
    ) and not isinstance(dados.limiar_meteorologico, bool)
    if limiar_numerico and dados.limiar_meteorologico <= 0:
        erros.append(
            ErroValidacaoRegra(
                "limiar_meteorologico", "Limiar meteorológico deve ser maior que zero."
            )
        )
    antecedencia_inteira = isinstance(
        dados.antecedencia_horas,  # pyright: ignore[reportUnnecessaryIsInstance]
        int,
    ) and not isinstance(dados.antecedencia_horas, bool)
    faixa_permitida = range(
        LIMIAR_ANTECEDENCIA_MINIMA_HORAS, LIMIAR_ANTECEDENCIA_MAXIMA_HORAS + 1
    )
    if antecedencia_inteira and dados.antecedencia_horas not in faixa_permitida:
        erros.append(
            ErroValidacaoRegra(
                "antecedencia_horas",
                f"Antecedência deve estar entre {LIMIAR_ANTECEDENCIA_MINIMA_HORAS} e "
                f"{LIMIAR_ANTECEDENCIA_MAXIMA_HORAS} horas.",
            )
        )
    return erros


def _validar_combinacoes_obrigatorias(dados: DadosRegra) -> list[ErroValidacaoRegra]:
    """Classe 'combinação obrigatória': campos textuais que não podem ficar vazios."""

    erros: list[ErroValidacaoRegra] = []
    if not dados.area_aplicavel.strip():
        erros.append(ErroValidacaoRegra("area_aplicavel", "Área aplicável é obrigatória."))
    if not dados.cobertura_exigida.strip():
        erros.append(ErroValidacaoRegra("cobertura_exigida", "Cobertura exigida é obrigatória."))
    if dados.canal not in CANAIS_VALIDOS:
        erros.append(
            ErroValidacaoRegra(
                "canal", f"Canal inválido: aceita apenas {', '.join(CANAIS_VALIDOS)}."
            )
        )
    return erros


def _validar_coerencia_evento_produto(dados: DadosRegra) -> list[ErroValidacaoRegra]:
    """Classe 'coerência evento↔produto': o par (evento_tipo, apolice_tipo) exigido por AD-013."""

    produto_esperado = PRODUTO_ESPERADO_POR_EVENTO_TIPO.get(dados.evento_tipo)
    if produto_esperado is None or dados.apolice_tipo not in TIPOS_APOLICE_VALIDOS:
        return []
    if dados.apolice_tipo != produto_esperado:
        return [
            ErroValidacaoRegra(
                "apolice_tipo",
                f"Evento '{dados.evento_tipo}' exige apólice '{produto_esperado}', "
                f"não '{dados.apolice_tipo}'.",
            )
        ]
    return []


def validar(dados: DadosRegra) -> ResultadoValidacaoRegra:
    """Valida tipos, faixas, combinações obrigatórias e coerência evento↔produto (REGRA-05/06).

    Roda todas as quatro classes de checagem independentemente e agrega todos os erros
    encontrados — nunca para na primeira falha — para que o formulário exiba todos os
    problemas de uma vez, sem descartar os valores já informados.
    """

    erros = [
        *_validar_tipos(dados),
        *_validar_faixas(dados),
        *_validar_combinacoes_obrigatorias(dados),
        *_validar_coerencia_evento_produto(dados),
    ]
    return ResultadoValidacaoRegra(valida=not erros, erros=tuple(erros))
