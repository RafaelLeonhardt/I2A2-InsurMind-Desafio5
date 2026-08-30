"""Repositórios DuckDB da coleta meteorológica do INMET."""

from pathlib import Path
from uuid import UUID, uuid4

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.aplicacao.portas_meteorologia import (
    AreaMonitorada,
    EstadoSincronizacao,
    OrigemSincronizacao,
    Sincronizacao,
)
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)

_ESTADOS_TERMINAIS = frozenset({EstadoSincronizacao.CONCLUIDO, EstadoSincronizacao.FALHA})


class RepositorioAreasMonitoradas:
    """Consulta o mapeamento entre estação real do INMET e área sintética (AD-007)."""

    def __init__(self, caminho: Path) -> None:
        """Vincula o repositório ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    def buscar_por_codigo_estacao(self, codigo_estacao_inmet: str) -> AreaMonitorada | None:
        """Resolve a área monitorada a partir do código real da estação, ou `None` se ausente."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                "SELECT id, codigo_estacao_inmet, nome_estacao, codigo_ibge_area, ativa "
                "FROM areas_monitoradas_inmet WHERE codigo_estacao_inmet = ?",
                [codigo_estacao_inmet],
            ).fetchone()
        if linha is None:
            return None
        return AreaMonitorada(
            id=UUID(str(linha[0])),
            codigo_estacao_inmet=str(linha[1]),
            nome_estacao=str(linha[2]),
            codigo_ibge_area=str(linha[3]),
            ativa=bool(linha[4]),
        )


class RepositorioEventosMeteorologicos:
    """Persiste eventos meteorológicos normalizados."""

    def __init__(self, caminho: Path) -> None:
        """Vincula o repositório ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    def salvar(self, evento: EventoMeteorologico) -> None:
        """Persiste o evento meteorológico normalizado em `eventos_meteorologicos`."""

        with abrir_conexao(self._caminho) as conexao:
            conexao.execute(
                "INSERT INTO eventos_meteorologicos "
                "(id, tipo, area, periodo_inicio, periodo_fim, intensidade, proveniencia, "
                "instante_observado) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    evento.id,
                    evento.tipo.value,
                    evento.area,
                    evento.periodo_inicio,
                    evento.periodo_fim,
                    evento.intensidade,
                    evento.proveniencia.value,
                    evento.instante_observado,
                ],
            )

    def buscar_por_id(self, id: UUID) -> EventoMeteorologico | None:
        """Retorna o evento com o id informado, ou `None` se não existir."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                "SELECT id, tipo, area, periodo_inicio, periodo_fim, intensidade, "
                "proveniencia, instante_observado FROM eventos_meteorologicos WHERE id = ?",
                [id],
            ).fetchone()
        if linha is None:
            return None
        return EventoMeteorologico(
            id=UUID(str(linha[0])),
            tipo=TipoEventoMeteorologico(str(linha[1])),
            area=str(linha[2]),
            periodo_inicio=linha[3],
            periodo_fim=linha[4],
            intensidade=float(linha[5]),
            proveniencia=ProvenienciaEvento(str(linha[6])),
            instante_observado=linha[7],
        )


class RepositorioSincronizacoes:
    """Persiste e consulta o histórico de tentativas de sincronização meteorológica."""

    def __init__(self, caminho: Path) -> None:
        """Vincula o repositório ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    def criar(
        self,
        requisicao_id: UUID,
        area_monitorada_id: UUID,
        origem: OrigemSincronizacao,
        estado: EstadoSincronizacao,
    ) -> Sincronizacao:
        """Persiste uma nova tentativa de sincronização, antes de qualquer resposta ao chamador."""

        id_sincronizacao = uuid4()
        with abrir_conexao(self._caminho) as conexao:
            conexao.execute(
                "INSERT INTO sincronizacoes_meteorologicas "
                "(id, requisicao_id, area_monitorada_id, origem, estado, registros_validos) "
                "VALUES (?, ?, ?, ?, ?, 0)",
                [id_sincronizacao, requisicao_id, area_monitorada_id, origem.value, estado.value],
            )
            linha = conexao.execute(
                "SELECT iniciado_em FROM sincronizacoes_meteorologicas WHERE id = ?",
                [id_sincronizacao],
            ).fetchone()
        assert linha is not None
        return Sincronizacao(
            id=id_sincronizacao,
            requisicao_id=requisicao_id,
            area_monitorada_id=area_monitorada_id,
            origem=origem,
            estado=estado,
            registros_validos=0,
            motivo_falha=None,
            iniciado_em=linha[0],
            finalizado_em=None,
        )

    def atualizar_estado(
        self,
        id: UUID,
        estado: EstadoSincronizacao,
        registros_validos: int = 0,
        motivo_falha: str | None = None,
    ) -> None:
        """Fecha ou avança o estado de uma sincronização já persistida."""

        finalizar = estado in _ESTADOS_TERMINAIS
        with abrir_conexao(self._caminho) as conexao:
            if finalizar:
                conexao.execute(
                    "UPDATE sincronizacoes_meteorologicas SET estado = ?, registros_validos = ?, "
                    "motivo_falha = ?, finalizado_em = now() WHERE id = ?",
                    [estado.value, registros_validos, motivo_falha, id],
                )
            else:
                conexao.execute(
                    "UPDATE sincronizacoes_meteorologicas SET estado = ?, registros_validos = ?, "
                    "motivo_falha = ? WHERE id = ?",
                    [estado.value, registros_validos, motivo_falha, id],
                )

    def listar_recentes(self) -> tuple[Sincronizacao, ...]:
        """Lista o histórico de sincronizações, da mais recente para a mais antiga."""

        with abrir_conexao(self._caminho) as conexao:
            linhas = conexao.execute(
                "SELECT id, requisicao_id, area_monitorada_id, origem, estado, "
                "registros_validos, motivo_falha, iniciado_em, finalizado_em "
                "FROM sincronizacoes_meteorologicas ORDER BY iniciado_em DESC"
            ).fetchall()
        return tuple(
            Sincronizacao(
                id=UUID(str(linha[0])),
                requisicao_id=UUID(str(linha[1])),
                area_monitorada_id=UUID(str(linha[2])),
                origem=OrigemSincronizacao(str(linha[3])),
                estado=EstadoSincronizacao(str(linha[4])),
                registros_validos=int(linha[5]),
                motivo_falha=None if linha[6] is None else str(linha[6]),
                iniciado_em=linha[7],
                finalizado_em=linha[8],
            )
            for linha in linhas
        )
