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
