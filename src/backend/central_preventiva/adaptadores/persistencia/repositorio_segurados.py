"""Consulta e atualização versionada de um segurado sintético por id."""

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.dominio.segurado import Segurado
from central_preventiva.dominio.validador_saida_canal import Canal


@dataclass(frozen=True, slots=True)
class PreferenciasSegurado:
    """As preferências de comunicação de um segurado (5.3, 5.6): canal, participação em
    alertas e versão (concorrência otimista, migração `0016`) — separado de `Segurado`
    (id+nome) para não alargar o tipo mínimo já usado por `consultar_segurado_padrao` e
    pela barra de contexto."""

    canal_preferido: str
    participa_de_alertas: bool
    versao: int


@dataclass(frozen=True, slots=True)
class SeguradoDetalhado:
    """Um segurado sintético com os dados básicos que o admin audita (LISTASEG-01..03):
    nome, área e canal do próprio segurado, mais o número da apólice mais recente — nulo
    quando o segurado não tiver nenhuma apólice. Separado de `Segurado` (id+nome, usado por
    `listar_sinteticos`/SELETOR-01) para não alargar o tipo mínimo já consumido pelo seletor
    "Visualizar como"."""

    id: UUID
    nome: str
    codigo_ibge_area: str
    canal_preferido: str
    apolice_numero: str | None


class ConflitoVersao(RuntimeError):
    """Indica que `versao_esperada` não corresponde à versão persistida do segurado."""

    def __init__(self, segurado_id: UUID, versao_esperada: int) -> None:
        """Registra o segurado e a versão esperada que não bateu."""

        super().__init__(
            f"O segurado {segurado_id} não está na versão esperada {versao_esperada}."
        )
        self.segurado_id = segurado_id
        self.versao_esperada = versao_esperada


class RepositorioSegurados:
    """Consulta e atualiza preferências de um segurado sintético pelo seu identificador."""

    def __init__(self, caminho: Path) -> None:
        """Vincula o repositório ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    def buscar_por_id(self, id: UUID) -> Segurado | None:
        """Retorna o segurado com o id informado, ou `None` se não existir."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                "SELECT id, nome FROM segurados WHERE id = ?", [id]
            ).fetchone()
        if linha is None:
            return None
        return Segurado(id=UUID(str(linha[0])), nome=str(linha[1]))

    def listar_sinteticos(self) -> list[Segurado]:
        """Lista todos os segurados do conjunto sintético semeado, ordenados por nome
        (SELETOR-01) — lista vazia se o seed ainda não foi restaurado."""

        with abrir_conexao(self._caminho) as conexao:
            linhas = conexao.execute("SELECT id, nome FROM segurados ORDER BY nome").fetchall()
        return [Segurado(id=UUID(str(linha[0])), nome=str(linha[1])) for linha in linhas]

    def listar_sinteticos_detalhado(self) -> list[SeguradoDetalhado]:
        """Lista todos os segurados sintéticos com área, canal e o número da apólice mais
        recente, ordenados por nome (LISTASEG-01..03, admin).

        `LEFT JOIN` preserva na lista um segurado sem nenhuma apólice (`apolice_numero`
        fica nulo) — nunca `INNER JOIN`, que o faria desaparecer. `QUALIFY ROW_NUMBER()`
        mantém só a apólice mais recente por segurado quando houver mais de uma, mesmo
        padrão de `RepositorioMeteorologia.mapear_execucoes_por_evento` (6.1). Separado de
        `listar_sinteticos` (SELETOR-01, id+nome) para não alargar um método/dataclass já
        usado pelo seletor "Visualizar como" do perfil Segurado."""

        with abrir_conexao(self._caminho) as conexao:
            linhas = conexao.execute(
                "SELECT s.id, s.nome, s.codigo_ibge_area, s.canal_preferido, a.numero "
                "FROM segurados s "
                "LEFT JOIN apolices a ON a.segurado_id = s.id "
                "QUALIFY ROW_NUMBER() "
                "OVER (PARTITION BY s.id ORDER BY a.criado_em DESC) = 1 "
                "ORDER BY s.nome"
            ).fetchall()
        return [
            SeguradoDetalhado(
                id=UUID(str(linha[0])),
                nome=str(linha[1]),
                codigo_ibge_area=str(linha[2]),
                canal_preferido=str(linha[3]),
                apolice_numero=str(linha[4]) if linha[4] is not None else None,
            )
            for linha in linhas
        ]

    def buscar_preferencias_por_id(self, id: UUID) -> PreferenciasSegurado | None:
        """Retorna o canal preferencial, a participação em alertas e a versão do segurado,
        ou `None` se não existir (5.3, APOLICE-01: "canal preferencial e participação em
        alertas" fazem parte do registro do segurado, não da apólice)."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                "SELECT canal_preferido, participa_de_alertas, versao FROM segurados "
                "WHERE id = ?",
                [id],
            ).fetchone()
        if linha is None:
            return None
        return PreferenciasSegurado(
            canal_preferido=str(linha[0]),
            participa_de_alertas=bool(linha[1]),
            versao=int(linha[2]),
        )

    def atualizar_preferencias(
        self,
        segurado_id: UUID,
        versao_esperada: int,
        canal_preferido: Canal,
        participa_de_alertas: bool,
    ) -> PreferenciasSegurado:
        """Atualiza canal e participação sob concorrência otimista (5.6, PREFS-02/04).

        Levanta `ConflitoVersao` se `versao_esperada` não bater — a linha não é mutada
        nesse caso. Mesmo padrão de `RepositorioExecucaoPreventiva.transicionar` (2.2).
        """

        with abrir_conexao(self._caminho) as conexao:
            resultado = conexao.execute(
                "UPDATE segurados SET canal_preferido = ?, participa_de_alertas = ?, "
                "versao = versao + 1, atualizado_em = now() "
                "WHERE id = ? AND versao = ? RETURNING versao",
                [canal_preferido.value, participa_de_alertas, segurado_id, versao_esperada],
            ).fetchone()
        if resultado is None:
            raise ConflitoVersao(segurado_id, versao_esperada)
        return PreferenciasSegurado(
            canal_preferido=canal_preferido.value,
            participa_de_alertas=participa_de_alertas,
            versao=int(resultado[0]),
        )
