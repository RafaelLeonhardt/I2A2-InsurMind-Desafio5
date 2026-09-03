"""Repositórios de candidatos e resultados de elegibilidade preventiva (ELEG-04..07)."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

import duckdb

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.serializacao_criterios import (
    desserializar_criterios,
    serializar_criterios,
)
from central_preventiva.dominio.avaliador_elegibilidade import (
    OPERANDO_AREA_AFETADA,
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
    """Um resultado de elegibilidade persistido, já enriquecido para consulta/explicação
    (ELEG-08, ELEG-09).

    `nome_segurado` é snapshot imutável (coluna própria, migração `0007`) — lido ao vivo
    de `segurados.nome` reescreveria a explicação histórica se o nome mudasse depois de
    uma avaliação concluída (AD-11, ELEG-04.3). `codigo_ibge_area` é derivado do próprio
    `criterios` já persistido (o critério "área afetada" sempre carrega o valor
    observado no momento da avaliação) — não uma segunda cópia armazenada, mas também
    não uma releitura ao vivo de `apolices`. `regra_versao` vem de `JOIN` em `regras`
    porque cada versão é uma linha própria e imutável (só `estado` é atualizado, nunca
    `versao`) — um `JOIN` nela nunca reescreve a explicação histórica.
    """

    id: UUID
    execucao_id: UUID | None
    evento_id: UUID
    regra_id: UUID
    regra_versao: int
    segurado_id: UUID
    nome_segurado: str
    apolice_id: UUID
    codigo_ibge_area: str
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
        nome_segurado: str,
        resultado: ResultadoElegibilidade,
    ) -> UUID | None:
        """Persiste o resultado da combinação, ou `None` se já existir (reprocessamento).

        `UNIQUE(execucao_id, evento_id, regra_id, segurado_id, apolice_id)` (migração
        `0006`) é a única garantia de "no máximo um resultado" — `ON CONFLICT DO NOTHING`
        torna a repetição um no-op idempotente, nunca um erro. `nome_segurado` é gravado
        como snapshot (migração `0007`, AD-11): o nome usado na avaliação, não uma
        referência viva a `segurados.nome`.
        """

        id_registro = uuid4()
        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                "INSERT INTO elegibilidades_historicas "
                "(id, execucao_id, evento_id, regra_id, segurado_id, apolice_id, "
                "elegivel, criterios, canal, nome_segurado, justificativa) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
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
                    nome_segurado,
                    resultado.justificativa,
                ],
            ).fetchone()
        if linha is None:
            return None
        return UUID(str(linha[0]))

    def copiar_para_execucao(
        self,
        execucao_origem_id: UUID,
        nova_execucao_id: UUID,
        conexao: duckdb.DuckDBPyConnection | None = None,
    ) -> int:
        """Copia para a nova execução todas as elegibilidades da origem (AD-012).

        Copia incluídas e excluídas, com `id` novo e o `execucao_id` da nova execução, e
        conteúdo de snapshot idêntico ao da origem. A nova execução nunca referencia as
        linhas da origem: as `UNIQUE` de `contextos_agente.elegibilidade_id` (3.1) e de
        `mensagens (elegibilidade_id, canal)` (3.2) tornariam a retentativa inviável sobre
        elas. A `UNIQUE (execucao_id, evento_id, regra_id, segurado_id, apolice_id)` de 2.5
        legitima as cópias, porque o `execucao_id` difere.

        Quando `conexao` é informada, a cópia roda na transação já aberta pelo chamador —
        é assim que `criar_correlacionada` a torna atômica com a criação da execução.
        Devolve o número de linhas copiadas.
        """

        if conexao is not None:
            return self._copiar(conexao, execucao_origem_id, nova_execucao_id)
        with abrir_conexao(self._caminho) as propria:
            return self._copiar(propria, execucao_origem_id, nova_execucao_id)

    def _copiar(
        self,
        conexao: duckdb.DuckDBPyConnection,
        execucao_origem_id: UUID,
        nova_execucao_id: UUID,
    ) -> int:
        """Executa a cópia das elegibilidades na conexão informada."""

        linhas = conexao.execute(
            "INSERT INTO elegibilidades_historicas "
            "(id, execucao_id, evento_id, regra_id, segurado_id, apolice_id, elegivel, "
            "criterios, canal, nome_segurado, justificativa) "
            "SELECT uuid(), ?, evento_id, regra_id, segurado_id, apolice_id, elegivel, "
            "criterios, canal, nome_segurado, justificativa "
            "FROM elegibilidades_historicas WHERE execucao_id = ? "
            "RETURNING id",
            [nova_execucao_id, execucao_origem_id],
        ).fetchall()
        return len(linhas)

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
                f"{_SELECT_REGISTRO_ENRIQUECIDO} WHERE e.execucao_id = ? "
                "ORDER BY e.criado_em DESC",
                [execucao_id],
            ).fetchall()
        return [_registro_de_linha(linha) for linha in linhas]

    def obter_por_id(self, id_registro: UUID) -> RegistroElegibilidade | None:
        """Resolve um resultado específico de elegibilidade, ou `None` se não existir."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                f"{_SELECT_REGISTRO_ENRIQUECIDO} WHERE e.id = ?",
                [id_registro],
            ).fetchone()
        if linha is None:
            return None
        return _registro_de_linha(linha)


_SELECT_REGISTRO_ENRIQUECIDO = (
    "SELECT e.id, e.execucao_id, e.evento_id, e.regra_id, r.versao, e.segurado_id, "
    "e.nome_segurado, e.apolice_id, e.elegivel, e.criterios, e.canal, "
    "e.justificativa, e.criado_em "
    "FROM elegibilidades_historicas AS e "
    "JOIN regras AS r ON r.id = e.regra_id"
)


def _codigo_ibge_area_de(criterios: tuple[Criterio, ...]) -> str:
    """Deriva a área do próprio snapshot de critérios já persistido, buscando o critério
    pelo nome estável `OPERANDO_AREA_AFETADA` — nunca pela posição (a ordem em que
    `avaliador_elegibilidade.avaliar` produz os critérios é um detalhe de implementação,
    não um contrato) — e nunca uma releitura ao vivo de `apolices.codigo_ibge_area`
    (AD-11).

    Linhas semeadas de demonstração (`execucao_id IS NULL`) não têm critérios reais
    (migração `0007`); nunca alcançam um cliente real (a listagem filtra por
    `execucao_id`, e o detalhe exige que ele bata com o da rota), então o fallback vazio
    aqui nunca é observável de fora.
    """

    criterio_area = next(
        (c for c in criterios if c.operando == OPERANDO_AREA_AFETADA), None
    )
    return criterio_area.valor_observado if criterio_area is not None else ""


def _registro_de_linha(linha: tuple[object, ...]) -> RegistroElegibilidade:
    """Traduz uma linha de `_SELECT_REGISTRO_ENRIQUECIDO` para `RegistroElegibilidade`."""

    criterios = desserializar_criterios(str(linha[9]))
    return RegistroElegibilidade(
        id=UUID(str(linha[0])),
        execucao_id=None if linha[1] is None else UUID(str(linha[1])),
        evento_id=UUID(str(linha[2])),
        regra_id=UUID(str(linha[3])),
        regra_versao=int(linha[4]),  # type: ignore[arg-type]
        segurado_id=UUID(str(linha[5])),
        nome_segurado=str(linha[6]),
        apolice_id=UUID(str(linha[7])),
        codigo_ibge_area=_codigo_ibge_area_de(criterios),
        elegivel=bool(linha[8]),
        criterios=criterios,
        canal=str(linha[10]),
        justificativa=str(linha[11]),
        criado_em=linha[12],  # type: ignore[arg-type]
    )
