"""Caso de uso de gestão de regras: validar, testar e ativar versões (REGRA-07..13)."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, cast
from uuid import UUID

from central_preventiva.aplicacao.portas_persistencia import (
    ConflitoIdempotencia,
    RespostaRegistrada,
)
from central_preventiva.dominio import avaliador_risco, validador_regra
from central_preventiva.dominio.avaliador_risco import RegraSnapshot, ResultadoAvaliacaoRisco
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    TipoEventoMeteorologico,
)
from central_preventiva.dominio.validador_regra import DadosRegra, ErroValidacaoRegra

OPERACAO_ATIVAR_REGRA = "ativar_regra"
STATUS_ATIVACAO_CONCLUIDA = 200


class ConfiguracaoInvalida(RuntimeError):
    """Indica que a configuração de regra não passou pelo `ValidadorRegra` (REGRA-08)."""

    def __init__(self, erros: tuple[ErroValidacaoRegra, ...]) -> None:
        """Registra os erros de campo e monta a mensagem agregada em português."""

        super().__init__(
            "A configuração de regra é inválida: " + "; ".join(erro.motivo for erro in erros)
        )
        self.erros = erros


class NenhumCenarioAplicavel(RuntimeError):
    """Indica que nenhum cenário sintético existe para o tipo de evento da regra.

    Bloqueia a ativação (edge case da spec: teste vazio é um resultado válido, mas a
    ativação continua bloqueada até a configuração ser revisada), sem impedir `testar`
    de devolver a lista vazia normalmente.
    """

    def __init__(self, evento_tipo: str) -> None:
        """Registra o tipo de evento sem cenário sintético aplicável."""

        super().__init__(
            f"Nenhum cenário sintético está disponível para o tipo de evento '{evento_tipo}'; "
            "revise a configuração antes de ativar."
        )
        self.evento_tipo = evento_tipo


@dataclass(frozen=True, slots=True)
class ResultadoTesteRegra:
    """Um caso de teste determinístico: o evento sintético usado e o resultado obtido."""

    evento_id: UUID
    resultado: ResultadoAvaliacaoRisco


@dataclass(frozen=True, slots=True)
class RegraAtivada:
    """A versão de regra recém-ativada (ou já registrada, se a chamada for idempotente)."""

    id: UUID
    versao: int
    estado: str
    dados: DadosRegra


class _Regra(Protocol):
    """Forma mínima do resultado de `criar_nova_versao` de que este caso de uso depende.

    Campos expostos como `@property` (somente leitura) para que a checagem estrutural do
    Protocol seja covariante — um atributo mutável exigiria o tipo exato em ambas as
    direções, e `Regra` (adaptador) declara `evento_tipo` como o enum concreto, não `object`.
    """

    @property
    def id(self) -> UUID: ...
    @property
    def versao(self) -> int: ...
    @property
    def estado(self) -> str: ...
    @property
    def evento_tipo(self) -> object: ...
    @property
    def limiar_meteorologico(self) -> float: ...
    @property
    def area_aplicavel(self) -> str: ...
    @property
    def apolice_tipo(self) -> str: ...
    @property
    def cobertura_exigida(self) -> str: ...
    @property
    def antecedencia_horas(self) -> int: ...
    @property
    def canal(self) -> str: ...


class _RepositorioRegras(Protocol):
    """Porta mínima de escrita de regras de que este caso de uso depende."""

    def criar_nova_versao(
        self, regra_anterior_id: UUID, versao_esperada: int, dados: DadosRegra
    ) -> _Regra:
        """Substitui a versão ativa por uma nova, sob concorrência otimista."""
        ...


class _RepositorioEventosMeteorologicos(Protocol):
    """Porta mínima de leitura de cenários sintéticos de que este caso de uso depende."""

    def listar_sinteticos_por_tipo(
        self, tipo: TipoEventoMeteorologico
    ) -> tuple[EventoMeteorologico, ...]:
        """Lista os eventos sintéticos do tipo informado."""
        ...


class _RepositorioIdempotencia(Protocol):
    """Porta mínima de idempotência (AD-002) de que este caso de uso depende."""

    def buscar(self, chave: str, operacao: str) -> RespostaRegistrada | None:
        """Retorna a resposta registrada para o par chave/operação, se existir."""
        ...

    def registrar(
        self, chave: str, operacao: str, hash_requisicao: str, status: int, corpo: str
    ) -> None:
        """Registra a resposta produzida para o par chave/operação."""
        ...


@dataclass(frozen=True, slots=True)
class PortasGestaoRegras:
    """Agrupa as portas de que o caso de uso de gestão de regras depende."""

    regras: _RepositorioRegras
    eventos: _RepositorioEventosMeteorologicos
    idempotencia: _RepositorioIdempotencia
    validar: Callable[[DadosRegra], validador_regra.ResultadoValidacaoRegra] = (
        validador_regra.validar
    )
    avaliar: Callable[[EventoMeteorologico, RegraSnapshot], ResultadoAvaliacaoRisco] = (
        avaliador_risco.avaliar
    )


def _snapshot_candidato(regra_id: UUID, dados: DadosRegra) -> RegraSnapshot:
    """Monta o `RegraSnapshot` candidato (ainda não ativo) para o motor de avaliação (2.3)."""

    return RegraSnapshot(
        id=regra_id,
        evento_tipo=TipoEventoMeteorologico(dados.evento_tipo),
        limiar_meteorologico=dados.limiar_meteorologico,
        area_aplicavel=dados.area_aplicavel,
        apolice_tipo=dados.apolice_tipo,
        versao=0,
    )


def _serializar_ativacao(ativada: RegraAtivada) -> str:
    """Serializa a regra ativada para o corpo guardado na chave de idempotência."""

    return json.dumps(
        {
            "id": str(ativada.id),
            "versao": ativada.versao,
            "estado": ativada.estado,
            "dados": {
                "evento_tipo": ativada.dados.evento_tipo,
                "limiar_meteorologico": ativada.dados.limiar_meteorologico,
                "area_aplicavel": ativada.dados.area_aplicavel,
                "apolice_tipo": ativada.dados.apolice_tipo,
                "cobertura_exigida": ativada.dados.cobertura_exigida,
                "antecedencia_horas": ativada.dados.antecedencia_horas,
                "canal": ativada.dados.canal,
            },
        }
    )


def _desserializar_ativacao(corpo: str) -> RegraAtivada:
    """Reconstrói a regra ativada a partir do corpo previamente registrado."""

    bruto = cast(dict[str, object], json.loads(corpo))
    dados_brutos = cast(dict[str, object], bruto["dados"])
    return RegraAtivada(
        id=UUID(cast(str, bruto["id"])),
        versao=cast(int, bruto["versao"]),
        estado=cast(str, bruto["estado"]),
        dados=DadosRegra(
            evento_tipo=cast(str, dados_brutos["evento_tipo"]),
            limiar_meteorologico=cast(float, dados_brutos["limiar_meteorologico"]),
            area_aplicavel=cast(str, dados_brutos["area_aplicavel"]),
            apolice_tipo=cast(str, dados_brutos["apolice_tipo"]),
            cobertura_exigida=cast(str, dados_brutos["cobertura_exigida"]),
            antecedencia_horas=cast(int, dados_brutos["antecedencia_horas"]),
            canal=cast(str, dados_brutos["canal"]),
        ),
    )


class ServicoGestaoRegras:
    """Orquestra validar → testar (via `AvaliadorRisco`, 2.3) → ativar (versão nova)."""

    def __init__(self, portas: PortasGestaoRegras) -> None:
        """Guarda as portas de que este caso de uso depende."""

        self._portas = portas

    def testar(self, regra_id: UUID, dados: DadosRegra) -> tuple[ResultadoTesteRegra, ...]:
        """Aplica deterministicamente `dados` aos cenários sintéticos do tipo do evento.

        Bloqueia com `ConfiguracaoInvalida` se `dados` não passar no `ValidadorRegra`
        (REGRA-08). Configuração válida sem nenhum cenário sintético aplicável devolve
        uma tupla vazia — resultado válido, não um erro técnico (edge case da spec).
        """

        resultado_validacao = self._portas.validar(dados)
        if not resultado_validacao.valida:
            raise ConfiguracaoInvalida(resultado_validacao.erros)

        candidata = _snapshot_candidato(regra_id, dados)
        eventos = self._portas.eventos.listar_sinteticos_por_tipo(candidata.evento_tipo)
        return tuple(
            ResultadoTesteRegra(
                evento_id=evento.id, resultado=self._portas.avaliar(evento, candidata)
            )
            for evento in eventos
        )

    def ativar(
        self,
        regra_anterior_id: UUID,
        versao_esperada: int,
        dados: DadosRegra,
        chave_idempotencia: str,
        hash_requisicao: str,
    ) -> RegraAtivada:
        """Ativa `dados` como nova versão de `regra_anterior_id`, de forma idempotente (AD-002).

        Sempre revalida e reexecuta o teste determinístico nesta chamada — não confia em
        um "já testado" enviado pelo cliente — bloqueando com `ConfiguracaoInvalida` ou
        `NenhumCenarioAplicavel` nas mesmas condições de `testar`. Repetir a mesma
        `Idempotency-Key` com o mesmo `hash_requisicao` devolve a versão já criada, sem
        criar outra; hash diferente levanta `ConflitoIdempotencia`.
        """

        registrada = self._portas.idempotencia.buscar(chave_idempotencia, OPERACAO_ATIVAR_REGRA)
        if registrada is not None:
            if registrada.hash_requisicao != hash_requisicao:
                raise ConflitoIdempotencia(
                    chave=chave_idempotencia, operacao=OPERACAO_ATIVAR_REGRA
                )
            return _desserializar_ativacao(registrada.corpo)

        resultado_validacao = self._portas.validar(dados)
        if not resultado_validacao.valida:
            raise ConfiguracaoInvalida(resultado_validacao.erros)

        candidata = _snapshot_candidato(regra_anterior_id, dados)
        eventos = self._portas.eventos.listar_sinteticos_por_tipo(candidata.evento_tipo)
        if not eventos:
            raise NenhumCenarioAplicavel(dados.evento_tipo)

        nova_regra = self._portas.regras.criar_nova_versao(
            regra_anterior_id, versao_esperada, dados
        )
        ativada = RegraAtivada(
            id=nova_regra.id, versao=nova_regra.versao, estado=nova_regra.estado, dados=dados
        )
        self._portas.idempotencia.registrar(
            chave_idempotencia,
            OPERACAO_ATIVAR_REGRA,
            hash_requisicao,
            STATUS_ATIVACAO_CONCLUIDA,
            _serializar_ativacao(ativada),
        )
        return ativada
