"""Conjunto sintético canônico da demonstração e suas operações de semeadura."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import duckdb

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.dominio.identificadores_demonstracao import identificador_demonstracao

MARCADOR_DEMONSTRACAO = "DEMO-"

TABELAS_EXCECAO_RESTAURACAO: frozenset[str] = frozenset(
    {"schema_migracoes", "areas_monitoradas_inmet"}
)
"""Lista de exceções da restauração ao estado inicial completo (AD-014).

`schema_migracoes` (registro de versão aplicada) e as tabelas de configuração versionada
(hoje só `areas_monitoradas_inmet`) nunca são apagadas pela restauração — toda outra
tabela do catálogo, incluindo qualquer tabela de execução futura, é apagada e (quando
fizer parte do conjunto sintético canônico) resemeada. Uma nova tabela de configuração
versionada precisa entrar aqui explicitamente; tabelas de execução não precisam.
"""


@dataclass(frozen=True, slots=True)
class TabelaSemeada:
    """Descreve as linhas canônicas de uma tabela de referência."""

    nome: str
    colunas: tuple[str, ...]
    linhas: tuple[tuple[object, ...], ...]


@dataclass(frozen=True, slots=True)
class ConjuntoSintetico:
    """Agrupa as tabelas de referência na ordem segura de inserção."""

    tabelas: tuple[TabelaSemeada, ...]


def dataset_sintetico_v1() -> ConjuntoSintetico:
    """Monta o conjunto sintético versionado da demonstração, sem qualquer dado real."""

    segurado_chuva_elegivel = identificador_demonstracao("segurado/chuva-elegivel")
    segurado_chuva_nao_elegivel = identificador_demonstracao("segurado/chuva-nao-elegivel")
    segurado_granizo_elegivel = identificador_demonstracao("segurado/granizo-elegivel")
    segurado_granizo_nao_elegivel = identificador_demonstracao("segurado/granizo-nao-elegivel")

    apolice_chuva_elegivel = identificador_demonstracao("apolice/chuva-elegivel")
    apolice_chuva_nao_elegivel = identificador_demonstracao("apolice/chuva-nao-elegivel")
    apolice_granizo_elegivel = identificador_demonstracao("apolice/granizo-elegivel")
    apolice_granizo_nao_elegivel = identificador_demonstracao("apolice/granizo-nao-elegivel")

    regra_chuva = identificador_demonstracao("regra/chuva-intensa")
    regra_granizo = identificador_demonstracao("regra/granizo")
    evento_chuva = identificador_demonstracao("evento/chuva-intensa")
    evento_granizo = identificador_demonstracao("evento/granizo")

    area_chuva = "9990001"
    area_granizo = "9990002"

    return ConjuntoSintetico(
        tabelas=(
            TabelaSemeada(
                nome="segurados",
                colunas=(
                    "id",
                    "nome",
                    "codigo_ibge_area",
                    "canal_preferido",
                    "participa_de_alertas",
                ),
                linhas=(
                    (
                        segurado_chuva_elegivel,
                        "Pessoa Segurada Sintética DEMO-001",
                        area_chuva,
                        "whatsapp",
                        True,
                    ),
                    (
                        segurado_chuva_nao_elegivel,
                        "Pessoa Segurada Sintética DEMO-002",
                        area_chuva,
                        "email",
                        True,
                    ),
                    (
                        segurado_granizo_elegivel,
                        "Pessoa Segurada Sintética DEMO-003",
                        area_granizo,
                        "sms",
                        True,
                    ),
                    (
                        segurado_granizo_nao_elegivel,
                        "Pessoa Segurada Sintética DEMO-004",
                        area_granizo,
                        "whatsapp",
                        False,
                    ),
                ),
            ),
            TabelaSemeada(
                nome="apolices",
                colunas=(
                    "id",
                    "segurado_id",
                    "numero",
                    "tipo",
                    "situacao",
                    "vigencia_inicio",
                    "vigencia_fim",
                    "coberturas",
                    "endereco_risco_sintetico",
                    "codigo_ibge_area",
                ),
                linhas=(
                    (
                        apolice_chuva_elegivel,
                        segurado_chuva_elegivel,
                        "DEMO-RES-0001",
                        "residencial",
                        "ativa",
                        date(2026, 1, 1),
                        date(2026, 12, 31),
                        ["alagamento", "vendaval"],
                        "Rua Sintética DEMO-001, Bairro Fictício",
                        area_chuva,
                    ),
                    (
                        apolice_chuva_nao_elegivel,
                        segurado_chuva_nao_elegivel,
                        "DEMO-RES-0002",
                        "residencial",
                        "cancelada",
                        date(2026, 1, 1),
                        date(2026, 12, 31),
                        ["alagamento"],
                        "Rua Sintética DEMO-002, Bairro Fictício",
                        area_chuva,
                    ),
                    (
                        apolice_granizo_elegivel,
                        segurado_granizo_elegivel,
                        "DEMO-AUT-0003",
                        "automovel",
                        "ativa",
                        date(2026, 1, 1),
                        date(2026, 12, 31),
                        ["granizo", "colisao"],
                        "Rua Sintética DEMO-003, Bairro Fictício",
                        area_granizo,
                    ),
                    (
                        apolice_granizo_nao_elegivel,
                        segurado_granizo_nao_elegivel,
                        "DEMO-AUT-0004",
                        "automovel",
                        "ativa",
                        date(2026, 1, 1),
                        date(2026, 12, 31),
                        ["colisao"],
                        "Rua Sintética DEMO-004, Bairro Fictício",
                        area_granizo,
                    ),
                ),
            ),
            TabelaSemeada(
                nome="regras",
                colunas=(
                    "id",
                    "evento_tipo",
                    "limiar_meteorologico",
                    "area_aplicavel",
                    "apolice_tipo",
                    "cobertura_exigida",
                    "antecedencia_horas",
                    "canal",
                    "versao",
                    "estado",
                ),
                linhas=(
                    (
                        regra_chuva,
                        "chuva_intensa",
                        50.0,
                        area_chuva,
                        "residencial",
                        "alagamento",
                        24,
                        "whatsapp",
                        1,
                        "ativa",
                    ),
                    (
                        regra_granizo,
                        "granizo",
                        20.0,
                        area_granizo,
                        "automovel",
                        "granizo",
                        12,
                        "sms",
                        1,
                        "ativa",
                    ),
                ),
            ),
            TabelaSemeada(
                nome="eventos_meteorologicos",
                colunas=(
                    "id",
                    "tipo",
                    "area",
                    "periodo_inicio",
                    "periodo_fim",
                    "intensidade",
                    "proveniencia",
                    "instante_observado",
                ),
                linhas=(
                    (
                        evento_chuva,
                        "chuva_intensa",
                        area_chuva,
                        datetime(2026, 3, 10, 6, 0, 0),
                        datetime(2026, 3, 10, 18, 0, 0),
                        72.5,
                        "sintetico",
                        datetime(2026, 3, 9, 18, 0, 0),
                    ),
                    (
                        evento_granizo,
                        "granizo",
                        area_granizo,
                        datetime(2026, 3, 12, 14, 0, 0),
                        datetime(2026, 3, 12, 20, 0, 0),
                        31.0,
                        "sintetico",
                        datetime(2026, 3, 12, 8, 0, 0),
                    ),
                ),
            ),
            TabelaSemeada(
                nome="elegibilidades_historicas",
                colunas=(
                    "id",
                    "evento_id",
                    "regra_id",
                    "segurado_id",
                    "apolice_id",
                    "elegivel",
                    "criterios",
                    "canal",
                    "nome_segurado",
                    "justificativa",
                ),
                linhas=(
                    (
                        identificador_demonstracao("elegibilidade/chuva-elegivel"),
                        evento_chuva,
                        regra_chuva,
                        segurado_chuva_elegivel,
                        apolice_chuva_elegivel,
                        True,
                        "[]",
                        "whatsapp",
                        "Pessoa Segurada Sintética DEMO-001",
                        "Apólice residencial ativa na área do evento, com cobertura de alagamento.",
                    ),
                    (
                        identificador_demonstracao("elegibilidade/chuva-nao-elegivel"),
                        evento_chuva,
                        regra_chuva,
                        segurado_chuva_nao_elegivel,
                        apolice_chuva_nao_elegivel,
                        False,
                        "[]",
                        "email",
                        "Pessoa Segurada Sintética DEMO-002",
                        "Apólice cancelada no momento do evento de chuva intensa.",
                    ),
                    (
                        identificador_demonstracao("elegibilidade/granizo-elegivel"),
                        evento_granizo,
                        regra_granizo,
                        segurado_granizo_elegivel,
                        apolice_granizo_elegivel,
                        True,
                        "[]",
                        "sms",
                        "Pessoa Segurada Sintética DEMO-003",
                        "Apólice de automóvel ativa na área do evento e com cobertura de granizo.",
                    ),
                    (
                        identificador_demonstracao("elegibilidade/granizo-nao-elegivel"),
                        evento_granizo,
                        regra_granizo,
                        segurado_granizo_nao_elegivel,
                        apolice_granizo_nao_elegivel,
                        False,
                        "[]",
                        "whatsapp",
                        "Pessoa Segurada Sintética DEMO-004",
                        "Apólice de automóvel sem a cobertura de granizo exigida pela regra.",
                    ),
                ),
            ),
        )
    )


class SemeadorDadosSinteticos:
    """Semeia e restaura o conjunto sintético de referência da demonstração."""

    def __init__(self, caminho: Path, conjunto: ConjuntoSintetico | None = None) -> None:
        """Vincula o semeador ao arquivo operacional e ao conjunto sintético canônico."""

        self._caminho = caminho
        self._conjunto = conjunto if conjunto is not None else dataset_sintetico_v1()

    def esta_semeado(self) -> bool:
        """Informa se todas as tabelas de referência já possuem o conjunto sintético."""

        with abrir_conexao(self._caminho) as conexao:
            existentes = {
                nome
                for (nome,) in conexao.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
                ).fetchall()
            }
            for tabela in self._conjunto.tabelas:
                if tabela.nome not in existentes:
                    return False
                linha = conexao.execute(f"SELECT count(*) FROM {tabela.nome}").fetchone()
                if linha is None or int(linha[0]) == 0:
                    return False
        return True

    def semear(self) -> None:
        """Insere o conjunto sintético de referência em uma única transação."""

        with abrir_conexao(self._caminho) as conexao:
            self._em_transacao(conexao, self._semear)

    def restaurar(self) -> None:
        """Repõe o conjunto sintético de referência em uma única transação."""

        with abrir_conexao(self._caminho) as conexao:
            self._em_transacao(conexao, self._restaurar)

    def _em_transacao(
        self,
        conexao: duckdb.DuckDBPyConnection,
        operacao: Callable[[duckdb.DuckDBPyConnection], None],
    ) -> None:
        """Executa a operação por inteiro, revertendo tudo se qualquer passo falhar."""

        conexao.execute("BEGIN TRANSACTION")
        try:
            operacao(conexao)
            conexao.execute("COMMIT")
        except duckdb.Error:
            conexao.execute("ROLLBACK")
            raise

    def _semear(self, conexao: duckdb.DuckDBPyConnection) -> None:
        """Insere todas as linhas canônicas, da tabela mais externa para a mais interna."""

        for tabela in self._conjunto.tabelas:
            self._inserir(conexao, tabela, tabela.linhas)

    def _restaurar(self, conexao: duckdb.DuckDBPyConnection) -> None:
        """Repõe o estado inicial completo (AD-014): wipe orientado pelo catálogo, reseed.

        Apaga toda tabela do catálogo do DuckDB fora de `TABELAS_EXCECAO_RESTAURACAO` —
        cobre automaticamente as tabelas semeadas e qualquer tabela de execução futura,
        sem lista manual — e então reinsere o conjunto sintético canônico.
        """

        tabelas_existentes = {
            nome
            for (nome,) in conexao.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()
        }
        for nome in tabelas_existentes - TABELAS_EXCECAO_RESTAURACAO:
            conexao.execute(f"DELETE FROM {nome}")
        for tabela in self._conjunto.tabelas:
            self._inserir(conexao, tabela, tabela.linhas)

    def _inserir(
        self,
        conexao: duckdb.DuckDBPyConnection,
        tabela: TabelaSemeada,
        linhas: tuple[tuple[object, ...], ...],
    ) -> None:
        """Insere as linhas indicadas na tabela de referência."""

        colunas = ", ".join(tabela.colunas)
        marcadores = ", ".join("?" for _ in tabela.colunas)
        comando = f"INSERT INTO {tabela.nome} ({colunas}) VALUES ({marcadores})"
        for linha in linhas:
            conexao.execute(comando, list(linha))
