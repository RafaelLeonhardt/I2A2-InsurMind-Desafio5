"""Serialização JSON de `Criterio`, compartilhada entre repositórios que a persistem.

Mesmo formato usado por `avaliacoes_risco.criterios` (2.3) e `elegibilidades_historicas.criterios`
(2.5) — um único ponto de verdade evita que os dois formatos divirjam silenciosamente.
"""

import json

from central_preventiva.dominio.avaliador_risco import Criterio


def serializar_criterios(criterios: tuple[Criterio, ...]) -> str:
    """Serializa os critérios avaliados em JSON, na ordem em que foram produzidos."""

    return json.dumps(
        [
            {
                "operando": criterio.operando,
                "valor_observado": criterio.valor_observado,
                "atende": criterio.atende,
                "justificativa": criterio.justificativa,
            }
            for criterio in criterios
        ]
    )


def desserializar_criterios(bruto: str) -> tuple[Criterio, ...]:
    """Reconstrói os critérios avaliados a partir do JSON persistido."""

    return tuple(
        Criterio(
            operando=item["operando"],
            valor_observado=item["valor_observado"],
            atende=item["atende"],
            justificativa=item["justificativa"],
        )
        for item in json.loads(bruto)
    )
