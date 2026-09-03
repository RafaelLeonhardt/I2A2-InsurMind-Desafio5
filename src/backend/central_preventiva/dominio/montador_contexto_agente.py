"""Montagem do contexto mínimo entregue ao agente redator (PREFL-11, PREFL-12, PREFL-15).

A garantia de minimização de dados é estrutural, não disciplinar: `ContextoAgente` declara
exatamente os cinco campos que o AC permite, é congelada e usa `slots`, então nem um campo
extra pode ser acrescentado em tempo de execução. Nada que não passe por estes cinco campos
alcança a OpenAI.

Função pura, sem I/O: recebe o snapshot de elegibilidade já avaliado (2.5) e o evento (2.1),
e devolve o contexto ou um erro tipado que identifica o item — nunca levanta exceção.

SPEC_DEVIATION: o design escreve `montar(elegibilidade, evento)`. A assinatura implementada
acrescenta `elegibilidade_id` como primeiro parâmetro, porque o T5 exige um erro tipado "que
identifica o item" e `ResultadoElegibilidade` (domínio, 2.5) não carrega identidade. O erro
sem o id obrigaria o caso de uso a recorrelacionar por posição.
"""

from dataclasses import dataclass
from uuid import UUID

from central_preventiva.dominio.avaliador_elegibilidade import (
    OPERANDO_AREA_AFETADA,
    OPERANDO_COBERTURA_EXIGIDA,
    ResultadoElegibilidade,
)
from central_preventiva.dominio.avaliador_risco import Criterio
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    TipoEventoMeteorologico,
)

CATEGORIA_EVENTO = "evento"
CATEGORIA_LOCALIZACAO = "localizacao_aproximada"
CATEGORIA_COBERTURAS = "coberturas_relevantes"
CATEGORIA_CANAL = "canal"
CATEGORIA_ORIENTACOES = "orientacoes_seguranca"

CATEGORIAS_UTILIZADAS: tuple[str, ...] = (
    CATEGORIA_EVENTO,
    CATEGORIA_LOCALIZACAO,
    CATEGORIA_COBERTURAS,
    CATEGORIA_CANAL,
    CATEGORIA_ORIENTACOES,
)
"""Categorias de dado que chegam ao agente redator — a proveniência positiva (PREFL-13)."""

CATEGORIAS_NAO_UTILIZADAS: tuple[str, ...] = (
    "documentos",
    "dados_financeiros",
    "dados_de_pagamento",
    "credenciais",
    "historico_de_sinistros",
    "identificacao_pessoal_direta",
)
"""Categorias deliberadamente deixadas de fora — a proveniência negativa (PREFL-12, PREFL-13).

São nomes de categoria, nunca conteúdo: registrar a proveniência não copia dado sensível
para a persistência nem para log.
"""

SENTINELA_SEM_COBERTURA = "nenhuma"
"""Valor que `avaliador_elegibilidade` grava no critério quando a apólice não tem cobertura."""

ORIENTACOES_POR_EVENTO: dict[TipoEventoMeteorologico, tuple[str, ...]] = {
    TipoEventoMeteorologico.CHUVA_INTENSA: (
        "Evite áreas alagadas e não atravesse ruas com água corrente.",
        "Desligue a energia elétrica se a água ameaçar entrar no imóvel.",
        "Mantenha documentos e itens essenciais em local elevado.",
    ),
    TipoEventoMeteorologico.GRANIZO: (
        "Recolha o veículo a um local coberto antes do início do granizo.",
        "Afaste-se de janelas, claraboias e telhas translúcidas.",
        "Não suba ao telhado durante nem logo após a queda de granizo.",
    ),
}
"""Orientações de segurança determinísticas por tipo de evento, escritas no repositório.

Não são geradas por modelo: são texto versionado, o que mantém a orientação de segurança
auditável e idêntica em toda execução do mesmo tipo de evento.
"""


@dataclass(frozen=True, slots=True)
class ContextoAgente:
    """Os únicos cinco campos que o agente redator pode receber (PREFL-11, PREFL-12).

    Congelada e com `slots`: acrescentar um sexto campo em tempo de execução levanta
    `AttributeError`, e alterar um campo levanta `FrozenInstanceError`. A violação da
    minimização de dados vira erro de tipo, não uma disciplina de revisão de código.
    """

    evento: str
    localizacao_aproximada: str
    coberturas_relevantes: tuple[str, ...]
    canal: str
    orientacoes_seguranca: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ErroContexto:
    """Campo obrigatório ausente ou inconsistente na montagem do contexto de um item.

    Identifica o item pelo `elegibilidade_id` para que só ele alcance um terminal de
    exceção, sem afetar os demais do mesmo público (PREFL-15).
    """

    elegibilidade_id: UUID
    campo: str
    motivo: str


def _valor_do_criterio(criterios: tuple[Criterio, ...], operando: str) -> str | None:
    """Lê o valor observado de um critério pelo nome estável, ou `None` se ele faltar."""

    for criterio in criterios:
        if criterio.operando == operando:
            return criterio.valor_observado
    return None


def _coberturas_de(valor_observado: str) -> tuple[str, ...]:
    """Separa a lista de coberturas gravada no snapshot, descartando a sentinela de vazio."""

    coberturas = [parte.strip() for parte in valor_observado.split(",")]
    return tuple(
        cobertura
        for cobertura in coberturas
        if cobertura and cobertura != SENTINELA_SEM_COBERTURA
    )


class MontadorContextoAgente:
    """Monta o contexto mínimo de um item elegível, validando os campos obrigatórios."""

    def montar(
        self,
        elegibilidade_id: UUID,
        elegibilidade: ResultadoElegibilidade,
        evento: EventoMeteorologico,
    ) -> ContextoAgente | ErroContexto:
        """Devolve o contexto mínimo do item, ou o erro tipado do primeiro campo inválido.

        Lê apenas do snapshot já avaliado: localização e coberturas vêm dos critérios
        persistidos pela avaliação de elegibilidade (2.5), buscados pelo nome estável do
        operando, nunca por posição e nunca por releitura ao vivo de `segurados`/`apolices`.
        Documento, dado financeiro, dado de pagamento e credencial não têm caminho até aqui.
        """

        localizacao = _valor_do_criterio(elegibilidade.criterios, OPERANDO_AREA_AFETADA)
        if localizacao is None or not localizacao.strip():
            return ErroContexto(
                elegibilidade_id,
                CATEGORIA_LOCALIZACAO,
                "A avaliação de elegibilidade não registrou a área afetada do item.",
            )

        valor_coberturas = _valor_do_criterio(
            elegibilidade.criterios, OPERANDO_COBERTURA_EXIGIDA
        )
        if valor_coberturas is None:
            return ErroContexto(
                elegibilidade_id,
                CATEGORIA_COBERTURAS,
                "A avaliação de elegibilidade não registrou as coberturas do item.",
            )
        coberturas = _coberturas_de(valor_coberturas)
        if not coberturas:
            return ErroContexto(
                elegibilidade_id,
                CATEGORIA_COBERTURAS,
                "O item não tem nenhuma cobertura relevante ao evento.",
            )

        if not elegibilidade.canal.strip():
            return ErroContexto(
                elegibilidade_id,
                CATEGORIA_CANAL,
                "O item não tem canal de comunicação registrado.",
            )

        orientacoes = ORIENTACOES_POR_EVENTO.get(evento.tipo)
        if orientacoes is None:
            return ErroContexto(
                elegibilidade_id,
                CATEGORIA_ORIENTACOES,
                f"Não há orientações de segurança versionadas para '{evento.tipo}'.",
            )

        return ContextoAgente(
            evento=str(evento.tipo),
            localizacao_aproximada=localizacao.strip(),
            coberturas_relevantes=coberturas,
            canal=elegibilidade.canal.strip(),
            orientacoes_seguranca=orientacoes,
        )
