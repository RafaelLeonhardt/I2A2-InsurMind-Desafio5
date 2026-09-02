"""Repositório de leitura e escrita versionada de `regras` (Épico 1 lê, 2.4 escreve)."""

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

import duckdb

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.dominio.avaliador_risco import RegraSnapshot
from central_preventiva.dominio.evento_meteorologico import TipoEventoMeteorologico
from central_preventiva.dominio.validador_regra import DadosRegra

_COLUNAS_REGRA = (
    "id, evento_tipo, limiar_meteorologico, area_aplicavel, apolice_tipo, "
    "cobertura_exigida, antecedencia_horas, canal, versao, estado"
)


class ConflitoVersao(RuntimeError):
    """Indica que `versao_esperada` não corresponde à versão ativa persistida da regra."""

    def __init__(self, regra_id: UUID, versao_esperada: int) -> None:
        """Registra a regra e a versão esperada que não bateu."""

        super().__init__(f"A regra {regra_id} não está na versão esperada {versao_esperada}.")
        self.regra_id = regra_id
        self.versao_esperada = versao_esperada


@dataclass(frozen=True, slots=True)
class Regra:
    """Uma versão completa de regra, para consulta/edição — além do `RegraSnapshot` de 2.3."""

    id: UUID
    evento_tipo: TipoEventoMeteorologico
    limiar_meteorologico: float
    area_aplicavel: str
    apolice_tipo: str
    cobertura_exigida: str
    antecedencia_horas: int
    canal: str
    versao: int
    estado: str


def _regra_de_linha(linha: tuple[object, ...]) -> Regra:
    """Traduz uma linha de `regras` (na ordem de `_COLUNAS_REGRA`) para `Regra`."""

    return Regra(
        id=UUID(str(linha[0])),
        evento_tipo=TipoEventoMeteorologico(str(linha[1])),
        limiar_meteorologico=float(linha[2]),  # type: ignore[arg-type]
        area_aplicavel=str(linha[3]),
        apolice_tipo=str(linha[4]),
        cobertura_exigida=str(linha[5]),
        antecedencia_horas=int(linha[6]),  # type: ignore[arg-type]
        canal=str(linha[7]),
        versao=int(linha[8]),  # type: ignore[arg-type]
        estado=str(linha[9]),
    )


class RepositorioRegras:
    """Consulta e versiona `regras` (schema do Épico 1) por substituição (AD-11, AD-008)."""

    def __init__(self, caminho: Path) -> None:
        """Vincula o repositório ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    def obter_ativa(self, evento_tipo: TipoEventoMeteorologico) -> RegraSnapshot | None:
        """Resolve a regra `ativa` para o tipo de evento informado, ou `None` se não houver."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                "SELECT id, evento_tipo, limiar_meteorologico, area_aplicavel, apolice_tipo, "
                "versao FROM regras WHERE evento_tipo = ? AND estado = 'ativa' "
                "ORDER BY versao DESC LIMIT 1",
                [evento_tipo.value],
            ).fetchone()
        if linha is None:
            return None
        return RegraSnapshot(
            id=UUID(str(linha[0])),
            evento_tipo=TipoEventoMeteorologico(str(linha[1])),
            limiar_meteorologico=float(linha[2]),
            area_aplicavel=str(linha[3]),
            apolice_tipo=str(linha[4]),
            versao=int(linha[5]),
        )

    def listar(self, evento_tipo: TipoEventoMeteorologico | None = None) -> list[Regra]:
        """Lista todas as versões de regra, mais recentes primeiro, opcionalmente por tipo."""

        consulta = f"SELECT {_COLUNAS_REGRA} FROM regras"
        parametros: list[str] = []
        if evento_tipo is not None:
            consulta += " WHERE evento_tipo = ?"
            parametros.append(evento_tipo.value)
        consulta += " ORDER BY evento_tipo, versao DESC"
        with abrir_conexao(self._caminho) as conexao:
            linhas = conexao.execute(consulta, parametros).fetchall()
        return [_regra_de_linha(linha) for linha in linhas]

    def obter_por_id(self, regra_id: UUID) -> Regra | None:
        """Resolve uma versão específica de regra pelo seu identificador, ou `None`."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                f"SELECT {_COLUNAS_REGRA} FROM regras WHERE id = ?", [regra_id]
            ).fetchone()
        if linha is None:
            return None
        return _regra_de_linha(linha)

    def criar_nova_versao(
        self, regra_anterior_id: UUID, versao_esperada: int, dados: DadosRegra
    ) -> Regra:
        """Substitui a versão ativa por uma nova, em uma única transação (AD-11, AD-008).

        Marca `regra_anterior_id` como `substituida` só se sua versão ativa corrente for
        exatamente `versao_esperada`; caso contrário levanta `ConflitoVersao` sem mutar
        nenhuma linha. A nova versão nasce `ativa`, com `versao = versao_esperada + 1`.
        """

        nova_id = uuid4()
        nova_versao = versao_esperada + 1
        with abrir_conexao(self._caminho) as conexao:
            conexao.execute("BEGIN TRANSACTION")
            try:
                substituida = conexao.execute(
                    "UPDATE regras SET estado = 'substituida' WHERE id = ? AND versao = ? "
                    "AND estado = 'ativa' RETURNING versao",
                    [regra_anterior_id, versao_esperada],
                ).fetchone()
                if substituida is None:
                    conexao.execute("ROLLBACK")
                    raise ConflitoVersao(regra_anterior_id, versao_esperada)

                conexao.execute(
                    "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, "
                    "area_aplicavel, apolice_tipo, cobertura_exigida, antecedencia_horas, "
                    "canal, versao, estado) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ativa')",
                    [
                        nova_id,
                        dados.evento_tipo,
                        dados.limiar_meteorologico,
                        dados.area_aplicavel,
                        dados.apolice_tipo,
                        dados.cobertura_exigida,
                        dados.antecedencia_horas,
                        dados.canal,
                        nova_versao,
                    ],
                )
                conexao.execute("COMMIT")
            except duckdb.Error:
                conexao.execute("ROLLBACK")
                raise
        return Regra(
            id=nova_id,
            evento_tipo=TipoEventoMeteorologico(dados.evento_tipo),
            limiar_meteorologico=dados.limiar_meteorologico,
            area_aplicavel=dados.area_aplicavel,
            apolice_tipo=dados.apolice_tipo,
            cobertura_exigida=dados.cobertura_exigida,
            antecedencia_horas=dados.antecedencia_horas,
            canal=dados.canal,
            versao=nova_versao,
            estado="ativa",
        )
