"""Recurso REST/JSON de gestão versionada de regras preventivas (REGRA-11..13)."""

from hashlib import sha256
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from central_preventiva.adaptadores.persistencia.repositorio_idempotencia import (
    RepositorioIdempotencia,
)
from central_preventiva.adaptadores.persistencia.repositorio_meteorologia import (
    RepositorioEventosMeteorologicos,
)
from central_preventiva.adaptadores.persistencia.repositorio_regras import (
    ConflitoVersao,
    RepositorioRegras,
)
from central_preventiva.aplicacao.gestao_regras import (
    ConfiguracaoInvalida,
    NenhumCenarioAplicavel,
    PortasGestaoRegras,
    RegraAtivada,
    ResultadoTesteRegra,
    ServicoGestaoRegras,
)
from central_preventiva.aplicacao.portas_persistencia import ConflitoIdempotencia
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.validador_regra import DadosRegra

TIPO_PROBLEMA = "application/problem+json"
CAMINHO_REGRAS = "/regras"
CAMINHO_REGRA = "/regras/{regra_id}"
CAMINHO_TESTAR = "/regras/{regra_id}/testar"
CAMINHO_ATIVAR = "/regras/{regra_id}/ativar"


class SolicitacaoRegra(BaseModel):
    """Configuração de regra proposta, no formato aceito por `testar`/`ativar`."""

    model_config = ConfigDict(extra="forbid")

    evento_tipo: str = Field(description="Tipo de evento (`chuva_intensa` ou `granizo`).")
    limiar_meteorologico: float = Field(description="Limiar numérico usado pela regra.")
    area_aplicavel: str = Field(description="Código IBGE da área a que a regra se aplica.")
    apolice_tipo: str = Field(description="Tipo de apólice (`residencial` ou `automovel`).")
    cobertura_exigida: str = Field(description="Cobertura que a apólice precisa ter.")
    antecedencia_horas: int = Field(description="Antecedência do alerta preventivo, em horas.")
    canal: str = Field(description="Canal de comunicação (`whatsapp`, `email` ou `sms`).")


class SolicitacaoAtivarRegra(SolicitacaoRegra):
    """Configuração de regra proposta, mais a versão esperada para concorrência otimista."""

    versao_esperada: int = Field(
        description="Versão ativa esperada da regra anterior (concorrência otimista, AD-008)."
    )


class RespostaRegra(BaseModel):
    """Uma versão de regra, para consulta e auditoria."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(description="Identificador desta versão de regra.")
    evento_tipo: str = Field(description="Tipo de evento (`chuva_intensa` ou `granizo`).")
    limiar_meteorologico: float = Field(description="Limiar numérico usado pela regra.")
    area_aplicavel: str = Field(description="Código IBGE da área a que a regra se aplica.")
    apolice_tipo: str = Field(description="Tipo de apólice (`residencial` ou `automovel`).")
    cobertura_exigida: str = Field(description="Cobertura que a apólice precisa ter.")
    antecedencia_horas: int = Field(description="Antecedência do alerta preventivo, em horas.")
    canal: str = Field(description="Canal de comunicação (`whatsapp`, `email` ou `sms`).")
    versao: int = Field(description="Número sequencial desta versão da regra.")
    estado: str = Field(description="Estado da versão (`ativa` ou `substituida`).")


class RespostaRegras(BaseModel):
    """Lista pública de versões de regra."""

    model_config = ConfigDict(extra="forbid")

    regras: list[RespostaRegra] = Field(description="Versões de regra, mais recentes primeiro.")


class RespostaCriterioTeste(BaseModel):
    """Um critério avaliado no teste determinístico: operando, valor, resultado e justificativa."""

    model_config = ConfigDict(extra="forbid")

    operando: str = Field(description="O que foi comparado (ex.: área aplicável, intensidade).")
    valor_observado: str = Field(description="Valor observado no evento para este critério.")
    atende: bool = Field(description="Se o valor observado atende ao critério.")
    justificativa: str = Field(description="Explicação em português brasileiro do resultado.")


class RespostaCasoTeste(BaseModel):
    """Um caso de teste determinístico: o cenário sintético usado e o resultado obtido."""

    model_config = ConfigDict(extra="forbid")

    evento_id: UUID = Field(description="Identificador do evento sintético usado no teste.")
    relevante: bool = Field(description="Se o cenário foi considerado relevante pela regra.")
    criterios: list[RespostaCriterioTeste] = Field(description="Critérios avaliados neste caso.")
    motivo: str = Field(description="Motivo tipado do resultado deste caso.")


class RespostaTeste(BaseModel):
    """Resultado do teste determinístico, um caso por cenário sintético aplicável."""

    model_config = ConfigDict(extra="forbid")

    casos: list[RespostaCasoTeste] = Field(
        description="Casos de teste, um por cenário sintético do tipo de evento da regra."
    )


class ErroCampo(BaseModel):
    """Um erro de validação localizado a um campo específico."""

    model_config = ConfigDict(extra="forbid")

    campo: str = Field(description="Nome do campo com erro.")
    motivo: str = Field(description="Motivo do erro em português brasileiro.")


class ProblemaRegras(BaseModel):
    """Falha de uma operação de regras, com ocorrência, impacto e próxima ação segura."""

    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(description="Código estável que identifica o tipo da falha.")
    correlacao_id: str = Field(description="Identificador único desta ocorrência de falha.")
    ocorrencia: str = Field(description="O que aconteceu, em português brasileiro.")
    impacto: str = Field(description="Efeito prático da falha para quem consultou o recurso.")
    proxima_acao: str = Field(description="Próxima ação segura recomendada para contornar a falha.")
    erros: list[ErroCampo] = Field(
        default_factory=lambda: [],
        description="Erros por campo, quando a falha vem de uma configuração inválida.",
    )


def problema(
    status: int,
    codigo: str,
    ocorrencia: str,
    impacto: str,
    proxima_acao: str,
    erros: list[ErroCampo] | None = None,
) -> JSONResponse:
    """Monta a resposta `problem+json` correlacionada de uma falha de regras."""

    corpo = ProblemaRegras(
        codigo=codigo,
        correlacao_id=str(uuid4()),
        ocorrencia=ocorrencia,
        impacto=impacto,
        proxima_acao=proxima_acao,
        erros=erros or [],
    )
    return JSONResponse(
        status_code=status,
        media_type=TIPO_PROBLEMA,
        content=corpo.model_dump(),
    )


def _resposta_regra(regra: object) -> RespostaRegra:
    """Traduz uma `Regra` interna para o contrato REST/JSON público."""

    return RespostaRegra(
        id=regra.id,  # type: ignore[attr-defined]
        evento_tipo=str(regra.evento_tipo),  # type: ignore[attr-defined]
        limiar_meteorologico=regra.limiar_meteorologico,  # type: ignore[attr-defined]
        area_aplicavel=regra.area_aplicavel,  # type: ignore[attr-defined]
        apolice_tipo=regra.apolice_tipo,  # type: ignore[attr-defined]
        cobertura_exigida=regra.cobertura_exigida,  # type: ignore[attr-defined]
        antecedencia_horas=regra.antecedencia_horas,  # type: ignore[attr-defined]
        canal=regra.canal,  # type: ignore[attr-defined]
        versao=regra.versao,  # type: ignore[attr-defined]
        estado=regra.estado,  # type: ignore[attr-defined]
    )


def _resposta_ativada(ativada: RegraAtivada) -> RespostaRegra:
    """Traduz uma `RegraAtivada` (fresca ou repetida por idempotência) para o contrato público."""

    return RespostaRegra(
        id=ativada.id,
        evento_tipo=ativada.dados.evento_tipo,
        limiar_meteorologico=ativada.dados.limiar_meteorologico,
        area_aplicavel=ativada.dados.area_aplicavel,
        apolice_tipo=ativada.dados.apolice_tipo,
        cobertura_exigida=ativada.dados.cobertura_exigida,
        antecedencia_horas=ativada.dados.antecedencia_horas,
        canal=ativada.dados.canal,
        versao=ativada.versao,
        estado=ativada.estado,
    )


def _resposta_teste(casos: tuple[ResultadoTesteRegra, ...]) -> RespostaTeste:
    """Traduz os casos de teste determinístico para o contrato REST/JSON público."""

    return RespostaTeste(
        casos=[
            RespostaCasoTeste(
                evento_id=caso.evento_id,
                relevante=caso.resultado.relevante,
                motivo=caso.resultado.motivo,
                criterios=[
                    RespostaCriterioTeste(
                        operando=criterio.operando,
                        valor_observado=criterio.valor_observado,
                        atende=criterio.atende,
                        justificativa=criterio.justificativa,
                    )
                    for criterio in caso.resultado.criterios
                ],
            )
            for caso in casos
        ]
    )


def _dados_de(corpo: SolicitacaoRegra) -> DadosRegra:
    """Traduz o corpo público para o `DadosRegra` interno consumido pelo caso de uso."""

    return DadosRegra(
        evento_tipo=corpo.evento_tipo,
        limiar_meteorologico=corpo.limiar_meteorologico,
        area_aplicavel=corpo.area_aplicavel,
        apolice_tipo=corpo.apolice_tipo,
        cobertura_exigida=corpo.cobertura_exigida,
        antecedencia_horas=corpo.antecedencia_horas,
        canal=corpo.canal,
    )


def _erros_de(excecao: ConfiguracaoInvalida) -> list[ErroCampo]:
    """Traduz os erros de campo de `ConfiguracaoInvalida` para o contrato público."""

    return [ErroCampo(campo=erro.campo, motivo=erro.motivo) for erro in excecao.erros]


def montar_portas_gestao_regras(configuracao: Configuracao) -> PortasGestaoRegras:
    """Compõe as portas reais da gestão de regras, reusadas pelo roteador."""

    return PortasGestaoRegras(
        regras=RepositorioRegras(configuracao.caminho_banco),
        eventos=RepositorioEventosMeteorologicos(configuracao.caminho_banco),
        idempotencia=RepositorioIdempotencia(configuracao.caminho_banco),
    )


def criar_roteador(configuracao: Configuracao) -> APIRouter:
    """Compõe o recurso de gestão versionada de regras sobre o banco operacional configurado."""

    roteador = APIRouter(tags=["Regras"])
    regras_repo = RepositorioRegras(configuracao.caminho_banco)
    servico = ServicoGestaoRegras(montar_portas_gestao_regras(configuracao))

    @roteador.get(
        CAMINHO_REGRAS,
        response_model=RespostaRegras,
        status_code=200,
        summary="Consultar todas as versões de regra",
        description="Devolve todas as versões de regra registradas, ativas e substituídas.",
        responses={200: {"description": "Versões de regra."}},
    )
    async def consultar_regras() -> RespostaRegras:  # pyright: ignore[reportUnusedFunction]
        """Traduz `RepositorioRegras.listar` para o contrato REST/JSON público."""

        return RespostaRegras(regras=[_resposta_regra(regra) for regra in regras_repo.listar()])

    @roteador.get(
        CAMINHO_REGRA,
        response_model=RespostaRegra,
        status_code=200,
        summary="Consultar uma versão específica de regra",
        description="Devolve uma versão específica de regra pelo seu identificador.",
        responses={
            200: {"description": "Versão de regra encontrada."},
            404: {"description": "Regra não encontrada.", "model": ProblemaRegras},
            422: {
                "description": "O identificador da regra não é um UUID válido.",
                "model": ProblemaRegras,
            },
        },
    )
    async def consultar_regra(  # pyright: ignore[reportUnusedFunction]
        regra_id: str,
    ) -> RespostaRegra | JSONResponse:
        """Traduz `RepositorioRegras.obter_por_id` para o contrato REST/JSON público."""

        try:
            regra_uuid = UUID(regra_id)
        except ValueError:
            return problema(
                422,
                "regra_id_invalido",
                f"'{regra_id}' não é um identificador de regra válido.",
                "Nenhuma regra pode ser exibida.",
                "Consulte a regra pelo identificador UUID retornado pela API.",
            )

        regra = regras_repo.obter_por_id(regra_uuid)
        if regra is None:
            return problema(
                404,
                "regra_inexistente",
                f"A regra '{regra_id}' não existe.",
                "Nenhuma regra pode ser exibida.",
                "Consulte a lista de regras e repita com um identificador válido.",
            )
        return _resposta_regra(regra)

    @roteador.post(
        CAMINHO_TESTAR,
        response_model=RespostaTeste,
        status_code=200,
        summary="Testar deterministicamente uma configuração de regra",
        description=(
            "Aplica a configuração proposta a cada cenário sintético do tipo de evento, "
            "sem persistir nada. Configuração inválida é bloqueada com motivos por campo."
        ),
        responses={
            200: {"description": "Resultado do teste determinístico (pode ser vazio)."},
            422: {
                "description": "Identificador inválido ou configuração de regra inválida.",
                "model": ProblemaRegras,
            },
        },
    )
    async def testar_regra(  # pyright: ignore[reportUnusedFunction]
        regra_id: str, corpo: SolicitacaoRegra
    ) -> RespostaTeste | JSONResponse:
        """Traduz `ServicoGestaoRegras.testar` para o contrato REST/JSON público."""

        try:
            regra_uuid = UUID(regra_id)
        except ValueError:
            return problema(
                422,
                "regra_id_invalido",
                f"'{regra_id}' não é um identificador de regra válido.",
                "Nenhum teste foi executado.",
                "Consulte a regra pelo identificador UUID retornado pela API.",
            )

        try:
            casos = servico.testar(regra_uuid, _dados_de(corpo))
        except ConfiguracaoInvalida as excecao:
            return problema(
                422,
                "configuracao_invalida",
                "A configuração de regra proposta é inválida.",
                "Nenhum teste foi executado.",
                "Corrija os campos indicados e tente testar de novo.",
                erros=_erros_de(excecao),
            )

        return _resposta_teste(casos)

    @roteador.post(
        CAMINHO_ATIVAR,
        response_model=RespostaRegra,
        status_code=200,
        summary="Ativar uma nova versão de regra",
        description=(
            "Revalida e reexecuta o teste determinístico, e ativa a configuração como nova "
            "versão da regra informada, de forma idempotente. Exige o cabeçalho "
            "`Idempotency-Key` em toda requisição."
        ),
        responses={
            200: {"description": "Nova versão ativada, ou resposta idempotente repetida."},
            404: {"description": "Regra anterior não encontrada.", "model": ProblemaRegras},
            409: {
                "description": "Conflito de versão ou de idempotência.",
                "model": ProblemaRegras,
            },
            422: {
                "description": (
                    "Identificador inválido, configuração inválida, cabeçalho "
                    "`Idempotency-Key` ausente ou nenhum cenário sintético aplicável."
                ),
                "model": ProblemaRegras,
            },
        },
    )
    async def ativar_regra(  # pyright: ignore[reportUnusedFunction]
        regra_id: str,
        corpo: SolicitacaoAtivarRegra,
        requisicao: Request,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    ) -> RespostaRegra | JSONResponse:
        """Traduz `ServicoGestaoRegras.ativar` para o contrato REST/JSON público."""

        try:
            regra_uuid = UUID(regra_id)
        except ValueError:
            return problema(
                422,
                "regra_id_invalido",
                f"'{regra_id}' não é um identificador de regra válido.",
                "Nenhuma versão foi ativada.",
                "Consulte a regra pelo identificador UUID retornado pela API.",
            )

        if idempotency_key is None or not idempotency_key.strip():
            return problema(
                422,
                "idempotency_key_ausente",
                "A requisição de ativação não informou o cabeçalho Idempotency-Key.",
                "Nenhuma versão foi ativada.",
                "Repita a requisição incluindo um cabeçalho Idempotency-Key único.",
            )

        if regras_repo.obter_por_id(regra_uuid) is None:
            return problema(
                404,
                "regra_inexistente",
                f"A regra '{regra_id}' não existe.",
                "Nenhuma versão foi ativada.",
                "Consulte a lista de regras e repita com um identificador válido.",
            )

        hash_requisicao = sha256(await requisicao.body()).hexdigest()

        try:
            ativada = servico.ativar(
                regra_uuid,
                corpo.versao_esperada,
                _dados_de(corpo),
                idempotency_key,
                hash_requisicao,
            )
        except ConfiguracaoInvalida as excecao:
            return problema(
                422,
                "configuracao_invalida",
                "A configuração de regra proposta é inválida.",
                "Nenhuma versão foi ativada.",
                "Corrija os campos indicados e tente ativar de novo.",
                erros=_erros_de(excecao),
            )
        except NenhumCenarioAplicavel:
            return problema(
                422,
                "nenhum_cenario_aplicavel",
                f"Nenhum cenário sintético está disponível para '{corpo.evento_tipo}'.",
                "Nenhuma versão foi ativada.",
                "Revise a configuração antes de tentar ativar de novo.",
            )
        except ConflitoVersao:
            return problema(
                409,
                "conflito_versao",
                "A versão esperada não corresponde à versão ativa corrente da regra.",
                "Nenhuma versão foi ativada.",
                "Recarregue a regra atual e tente ativar de novo com a versão correta.",
            )
        except ConflitoIdempotencia:
            return problema(
                409,
                "conflito_idempotencia",
                "A chave de idempotência já foi usada com outro conteúdo de requisição.",
                "Nenhuma nova versão foi ativada.",
                "Gere uma nova Idempotency-Key para ativar outra configuração.",
            )

        return _resposta_ativada(ativada)

    return roteador
