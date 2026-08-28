"""Testes do caso de uso de inicialização dos dados sintéticos."""

import ast
from pathlib import Path

import pytest

from central_preventiva.aplicacao.inicializacao import (
    PortasInicializacao,
    inicializar_dados_sinteticos,
    verificar_versao_schema,
)
from central_preventiva.aplicacao.portas_persistencia import (
    MigracaoFalhou,
    MigracoesPendentes,
    ResultadoMigracao,
    VersaoSchemaFutura,
)


class MigracoesFalsas:
    """Porta de migrações falsa que registra as chamadas recebidas."""

    def __init__(
        self,
        registrada: int | None,
        conhecida: int,
        aplicadas: tuple[int, ...] = (),
        erro: Exception | None = None,
    ) -> None:
        self._registrada = registrada
        self._conhecida = conhecida
        self._aplicadas = aplicadas
        self._erro = erro
        self.chamadas: list[str] = []

    def versao_registrada(self) -> int | None:
        self.chamadas.append("versao_registrada")
        return self._registrada

    def versao_conhecida(self) -> int:
        self.chamadas.append("versao_conhecida")
        return self._conhecida

    def aplicar_pendentes(self) -> ResultadoMigracao:
        self.chamadas.append("aplicar_pendentes")
        if self._erro is not None:
            raise self._erro
        return ResultadoMigracao(
            versoes_aplicadas=self._aplicadas,
            versao_final=max(self._aplicadas, default=self._registrada or 0),
        )


class DadosSinteticosFalsos:
    """Porta de dados sintéticos falsa que registra as chamadas recebidas."""

    def __init__(self, semeado: bool) -> None:
        self._semeado = semeado
        self.chamadas: list[str] = []

    def esta_semeado(self) -> bool:
        self.chamadas.append("esta_semeado")
        return self._semeado

    def semear(self) -> None:
        self.chamadas.append("semear")
        self._semeado = True

    def restaurar(self) -> None:
        self.chamadas.append("restaurar")


def montar(
    migracoes: MigracoesFalsas, dados: DadosSinteticosFalsos
) -> tuple[PortasInicializacao, list[str]]:
    """Agrupa as portas falsas e devolve um diário compartilhado de chamadas."""

    diario: list[str] = []
    migracoes.chamadas = diario
    dados.chamadas = diario
    return PortasInicializacao(migracoes=migracoes, dados=dados), diario


def test_banco_vazio_aplica_migracoes_e_depois_semeia() -> None:
    migracoes = MigracoesFalsas(registrada=None, conhecida=1, aplicadas=(1,))
    dados = DadosSinteticosFalsos(semeado=False)
    portas, diario = montar(migracoes, dados)

    resultado = inicializar_dados_sinteticos(portas)

    assert diario == ["aplicar_pendentes", "esta_semeado", "semear"]
    assert resultado.estado == "inicializado"
    assert resultado.versoes_aplicadas == (1,)
    assert resultado.semeado_agora is True


def test_reexecucao_sobre_banco_preparado_nao_escreve_e_relata_ja_preparado() -> None:
    migracoes = MigracoesFalsas(registrada=1, conhecida=1)
    dados = DadosSinteticosFalsos(semeado=True)
    portas, diario = montar(migracoes, dados)

    resultado = inicializar_dados_sinteticos(portas)

    assert diario == ["aplicar_pendentes", "esta_semeado"]
    assert "semear" not in diario
    assert resultado.estado == "ja_preparado"
    assert resultado.versoes_aplicadas == ()
    assert resultado.semeado_agora is False


def test_versao_futura_interrompe_a_inicializacao_sem_semear() -> None:
    migracoes = MigracoesFalsas(
        registrada=99,
        conhecida=1,
        erro=VersaoSchemaFutura(versao_registrada=99, versao_conhecida=1),
    )
    dados = DadosSinteticosFalsos(semeado=False)
    portas, diario = montar(migracoes, dados)

    with pytest.raises(VersaoSchemaFutura) as captura:
        inicializar_dados_sinteticos(portas)

    assert captura.value.versao_registrada == 99
    assert diario == ["aplicar_pendentes"]


def test_migracao_falha_interrompe_a_inicializacao_sem_semear() -> None:
    migracoes = MigracoesFalsas(
        registrada=1,
        conhecida=2,
        erro=MigracaoFalhou(versao=2, descricao="extra", causa="sql inválido"),
    )
    dados = DadosSinteticosFalsos(semeado=False)
    portas, diario = montar(migracoes, dados)

    with pytest.raises(MigracaoFalhou) as captura:
        inicializar_dados_sinteticos(portas)

    assert captura.value.versao == 2
    assert diario == ["aplicar_pendentes"]


def test_verificar_versao_schema_aceita_banco_na_versao_conhecida() -> None:
    migracoes = MigracoesFalsas(registrada=1, conhecida=1)
    dados = DadosSinteticosFalsos(semeado=True)
    portas, diario = montar(migracoes, dados)

    assert verificar_versao_schema(portas) is None
    assert "aplicar_pendentes" not in diario
    assert "semear" not in diario


def test_verificar_versao_schema_recusa_versao_registrada_futura() -> None:
    migracoes = MigracoesFalsas(registrada=7, conhecida=3)
    dados = DadosSinteticosFalsos(semeado=True)
    portas, diario = montar(migracoes, dados)

    with pytest.raises(VersaoSchemaFutura) as captura:
        verificar_versao_schema(portas)

    assert captura.value.versao_registrada == 7
    assert captura.value.versao_conhecida == 3
    assert "aplicar_pendentes" not in diario
    assert "semear" not in diario


@pytest.mark.parametrize("registrada", [None, 1])
def test_verificar_versao_schema_sinaliza_migracoes_pendentes(registrada: int | None) -> None:
    migracoes = MigracoesFalsas(registrada=registrada, conhecida=3)
    dados = DadosSinteticosFalsos(semeado=False)
    portas, diario = montar(migracoes, dados)

    with pytest.raises(MigracoesPendentes) as captura:
        verificar_versao_schema(portas)

    assert captura.value.versao_registrada == registrada
    assert captura.value.versao_conhecida == 3
    assert "aplicar_pendentes" not in diario
    assert "semear" not in diario


def test_caso_de_uso_nao_importa_adaptadores_nem_duckdb() -> None:
    modulo = Path("central_preventiva/aplicacao/inicializacao.py")
    proibidos = ("duckdb", "central_preventiva.adaptadores", "central_preventiva.composicao")

    arvore = ast.parse(modulo.read_text(encoding="utf-8"))
    importados: list[str] = []
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            importados.extend(nome.name for nome in no.names)
        if isinstance(no, ast.ImportFrom):
            importados.append(no.module or "")

    assert importados, "O módulo deve declarar ao menos uma importação."
    for importado in importados:
        assert not importado.startswith(proibidos), importado
