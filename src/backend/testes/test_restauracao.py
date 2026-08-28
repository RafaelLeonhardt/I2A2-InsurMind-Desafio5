"""Testes do caso de uso de restauração dos dados sintéticos."""

import json
from datetime import UTC, datetime

import pytest

from central_preventiva.aplicacao.portas_persistencia import (
    ConflitoIdempotencia,
    ExecucaoAtivaImpedeRestauracao,
    NaoInicializado,
    RespostaRegistrada,
)
from central_preventiva.aplicacao.restauracao import (
    OPERACAO_RESTAURACAO,
    STATUS_RESTAURACAO,
    PortasRestauracao,
    restaurar_dados_sinteticos,
)

CHAVE = "11111111-2222-3333-4444-555555555555"
HASH = "hash-da-requisicao"
INSTANTE_REGISTRADO = datetime(2026, 3, 10, 12, 30, 45, tzinfo=UTC)


class IdempotenciaFalsa:
    """Porta de idempotência falsa que registra as chamadas recebidas."""

    def __init__(self, registrada: RespostaRegistrada | None = None) -> None:
        self._registrada = registrada
        self.chamadas: list[str] = []
        self.registros: list[tuple[str, str, str, int, str]] = []

    def buscar(self, chave: str, operacao: str) -> RespostaRegistrada | None:
        self.chamadas.append("buscar")
        self.consultado = (chave, operacao)
        return self._registrada

    def registrar(
        self,
        chave: str,
        operacao: str,
        hash_requisicao: str,
        status: int,
        corpo: str,
    ) -> None:
        self.chamadas.append("registrar")
        self.registros.append((chave, operacao, hash_requisicao, status, corpo))


class ExecucoesFalsas:
    """Porta de execuções falsa que registra as chamadas recebidas."""

    def __init__(self, ativa: bool) -> None:
        self._ativa = ativa
        self.chamadas: list[str] = []

    def existe_execucao_nao_terminal(self) -> bool:
        self.chamadas.append("existe_execucao_nao_terminal")
        return self._ativa


class DadosSinteticosFalsos:
    """Porta de dados sintéticos falsa que registra as chamadas recebidas."""

    def __init__(self, semeado: bool = True) -> None:
        self._semeado = semeado
        self.chamadas: list[str] = []

    def esta_semeado(self) -> bool:
        self.chamadas.append("esta_semeado")
        return self._semeado

    def semear(self) -> None:
        self.chamadas.append("semear")

    def restaurar(self) -> None:
        self.chamadas.append("restaurar")


def montar(
    idempotencia: IdempotenciaFalsa,
    execucoes: ExecucoesFalsas,
    dados: DadosSinteticosFalsos,
) -> tuple[PortasRestauracao, list[str]]:
    """Agrupa as portas falsas e devolve um diário compartilhado de chamadas."""

    diario: list[str] = []
    idempotencia.chamadas = diario
    execucoes.chamadas = diario
    dados.chamadas = diario
    portas = PortasRestauracao(
        idempotencia=idempotencia,
        execucoes=execucoes,
        dados=dados,
    )
    return portas, diario


def resposta_registrada(hash_requisicao: str = HASH) -> RespostaRegistrada:
    """Monta a resposta previamente registrada para a chave de idempotência."""

    return RespostaRegistrada(
        hash_requisicao=hash_requisicao,
        status=STATUS_RESTAURACAO,
        corpo=json.dumps(
            {"status": "restaurado", "restaurado_em": INSTANTE_REGISTRADO.isoformat()}
        ),
    )


def test_restauracao_bem_sucedida_consulta_guarda_restaura_e_registra() -> None:
    idempotencia = IdempotenciaFalsa()
    execucoes = ExecucoesFalsas(ativa=False)
    dados = DadosSinteticosFalsos(semeado=True)
    portas, diario = montar(idempotencia, execucoes, dados)

    resultado = restaurar_dados_sinteticos(portas, CHAVE, HASH)

    assert diario == [
        "buscar",
        "esta_semeado",
        "existe_execucao_nao_terminal",
        "restaurar",
        "registrar",
    ]
    assert resultado.status == "restaurado"
    assert resultado.restaurado_em.tzinfo is not None
    assert idempotencia.registros == [
        (
            CHAVE,
            OPERACAO_RESTAURACAO,
            HASH,
            STATUS_RESTAURACAO,
            json.dumps(
                {"status": "restaurado", "restaurado_em": resultado.restaurado_em.isoformat()}
            ),
        )
    ]


def test_chave_repetida_com_mesmo_conteudo_devolve_a_resposta_registrada() -> None:
    idempotencia = IdempotenciaFalsa(resposta_registrada())
    execucoes = ExecucoesFalsas(ativa=False)
    dados = DadosSinteticosFalsos(semeado=True)
    portas, diario = montar(idempotencia, execucoes, dados)

    resultado = restaurar_dados_sinteticos(portas, CHAVE, HASH)

    assert diario == ["buscar"]
    assert "restaurar" not in diario
    assert "registrar" not in diario
    assert resultado.status == "restaurado"
    assert resultado.restaurado_em == INSTANTE_REGISTRADO
    assert idempotencia.consultado == (CHAVE, OPERACAO_RESTAURACAO)


def test_chave_repetida_com_conteudo_diferente_conflita_sem_mutacao() -> None:
    idempotencia = IdempotenciaFalsa(resposta_registrada(hash_requisicao="outro-hash"))
    execucoes = ExecucoesFalsas(ativa=False)
    dados = DadosSinteticosFalsos(semeado=True)
    portas, diario = montar(idempotencia, execucoes, dados)

    with pytest.raises(ConflitoIdempotencia) as captura:
        restaurar_dados_sinteticos(portas, CHAVE, HASH)

    assert captura.value.chave == CHAVE
    assert captura.value.operacao == OPERACAO_RESTAURACAO
    assert diario == ["buscar"]
    assert "restaurar" not in diario
    assert "registrar" not in diario


def test_execucao_ativa_impede_a_restauracao_sem_mutacao() -> None:
    idempotencia = IdempotenciaFalsa()
    execucoes = ExecucoesFalsas(ativa=True)
    dados = DadosSinteticosFalsos(semeado=True)
    portas, diario = montar(idempotencia, execucoes, dados)

    with pytest.raises(ExecucaoAtivaImpedeRestauracao) as captura:
        restaurar_dados_sinteticos(portas, CHAVE, HASH)

    assert "execução ativa impede a restauração" in str(captura.value)
    assert diario == ["buscar", "esta_semeado", "existe_execucao_nao_terminal"]
    assert "restaurar" not in diario
    assert "registrar" not in diario


def test_restauracao_antes_da_inicializacao_e_recusada_sem_consultar_a_guarda() -> None:
    idempotencia = IdempotenciaFalsa()
    execucoes = ExecucoesFalsas(ativa=False)
    dados = DadosSinteticosFalsos(semeado=False)
    portas, diario = montar(idempotencia, execucoes, dados)

    with pytest.raises(NaoInicializado) as captura:
        restaurar_dados_sinteticos(portas, CHAVE, HASH)

    assert "Execute o comando de inicialização" in str(captura.value)
    assert diario == ["buscar", "esta_semeado"]
    assert "existe_execucao_nao_terminal" not in diario
    assert "restaurar" not in diario
