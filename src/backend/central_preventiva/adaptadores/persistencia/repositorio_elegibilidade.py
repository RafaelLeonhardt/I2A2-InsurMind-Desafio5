"""Repositórios de candidatos e resultados de elegibilidade preventiva (ELEG-04..07)."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.serializacao_criterios import (
    desserializar_criterios,
    serializar_criterios,
)
from central_preventiva.dominio.avaliador_elegibilidade import (
    CandidatoElegibilidade,
    ResultadoElegibilidade,
)
from central_preventiva.dominio.avaliador_risco import Criterio


@dataclass(frozen=True, slots=True)
class ContagemElegibilidade:
    """Quantidades de resultados de elegibilidade de uma execução."""

    incluidos: int
    excluidos: int


@dataclass(frozen=True, slots=True)
class RegistroElegibilidade:
    """Um resultado de elegibilidade persistido, pronto para consulta (ELEG-08, ELEG-09)."""

    id: UUID
    execucao_id: UUID | None
    evento_id: UUID
    regra_id: UUID
    segurado_id: UUID
    apolice_id: UUID
    elegivel: bool
    criterios: tuple[Criterio, ...]
    canal: str
    justificativa: str
    criado_em: datetime


class RepositorioCandidatosElegibilidade:
    """Lista segurados+apólices candidatos a uma avaliação de elegibilidade, por área."""

    def __init__(self, caminho: Path) -> None:
        """Vincula o repositório ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    def listar_candidatos(self, area: str) -> list[CandidatoElegibilidade]:
        """Lista todo segurado+apólice com apólice na área informada, qualquer situação.

        A situação da apólice (`ativa`/`cancelada`/`suspensa`) não filtra aqui — é o
        próprio `AvaliadorElegibilidade` que decide inclusão/exclusão a partir dela.
        """

        with abrir_conexao(self._caminho) as conexao:
            linhas = conexao.execute(
                "SELECT s.id, a.id, s.nome, a.codigo_ibge_area, s.canal_preferido, "
                "s.participa_de_alertas, a.tipo, a.situacao, a.coberturas "
                "FROM apolices AS a JOIN segurados AS s ON s.id = a.segurado_id "
                "WHERE a.codigo_ibge_area = ?",
                [area],
            ).fetchall()
        return [
            CandidatoElegibilidade(
                segurado_id=UUID(str(linha[0])),
                apolice_id=UUID(str(linha[1])),
                nome_segurado=str(linha[2]),
                codigo_ibge_area=str(linha[3]),
                canal_preferido=str(linha[4]),
                participa_de_alertas=bool(linha[5]),
                apolice_tipo=str(linha[6]),
                apolice_situacao=str(linha[7]),
                coberturas=tuple(linha[8]),
            )
            for linha in linhas
        ]


class RepositorioElegibilidades:
    """Persiste um resultado por combinação (dedução por `UNIQUE`, AD-10) e consulta."""

    def __init__(self, caminho: Path) -> None:
        """Vincula o repositório ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    def salvar(
        self,
        execucao_id: UUID,
        evento_id: UUID,
        regra_id: UUID,
        segurado_id: UUID,
        apolice_id: UUID,
        resultado: ResultadoElegibilidade,
    ) -> UUID | None:
        """Persiste o resultado da combinação, ou `None` se já existir (reprocessamento).

        `UNIQUE(execucao_id, evento_id, regra_id, segurado_id, apolice_id)` (migração
        `0006`) é a única garantia de "no máximo um resultado" — `ON CONFLICT DO NOTHING`
        torna a repetição um no-op idempotente, nunca um erro.
        """

        id_registro = uuid4()
        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                "INSERT INTO elegibilidades_historicas "
                "(id, execucao_id, evento_id, regra_id, segurado_id, apolice_id, "
                "elegivel, criterios, canal, justificativa) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT DO NOTHING RETURNING id",
                [
                    id_registro,
                    execucao_id,
                    evento_id,
                    regra_id,
                    segurado_id,
                    apolice_id,
                    resultado.elegivel,
                    serializar_criterios(resultado.criterios),
                    resultado.canal,
                    resultado.justificativa,
                ],
            ).fetchone()
        if linha is None:
            return None
        return UUID(str(linha[0]))

    def contar_por_execucao(self, execucao_id: UUID) -> ContagemElegibilidade:
        """Conta incluídos/excluídos já persistidos para a execução informada."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                "SELECT count(*) FILTER (WHERE elegivel), count(*) FILTER (WHERE NOT elegivel) "
                "FROM elegibilidades_historicas WHERE execucao_id = ?",
                [execucao_id],
            ).fetchone()
        assert linha is not None
        return ContagemElegibilidade(incluidos=int(linha[0]), excluidos=int(linha[1]))

    def listar_por_execucao(self, execucao_id: UUID) -> list[RegistroElegibilidade]:
        """Lista todos os resultados de elegibilidade da execução, mais recentes primeiro."""

        with abrir_conexao(self._caminho) as conexao:
            linhas = conexao.execute(
                "SELECT id, execucao_id, evento_id, regra_id, segurado_id, apolice_id, "
                "elegivel, criterios, canal, justificativa, criado_em "
                "FROM elegibilidades_historicas WHERE execucao_id = ? "
                "ORDER BY criado_em DESC",
                [execucao_id],
            ).fetchall()
        return [_registro_de_linha(linha) for linha in linhas]

    def obter_por_id(self, id_registro: UUID) -> RegistroElegibilidade | None:
        """Resolve um resultado específico de elegibilidade, ou `None` se não existir."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                "SELECT id, execucao_id, evento_id, regra_id, segurado_id, apolice_id, "
                "elegivel, criterios, canal, justificativa, criado_em "
                "FROM elegibilidades_historicas WHERE id = ?",
                [id_registro],
            ).fetchone()
        if linha is None:
            return None
        return _registro_de_linha(linha)


def _registro_de_linha(linha: tuple[object, ...]) -> RegistroElegibilidade:
    """Traduz uma linha de `elegibilidades_historicas` para `RegistroElegibilidade`."""

    return RegistroElegibilidade(
        id=UUID(str(linha[0])),
        execucao_id=None if linha[1] is None else UUID(str(linha[1])),
        evento_id=UUID(str(linha[2])),
        regra_id=UUID(str(linha[3])),
        segurado_id=UUID(str(linha[4])),
        apolice_id=UUID(str(linha[5])),
        elegivel=bool(linha[6]),
        criterios=desserializar_criterios(str(linha[7])),
        canal=str(linha[8]),
        justificativa=str(linha[9]),
        criado_em=linha[10],  # type: ignore[arg-type]
    )
