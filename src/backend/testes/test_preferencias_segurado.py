"""Testes do `ServicoPreferenciasSegurado`: atualização idempotente de canal e
participação em alertas (PREFS-02/03/06, 5.6)."""

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest

from central_preventiva.adaptadores.persistencia.repositorio_segurados import ConflitoVersao
from central_preventiva.aplicacao.portas_persistencia import (
    ConflitoIdempotencia,
    RespostaRegistrada,
)
from central_preventiva.aplicacao.preferencias_segurado import (
    PortasPreferenciasSegurado,
    ServicoPreferenciasSegurado,
)
from central_preventiva.dominio.validador_saida_canal import Canal


@dataclass(frozen=True, slots=True)
class PreferenciasFalsas:
    canal_preferido: str
    participa_de_alertas: bool
    versao: int


class RepositorioSeguradosFalso:
    def __init__(self, versao_inicial: int = 1) -> None:
        self.chamadas: list[tuple[UUID, int, Canal, bool]] = []
        self._versao = versao_inicial

    def atualizar_preferencias(
        self,
        segurado_id: UUID,
        versao_esperada: int,
        canal_preferido: Canal,
        participa_de_alertas: bool,
    ) -> PreferenciasFalsas:
        self.chamadas.append((segurado_id, versao_esperada, canal_preferido, participa_de_alertas))
        if versao_esperada != self._versao:
            raise ConflitoVersao(segurado_id, versao_esperada)
        self._versao += 1
        return PreferenciasFalsas(
            canal_preferido=canal_preferido.value,
            participa_de_alertas=participa_de_alertas,
            versao=self._versao,
        )


class RepositorioIdempotenciaFalso:
    def __init__(self) -> None:
        self._respostas: dict[tuple[str, str], RespostaRegistrada] = {}

    def buscar(self, chave: str, operacao: str) -> RespostaRegistrada | None:
        return self._respostas.get((chave, operacao))

    def registrar(
        self, chave: str, operacao: str, hash_requisicao: str, status: int, corpo: str
    ) -> None:
        self._respostas[(chave, operacao)] = RespostaRegistrada(
            hash_requisicao=hash_requisicao, status=status, corpo=corpo
        )


def montar_servico(
    versao_inicial: int = 1,
) -> tuple[ServicoPreferenciasSegurado, RepositorioSeguradosFalso, RepositorioIdempotenciaFalso]:
    segurados = RepositorioSeguradosFalso(versao_inicial)
    idempotencia = RepositorioIdempotenciaFalso()
    portas = PortasPreferenciasSegurado(
        segurados=segurados,  # type: ignore[arg-type]
        idempotencia=idempotencia,  # type: ignore[arg-type]
    )
    return ServicoPreferenciasSegurado(portas), segurados, idempotencia


def test_atualizar_com_alteracao_valida_persiste_e_retorna_atualizada() -> None:
    servico, segurados, _ = montar_servico()
    segurado_id = uuid4()

    atualizadas = servico.atualizar(segurado_id, 1, Canal.SMS, False, "chave-1", "hash-1")

    assert atualizadas.segurado_id == segurado_id
    assert atualizadas.canal_preferido == "sms"
    assert atualizadas.participa_de_alertas is False
    assert atualizadas.versao == 2
    assert len(segurados.chamadas) == 1


def test_atualizar_repete_mesma_chave_conteudo_identico_nao_persiste_de_novo() -> None:
    servico, segurados, _ = montar_servico()
    segurado_id = uuid4()

    primeira = servico.atualizar(segurado_id, 1, Canal.SMS, False, "chave-1", "hash-1")
    segunda = servico.atualizar(segurado_id, 1, Canal.SMS, False, "chave-1", "hash-1")

    assert segunda == primeira
    assert len(segurados.chamadas) == 1


def test_atualizar_repete_mesma_chave_conteudo_diferente_levanta_conflito_idempotencia() -> None:
    servico, segurados, _ = montar_servico()
    segurado_id = uuid4()

    servico.atualizar(segurado_id, 1, Canal.SMS, False, "chave-1", "hash-1")

    with pytest.raises(ConflitoIdempotencia):
        servico.atualizar(segurado_id, 1, Canal.EMAIL, True, "chave-1", "hash-2")

    assert len(segurados.chamadas) == 1


def test_atualizar_versao_desatualizada_propaga_conflito_versao_sem_registrar_idempotencia() -> (
    None
):
    servico, segurados, idempotencia = montar_servico(versao_inicial=2)
    segurado_id = uuid4()

    with pytest.raises(ConflitoVersao):
        servico.atualizar(segurado_id, 1, Canal.SMS, False, "chave-1", "hash-1")

    assert len(segurados.chamadas) == 1
    assert idempotencia.buscar("chave-1", "atualizar_preferencias_segurado") is None


def test_atualizar_para_o_mesmo_valor_ja_vigente_e_alteracao_valida_normal() -> None:
    servico, segurados, _ = montar_servico()
    segurado_id = uuid4()

    atualizadas = servico.atualizar(segurado_id, 1, Canal.WHATSAPP, True, "chave-1", "hash-1")

    assert atualizadas.canal_preferido == "whatsapp"
    assert atualizadas.participa_de_alertas is True
    assert atualizadas.versao == 2
    assert len(segurados.chamadas) == 1
