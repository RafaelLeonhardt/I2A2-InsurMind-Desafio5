"""Caso de uso da apólice do segurado ativo e da explicação de critérios (APOLICE-01..06,
5.3).

`ServicoApoliceSegurado.obter` monta os dados cadastrais da apólice mais um "estado
objetivo" textual (`ativa`/`cancelada`/`suspensa`/`expirada`) derivado só de
`apolices.situacao` e da comparação de `vigencia_fim` com a data corrente — nunca uma
exceção técnica (design.md, Tech Decision).

`obter_explicacao` lê exclusivamente `elegibilidades_historicas.criterios` (2.5), o
snapshot imutável já persistido no momento da avaliação — nunca `RepositorioApolices`.
Isso garante por construção que uma comunicação histórica nunca reflete uma mudança
posterior da apólice (APOLICE-05, AD-11): não há nenhum caminho de código para o dado
atual vazar na explicação de uma execução passada. Os critérios são filtrados às
categorias relevantes à apólice (área, tipo/situação, cobertura) — "participação em
alertas" é um critério interno de elegibilidade, não uma característica da apólice em si,
e fica de fora (design.md, Approach).
"""

from dataclasses import dataclass
from datetime import date
from typing import Protocol
from uuid import UUID

from central_preventiva.adaptadores.persistencia.repositorio_apolices import Apolice
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RegistroElegibilidade,
)
from central_preventiva.adaptadores.persistencia.repositorio_segurados import (
    PreferenciasSegurado,
)
from central_preventiva.dominio.avaliador_elegibilidade import (
    OPERANDO_AREA_AFETADA,
    OPERANDO_COBERTURA_EXIGIDA,
)
from central_preventiva.dominio.avaliador_risco import Criterio

OPERANDO_TIPO_APOLICE = "tipo da apólice"
OPERANDO_SITUACAO_APOLICE = "situação da apólice"

_OPERANDOS_RELEVANTES_A_APOLICE = frozenset(
    {
        OPERANDO_AREA_AFETADA,
        OPERANDO_TIPO_APOLICE,
        OPERANDO_SITUACAO_APOLICE,
        OPERANDO_COBERTURA_EXIGIDA,
    }
)
"""Categorias de critério relevantes à apólice (design.md, Approach) — exclui
"participação em alertas", um critério interno de elegibilidade do segurado, não da
apólice."""

ESTADO_EXPIRADA = "expirada"
"""Estado objetivo de uma apólice `ativa` cuja `vigencia_fim` já passou — distinto de
`cancelada`/`suspensa` (Edge Case da spec: vigência expirada não é a mesma condição que
uma apólice cancelada ou suspensa pela seguradora)."""


@dataclass(frozen=True, slots=True)
class ApoliceSegurado:
    """Os dados da apólice exibíveis ao segurado ativo (APOLICE-01), com o estado
    objetivo textual — nunca uma falha técnica para uma condição normal (APOLICE-03)."""

    numero: str
    tipo: str
    situacao: str
    estado_objetivo: str
    vigencia_inicio: date
    vigencia_fim: date
    endereco_risco_sintetico: str
    coberturas: tuple[str, ...]
    canal_preferido: str
    participa_de_alertas: bool


@dataclass(frozen=True, slots=True)
class ExplicacaoApolice:
    """A explicação de como os critérios relevantes à apólice foram comparados numa
    execução específica (APOLICE-02) — sempre o snapshot da execução, nunca o dado
    atual (APOLICE-05)."""

    elegibilidade_id: UUID
    criterios: tuple[Criterio, ...]


def _estado_objetivo(apolice: Apolice, hoje: date) -> str:
    """Deriva o estado objetivo da apólice — texto de domínio, nunca uma exceção."""

    if apolice.situacao != "ativa":
        return apolice.situacao
    if apolice.vigencia_fim < hoje:
        return ESTADO_EXPIRADA
    return apolice.situacao


class _RepositorioApolices(Protocol):
    """Porta mínima de `apolices` (5.3)."""

    def buscar_por_segurado(self, segurado_id: UUID) -> Apolice | None: ...


class _RepositorioSegurados(Protocol):
    """Porta mínima de preferências do segurado (5.3, estendida em `repositorio_segurados.py`)."""

    def buscar_preferencias_por_id(self, id: UUID) -> PreferenciasSegurado | None: ...


class _RepositorioElegibilidades(Protocol):
    """Porta mínima de `elegibilidades_historicas` (2.5)."""

    def obter_por_id(self, id_registro: UUID) -> RegistroElegibilidade | None: ...


@dataclass(frozen=True, slots=True)
class PortasApoliceSegurado:
    """Agrupa as portas de que a apólice/explicação do segurado dependem."""

    apolices: _RepositorioApolices
    segurados: _RepositorioSegurados
    elegibilidades: _RepositorioElegibilidades


class ServicoApoliceSegurado:
    """Resolve a apólice do segurado ativo e a explicação de critérios, só leitura."""

    def __init__(self, portas: PortasApoliceSegurado) -> None:
        """Guarda as portas usadas pela apólice/explicação do segurado."""

        self._portas = portas

    def obter(self, segurado_id: UUID) -> ApoliceSegurado | None:
        """Monta a apólice do segurado, ou `None` se não houver nenhuma (APOLICE-04)."""

        apolice = self._portas.apolices.buscar_por_segurado(segurado_id)
        if apolice is None:
            return None
        preferencias = self._portas.segurados.buscar_preferencias_por_id(segurado_id)
        assert preferencias is not None, (
            f"segurado {segurado_id} tem apólice {apolice.id} mas não tem registro "
            "de preferências"
        )

        return ApoliceSegurado(
            numero=apolice.numero,
            tipo=apolice.tipo,
            situacao=apolice.situacao,
            estado_objetivo=_estado_objetivo(apolice, date.today()),
            vigencia_inicio=apolice.vigencia_inicio,
            vigencia_fim=apolice.vigencia_fim,
            endereco_risco_sintetico=apolice.endereco_risco_sintetico,
            coberturas=apolice.coberturas,
            canal_preferido=preferencias.canal_preferido,
            participa_de_alertas=preferencias.participa_de_alertas,
        )

    def obter_explicacao(
        self, segurado_id: UUID, elegibilidade_id: UUID
    ) -> ExplicacaoApolice | None:
        """Devolve a explicação de critérios de uma execução, ou `None` se a
        elegibilidade não existir ou não pertencer ao `segurado_id` informado
        (APOLICE-04) — resposta idêntica nos dois casos, mesmo padrão de
        não-enumeração de 4.2/4.3/5.2."""

        registro = self._portas.elegibilidades.obter_por_id(elegibilidade_id)
        if registro is None or registro.segurado_id != segurado_id:
            return None

        criterios_relevantes = tuple(
            criterio
            for criterio in registro.criterios
            if criterio.operando in _OPERANDOS_RELEVANTES_A_APOLICE
        )
        return ExplicacaoApolice(elegibilidade_id=registro.id, criterios=criterios_relevantes)
