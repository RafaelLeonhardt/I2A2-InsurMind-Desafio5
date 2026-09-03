"""Testes da montagem do contexto mínimo do agente redator (PREFL-11, PREFL-12, PREFL-15)."""

import dataclasses
from datetime import UTC, datetime
from uuid import UUID

import pytest

from central_preventiva.dominio import montador_contexto_agente as modulo
from central_preventiva.dominio.avaliador_elegibilidade import (
    OPERANDO_AREA_AFETADA,
    OPERANDO_COBERTURA_EXIGIDA,
    ResultadoElegibilidade,
)
from central_preventiva.dominio.avaliador_risco import Criterio
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)
from central_preventiva.dominio.montador_contexto_agente import (
    CATEGORIA_CANAL,
    CATEGORIA_COBERTURAS,
    CATEGORIA_LOCALIZACAO,
    CATEGORIA_ORIENTACOES,
    CATEGORIAS_NAO_UTILIZADAS,
    CATEGORIAS_UTILIZADAS,
    ORIENTACOES_POR_EVENTO,
    ContextoAgente,
    ErroContexto,
    MontadorContextoAgente,
)

ELEGIBILIDADE_ID = UUID("11111111-1111-1111-1111-111111111111")
OUTRA_ELEGIBILIDADE_ID = UUID("22222222-2222-2222-2222-222222222222")

EVENTO = EventoMeteorologico(
    id=UUID("33333333-3333-3333-3333-333333333333"),
    tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
    area="9990001",
    periodo_inicio=datetime(2026, 9, 3, 12, 0, tzinfo=UTC),
    periodo_fim=datetime(2026, 9, 3, 18, 0, tzinfo=UTC),
    intensidade=62.5,
    proveniencia=ProvenienciaEvento.REAL_INMET,
    instante_observado=datetime(2026, 9, 3, 18, 0, tzinfo=UTC),
)


def criterio(operando: str, valor: str) -> Criterio:
    """Monta um critério de snapshot com o operando e o valor observado informados."""

    return Criterio(
        operando=operando, valor_observado=valor, atende=True, justificativa="irrelevante"
    )


def elegibilidade(
    area: str = "9990001",
    coberturas: str = "alagamento, vendaval",
    canal: str = "sms",
    extras: tuple[Criterio, ...] = (),
) -> ResultadoElegibilidade:
    """Monta um `ResultadoElegibilidade` incluído, no formato que 2.5 persiste."""

    return ResultadoElegibilidade(
        elegivel=True,
        criterios=(
            criterio(OPERANDO_AREA_AFETADA, area),
            criterio(OPERANDO_COBERTURA_EXIGIDA, coberturas),
            *extras,
        ),
        canal=canal,
        motivo="incluido",
        justificativa="Segurado e apólice atendem integralmente aos critérios da regra ativa.",
    )


def montar(
    resultado: ResultadoElegibilidade,
    evento: EventoMeteorologico = EVENTO,
    elegibilidade_id: UUID = ELEGIBILIDADE_ID,
) -> ContextoAgente | ErroContexto:
    """Executa a montagem do contexto para o item informado."""

    return MontadorContextoAgente().montar(elegibilidade_id, resultado, evento)


def test_contexto_declara_exatamente_os_cinco_campos_permitidos() -> None:
    """PREFL-11: o tipo carrega os cinco campos do AC, nem um a mais."""

    assert {campo.name for campo in dataclasses.fields(ContextoAgente)} == {
        "evento",
        "localizacao_aproximada",
        "coberturas_relevantes",
        "canal",
        "orientacoes_seguranca",
    }


def test_contexto_recusa_campo_extra_e_alteracao_em_tempo_de_execucao() -> None:
    """PREFL-12: nenhum dado a mais pode ser anexado ao contexto depois de montado."""

    contexto = montar(elegibilidade())
    assert isinstance(contexto, ContextoAgente)

    assert not hasattr(contexto, "__dict__")
    with pytest.raises((AttributeError, TypeError)):
        contexto.documento_do_segurado = "000.000.000-00"  # type: ignore[attr-defined]
    assert not hasattr(contexto, "documento_do_segurado")
    with pytest.raises(dataclasses.FrozenInstanceError):
        contexto.canal = "email"  # type: ignore[misc]
    assert contexto.canal == "sms"


def test_contexto_montado_traz_os_cinco_valores_do_snapshot_e_do_evento() -> None:
    contexto = montar(elegibilidade(area="9990002", coberturas="alagamento, vendaval"))

    assert contexto == ContextoAgente(
        evento="chuva_intensa",
        localizacao_aproximada="9990002",
        coberturas_relevantes=("alagamento", "vendaval"),
        canal="sms",
        orientacoes_seguranca=ORIENTACOES_POR_EVENTO[TipoEventoMeteorologico.CHUVA_INTENSA],
    )


def test_nenhum_dado_fora_da_lista_permitida_atravessa_a_montagem() -> None:
    """PREFL-12: documento, dado financeiro, pagamento e credencial não têm caminho até o
    contexto, mesmo quando presentes no snapshot de entrada."""

    sensiveis = (
        criterio("documento do segurado", "000.000.000-00"),
        criterio("premio mensal", "R$ 249,90"),
        criterio("cartao de pagamento", "4111111111111111"),
        criterio("credencial de acesso", "sk-nao-deve-vazar"),
    )

    contexto = montar(elegibilidade(extras=sensiveis))

    assert isinstance(contexto, ContextoAgente)
    serializado = repr(contexto)
    for sensivel in sensiveis:
        assert sensivel.valor_observado not in serializado
        assert sensivel.operando not in serializado


def test_area_ausente_no_snapshot_produz_erro_tipado_do_proprio_item() -> None:
    resultado = ResultadoElegibilidade(
        elegivel=True,
        criterios=(criterio(OPERANDO_COBERTURA_EXIGIDA, "alagamento"),),
        canal="sms",
        motivo="incluido",
        justificativa="irrelevante",
    )

    erro = montar(resultado)

    assert isinstance(erro, ErroContexto)
    assert erro.elegibilidade_id == ELEGIBILIDADE_ID
    assert erro.campo == CATEGORIA_LOCALIZACAO


def test_area_em_branco_no_snapshot_produz_erro_tipado() -> None:
    erro = montar(elegibilidade(area="   "))

    assert isinstance(erro, ErroContexto)
    assert erro.campo == CATEGORIA_LOCALIZACAO


def test_segurado_sem_cobertura_relevante_ao_evento_produz_erro_tipado() -> None:
    """Edge case da spec: sem cobertura relevante o item é tratado como inconsistente."""

    erro = montar(elegibilidade(coberturas="nenhuma"))

    assert isinstance(erro, ErroContexto)
    assert erro.elegibilidade_id == ELEGIBILIDADE_ID
    assert erro.campo == CATEGORIA_COBERTURAS


def test_criterio_de_cobertura_ausente_no_snapshot_produz_erro_tipado() -> None:
    resultado = ResultadoElegibilidade(
        elegivel=True,
        criterios=(criterio(OPERANDO_AREA_AFETADA, "9990001"),),
        canal="sms",
        motivo="incluido",
        justificativa="irrelevante",
    )

    erro = montar(resultado)

    assert isinstance(erro, ErroContexto)
    assert erro.campo == CATEGORIA_COBERTURAS


def test_canal_em_branco_produz_erro_tipado() -> None:
    erro = montar(elegibilidade(canal="  "))

    assert isinstance(erro, ErroContexto)
    assert erro.campo == CATEGORIA_CANAL


def test_tipo_de_evento_sem_orientacoes_versionadas_produz_erro_tipado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nenhum caminho levanta exceção não tratada: um tipo sem orientação vira erro tipado."""

    monkeypatch.setattr(modulo, "ORIENTACOES_POR_EVENTO", {})

    erro = montar(elegibilidade())

    assert isinstance(erro, ErroContexto)
    assert erro.campo == CATEGORIA_ORIENTACOES


def test_todo_tipo_de_evento_conhecido_tem_orientacoes_de_seguranca_versionadas() -> None:
    assert set(ORIENTACOES_POR_EVENTO) == set(TipoEventoMeteorologico)
    for orientacoes in ORIENTACOES_POR_EVENTO.values():
        assert orientacoes


def test_falha_de_um_item_nao_impede_a_montagem_do_item_seguinte() -> None:
    """PREFL-15: só o item inconsistente alcança o terminal de exceção."""

    invalido = montar(elegibilidade(coberturas="nenhuma"), elegibilidade_id=ELEGIBILIDADE_ID)
    valido = montar(elegibilidade(), elegibilidade_id=OUTRA_ELEGIBILIDADE_ID)

    assert isinstance(invalido, ErroContexto)
    assert invalido.elegibilidade_id == ELEGIBILIDADE_ID
    assert isinstance(valido, ContextoAgente)
    assert valido.canal == "sms"


def test_categorias_de_proveniencia_cobrem_o_permitido_e_o_excluido() -> None:
    """PREFL-13: as duas listas de proveniência são nomes de categoria, sem conteúdo."""

    assert CATEGORIAS_UTILIZADAS == (
        "evento",
        "localizacao_aproximada",
        "coberturas_relevantes",
        "canal",
        "orientacoes_seguranca",
    )
    assert set(CATEGORIAS_UTILIZADAS) == {
        campo.name for campo in dataclasses.fields(ContextoAgente)
    }
    assert {
        "documentos",
        "dados_financeiros",
        "dados_de_pagamento",
        "credenciais",
    } <= set(CATEGORIAS_NAO_UTILIZADAS)
