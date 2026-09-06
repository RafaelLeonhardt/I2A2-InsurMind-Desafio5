"""Caso de uso de atualização de preferências do segurado (PREFS-02/03/06, 5.6).

Única mutação legítima do perfil Segurado no MVP: canal preferencial e participação em
alertas, sob concorrência otimista (`versao_esperada`) e idempotência (`Idempotency-Key`,
AD-002) — quarta aplicação do mesmo padrão já usado por `ServicoGestaoRegras.ativar` (2.4).

O efeito "só futuro" (PREFS-04/05) não exige nenhum mecanismo aqui: `segurados` é lido ao
vivo só pela preparação de comunicação futura, enquanto `elegibilidades_historicas.canal`
(2.5) já é um snapshot imutável — uma alteração de preferência nunca alcança histórico.
"""

import json
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from central_preventiva.aplicacao.portas_persistencia import (
    ConflitoIdempotencia,
    RespostaRegistrada,
)
from central_preventiva.dominio.validador_saida_canal import Canal

OPERACAO_ATUALIZAR_PREFERENCIAS = "atualizar_preferencias_segurado"
STATUS_ATUALIZACAO_CONCLUIDA = 200


@dataclass(frozen=True, slots=True)
class PreferenciasAtualizadas:
    """As preferências do segurado após a atualização (fresca ou repetida por
    idempotência)."""

    segurado_id: UUID
    canal_preferido: str
    participa_de_alertas: bool
    versao: int


class _PreferenciasSegurado(Protocol):
    """Forma mínima do resultado de `atualizar_preferencias` de que este caso de uso
    depende."""

    @property
    def canal_preferido(self) -> str: ...
    @property
    def participa_de_alertas(self) -> bool: ...
    @property
    def versao(self) -> int: ...


class _RepositorioSegurados(Protocol):
    """Porta mínima de escrita de preferências de que este caso de uso depende."""

    def atualizar_preferencias(
        self,
        segurado_id: UUID,
        versao_esperada: int,
        canal_preferido: Canal,
        participa_de_alertas: bool,
    ) -> _PreferenciasSegurado:
        """Atualiza canal e participação, sob concorrência otimista."""
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
class PortasPreferenciasSegurado:
    """Agrupa as portas de que o caso de uso de preferências do segurado depende."""

    segurados: _RepositorioSegurados
    idempotencia: _RepositorioIdempotencia


def _serializar_atualizacao(atualizadas: PreferenciasAtualizadas) -> str:
    """Serializa as preferências atualizadas para o corpo guardado na chave de
    idempotência."""

    return json.dumps(
        {
            "segurado_id": str(atualizadas.segurado_id),
            "canal_preferido": atualizadas.canal_preferido,
            "participa_de_alertas": atualizadas.participa_de_alertas,
            "versao": atualizadas.versao,
        }
    )


def _desserializar_atualizacao(corpo: str) -> PreferenciasAtualizadas:
    """Reconstrói as preferências atualizadas a partir do corpo previamente registrado."""

    bruto = json.loads(corpo)
    return PreferenciasAtualizadas(
        segurado_id=UUID(bruto["segurado_id"]),
        canal_preferido=bruto["canal_preferido"],
        participa_de_alertas=bruto["participa_de_alertas"],
        versao=bruto["versao"],
    )


class ServicoPreferenciasSegurado:
    """Atualiza canal preferencial e participação em alertas de forma idempotente."""

    def __init__(self, portas: PortasPreferenciasSegurado) -> None:
        """Guarda as portas de que este caso de uso depende."""

        self._portas = portas

    def atualizar(
        self,
        segurado_id: UUID,
        versao_esperada: int,
        canal_preferido: Canal,
        participa_de_alertas: bool,
        chave_idempotencia: str,
        hash_requisicao: str,
    ) -> PreferenciasAtualizadas:
        """Atualiza as preferências do segurado, de forma idempotente (AD-002).

        Repetir a mesma `Idempotency-Key` com o mesmo `hash_requisicao` devolve a
        atualização já aplicada, sem persistir de novo; hash diferente levanta
        `ConflitoIdempotencia`. `versao_esperada` desatualizada propaga `ConflitoVersao`
        do repositório, sem registrar nenhuma resposta de idempotência.
        """

        registrada = self._portas.idempotencia.buscar(
            chave_idempotencia, OPERACAO_ATUALIZAR_PREFERENCIAS
        )
        if registrada is not None:
            if registrada.hash_requisicao != hash_requisicao:
                raise ConflitoIdempotencia(
                    chave=chave_idempotencia, operacao=OPERACAO_ATUALIZAR_PREFERENCIAS
                )
            return _desserializar_atualizacao(registrada.corpo)

        preferencias = self._portas.segurados.atualizar_preferencias(
            segurado_id, versao_esperada, canal_preferido, participa_de_alertas
        )
        atualizadas = PreferenciasAtualizadas(
            segurado_id=segurado_id,
            canal_preferido=preferencias.canal_preferido,
            participa_de_alertas=preferencias.participa_de_alertas,
            versao=preferencias.versao,
        )
        self._portas.idempotencia.registrar(
            chave_idempotencia,
            OPERACAO_ATUALIZAR_PREFERENCIAS,
            hash_requisicao,
            STATUS_ATUALIZACAO_CONCLUIDA,
            _serializar_atualizacao(atualizadas),
        )
        return atualizadas
