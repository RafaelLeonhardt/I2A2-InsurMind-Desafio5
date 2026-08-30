"""Normaliza a resposta bruta do INMET (real ou cenário sintético) em `EventoMeteorologico`."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import uuid4

from central_preventiva.aplicacao.portas_meteorologia import AreaMonitorada, RespostaColetaInmet
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)

INTENSIDADE_MINIMA_PLAUSIVEL = 0.0
INTENSIDADE_MAXIMA_PLAUSIVEL = 500.0
"""Faixa fisicamente plausível de precipitação horária (mm), acima/abaixo da qual a leitura é
rejeitada mesmo com status HTTP 200 (edge case do `spec.md`)."""


class MotivoRejeicao(StrEnum):
    """Motivo tipado pelo qual uma resposta do INMET não vira `EventoMeteorologico`."""

    CAMPO_AUSENTE = "campo_ausente"
    MEDIDA_INVALIDA = "medida_invalida"
    GEOGRAFIA_NAO_RECONHECIDA = "geografia_nao_reconhecida"


@dataclass(frozen=True, slots=True)
class ResultadoNormalizacao:
    """Resultado da normalização: exatamente um dos dois campos é preenchido."""

    evento: EventoMeteorologico | None
    motivo_rejeicao: MotivoRejeicao | None

    @staticmethod
    def aceitar(evento: EventoMeteorologico) -> "ResultadoNormalizacao":
        """Constrói um resultado de sucesso a partir do evento normalizado."""

        return ResultadoNormalizacao(evento=evento, motivo_rejeicao=None)

    @staticmethod
    def rejeitar(motivo: MotivoRejeicao) -> "ResultadoNormalizacao":
        """Constrói um resultado de rejeição com o motivo tipado informado."""

        return ResultadoNormalizacao(evento=None, motivo_rejeicao=motivo)


class NormalizadorInmet:
    """Converte a resposta bruta do INMET (ou do cenário sintético de granizo) em domínio."""

    def normalizar(
        self, bruta: RespostaColetaInmet, area: AreaMonitorada | None
    ) -> ResultadoNormalizacao:
        """Normaliza a resposta bruta, sem nunca lançar exceção para entrada malformada."""

        if area is None:
            return ResultadoNormalizacao.rejeitar(MotivoRejeicao.GEOGRAFIA_NAO_RECONHECIDA)

        corpo = bruta.corpo
        if not isinstance(corpo, dict):
            return ResultadoNormalizacao.rejeitar(MotivoRejeicao.CAMPO_AUSENTE)

        if corpo.get("_sintetico") is True and corpo.get("TIPO_EVENTO_SINTETICO") == "granizo":
            return self._normalizar_cenario_sintetico_granizo(corpo, area)

        return self._normalizar_leitura_real(corpo, area)

    def _normalizar_leitura_real(
        self, corpo: dict[str, object], area: AreaMonitorada
    ) -> ResultadoNormalizacao:
        """Normaliza uma leitura horária real de estação automática (AD-013: só chuva_intensa)."""

        chuva_bruta = corpo.get("CHUVA")
        data_medicao = corpo.get("DT_MEDICAO")
        hora_medicao = corpo.get("HR_MEDICAO")
        if chuva_bruta is None or data_medicao is None or hora_medicao is None:
            return ResultadoNormalizacao.rejeitar(MotivoRejeicao.CAMPO_AUSENTE)

        try:
            intensidade = float(chuva_bruta)
        except (TypeError, ValueError):
            return ResultadoNormalizacao.rejeitar(MotivoRejeicao.MEDIDA_INVALIDA)

        if not (INTENSIDADE_MINIMA_PLAUSIVEL <= intensidade <= INTENSIDADE_MAXIMA_PLAUSIVEL):
            return ResultadoNormalizacao.rejeitar(MotivoRejeicao.MEDIDA_INVALIDA)

        try:
            instante_observado = datetime.strptime(
                f"{data_medicao} {hora_medicao}", "%Y-%m-%d %H%M"
            )
        except ValueError:
            return ResultadoNormalizacao.rejeitar(MotivoRejeicao.MEDIDA_INVALIDA)

        evento = EventoMeteorologico(
            id=uuid4(),
            tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
            area=area.codigo_ibge_area,
            periodo_inicio=instante_observado - timedelta(hours=1),
            periodo_fim=instante_observado,
            intensidade=intensidade,
            proveniencia=ProvenienciaEvento.REAL_INMET,
            instante_observado=instante_observado,
        )
        return ResultadoNormalizacao.aceitar(evento)

    def _normalizar_cenario_sintetico_granizo(
        self, corpo: dict[str, object], area: AreaMonitorada
    ) -> ResultadoNormalizacao:
        """Normaliza o payload do cenário sintético de contingência (AD-013)."""

        intensidade_bruta = corpo.get("INTENSIDADE")
        periodo_inicio_bruto = corpo.get("PERIODO_INICIO")
        periodo_fim_bruto = corpo.get("PERIODO_FIM")
        instante_bruto = corpo.get("INSTANTE_OBSERVADO")
        if None in (intensidade_bruta, periodo_inicio_bruto, periodo_fim_bruto, instante_bruto):
            return ResultadoNormalizacao.rejeitar(MotivoRejeicao.CAMPO_AUSENTE)

        try:
            intensidade = float(intensidade_bruta)  # type: ignore[arg-type]
            periodo_inicio = datetime.fromisoformat(str(periodo_inicio_bruto))
            periodo_fim = datetime.fromisoformat(str(periodo_fim_bruto))
            instante_observado = datetime.fromisoformat(str(instante_bruto))
        except (TypeError, ValueError):
            return ResultadoNormalizacao.rejeitar(MotivoRejeicao.MEDIDA_INVALIDA)

        if not (INTENSIDADE_MINIMA_PLAUSIVEL <= intensidade <= INTENSIDADE_MAXIMA_PLAUSIVEL):
            return ResultadoNormalizacao.rejeitar(MotivoRejeicao.MEDIDA_INVALIDA)

        evento = EventoMeteorologico(
            id=uuid4(),
            tipo=TipoEventoMeteorologico.GRANIZO,
            area=area.codigo_ibge_area,
            periodo_inicio=periodo_inicio,
            periodo_fim=periodo_fim,
            intensidade=intensidade,
            proveniencia=ProvenienciaEvento.SINTETICO,
            instante_observado=instante_observado,
        )
        return ResultadoNormalizacao.aceitar(evento)
