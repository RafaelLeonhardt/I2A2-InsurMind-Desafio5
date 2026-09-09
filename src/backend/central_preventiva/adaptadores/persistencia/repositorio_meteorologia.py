"""Repositórios DuckDB da coleta meteorológica do INMET."""

from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.aplicacao.portas_meteorologia import (
    AreaMonitorada,
    CodigoResultadoTentativa,
    EstadoSincronizacao,
    OrigemSincronizacao,
    Sincronizacao,
    TentativaColeta,
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

    def listar_ativas(self) -> tuple[AreaMonitorada, ...]:
        """Lista as áreas monitoradas atualmente ativas."""

        with abrir_conexao(self._caminho) as conexao:
            linhas = conexao.execute(
                "SELECT id, codigo_estacao_inmet, nome_estacao, codigo_ibge_area, ativa "
                "FROM areas_monitoradas_inmet WHERE ativa = true"
            ).fetchall()
        return tuple(
            AreaMonitorada(
                id=UUID(str(linha[0])),
                codigo_estacao_inmet=str(linha[1]),
                nome_estacao=str(linha[2]),
                codigo_ibge_area=str(linha[3]),
                ativa=bool(linha[4]),
            )
            for linha in linhas
        )

    def buscar_por_id(self, id: UUID) -> AreaMonitorada | None:
        """Resolve a área monitorada a partir do seu identificador interno, ou `None`."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                "SELECT id, codigo_estacao_inmet, nome_estacao, codigo_ibge_area, ativa "
                "FROM areas_monitoradas_inmet WHERE id = ?",
                [id],
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
        """Persiste o evento meteorológico normalizado, sem duplicar por conteúdo (AD-010).

        `UNIQUE (tipo, area, periodo_inicio, periodo_fim)` (migração 0003) mais o
        insert-or-noop garantem que uma coleta que observa o mesmo evento de novo (ex.:
        recuperação real após um cenário sintético) não duplica a linha.
        """

        with abrir_conexao(self._caminho) as conexao:
            conexao.execute(
                "INSERT INTO eventos_meteorologicos "
                "(id, tipo, area, periodo_inicio, periodo_fim, intensidade, proveniencia, "
                "instante_observado) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT DO NOTHING",
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

    def listar(self) -> tuple[EventoMeteorologico, ...]:
        """Lista os eventos meteorológicos, do mais recente para o mais antigo."""

        with abrir_conexao(self._caminho) as conexao:
            linhas = conexao.execute(
                "SELECT id, tipo, area, periodo_inicio, periodo_fim, intensidade, "
                "proveniencia, instante_observado FROM eventos_meteorologicos "
                "ORDER BY instante_observado DESC"
            ).fetchall()
        return tuple(
            EventoMeteorologico(
                id=UUID(str(linha[0])),
                tipo=TipoEventoMeteorologico(str(linha[1])),
                area=str(linha[2]),
                periodo_inicio=linha[3],
                periodo_fim=linha[4],
                intensidade=float(linha[5]),
                proveniencia=ProvenienciaEvento(str(linha[6])),
                instante_observado=linha[7],
            )
            for linha in linhas
        )

    def mapear_execucoes_por_evento(self) -> dict[UUID, tuple[UUID, str]]:
        """Liga cada evento à sua execução preventiva mais recente (História 6.1).

        A ligação física já existe em `avaliacoes_risco` (`evento_id` + `execucao_id`
        persistidos juntos, migração 0004) — este método só a expõe para a listagem de
        eventos, sem tocar no dataclass de domínio `EventoMeteorologico`, que é reusado
        por `salvar`/`buscar_por_id`/`listar_sinteticos_por_tipo` e não tem relação com
        execução. `QUALIFY` mantém só a avaliação mais recente por evento, caso um
        evento venha a ser reavaliado mais de uma vez (o schema não impede).
        """

        with abrir_conexao(self._caminho) as conexao:
            linhas = conexao.execute(
                "SELECT ar.evento_id, ar.execucao_id, ep.estado "
                "FROM avaliacoes_risco ar "
                "JOIN execucao_preventiva ep ON ep.id = ar.execucao_id "
                "QUALIFY ROW_NUMBER() "
                "OVER (PARTITION BY ar.evento_id ORDER BY ar.criado_em DESC) = 1"
            ).fetchall()
        return {
            UUID(str(linha[0])): (UUID(str(linha[1])), str(linha[2])) for linha in linhas
        }

    def listar_sinteticos_por_tipo(
        self, tipo: TipoEventoMeteorologico
    ) -> tuple[EventoMeteorologico, ...]:
        """Lista os eventos sintéticos do tipo informado (cenários de teste de regra, 2.4)."""

        with abrir_conexao(self._caminho) as conexao:
            linhas = conexao.execute(
                "SELECT id, tipo, area, periodo_inicio, periodo_fim, intensidade, "
                "proveniencia, instante_observado FROM eventos_meteorologicos "
                "WHERE tipo = ? AND proveniencia = 'sintetico' ORDER BY instante_observado",
                [tipo.value],
            ).fetchall()
        return tuple(
            EventoMeteorologico(
                id=UUID(str(linha[0])),
                tipo=TipoEventoMeteorologico(str(linha[1])),
                area=str(linha[2]),
                periodo_inicio=linha[3],
                periodo_fim=linha[4],
                intensidade=float(linha[5]),
                proveniencia=ProvenienciaEvento(str(linha[6])),
                instante_observado=linha[7],
            )
            for linha in linhas
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

    def buscar_por_id(self, id: UUID) -> Sincronizacao | None:
        """Resolve a sincronização a partir do seu identificador, ou `None` se ausente."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                "SELECT id, requisicao_id, area_monitorada_id, origem, estado, "
                "registros_validos, motivo_falha, iniciado_em, finalizado_em "
                "FROM sincronizacoes_meteorologicas WHERE id = ?",
                [id],
            ).fetchone()
        if linha is None:
            return None
        return Sincronizacao(
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


class RepositorioTentativasColeta:
    """Persiste e consulta as tentativas individuais de uma coleta com retry (RESIL-02)."""

    def __init__(self, caminho: Path) -> None:
        """Vincula o repositório ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    def registrar_tentativa(
        self,
        sincronizacao_id: UUID,
        numero_tentativa: int,
        codigo_resultado: CodigoResultadoTentativa,
        iniciado_em: datetime,
        finalizado_em: datetime,
    ) -> None:
        """Persiste uma tentativa individual, assim que ela termina."""

        with abrir_conexao(self._caminho) as conexao:
            conexao.execute(
                "INSERT INTO tentativas_coleta_meteorologica "
                "(id, sincronizacao_id, numero_tentativa, codigo_resultado, iniciado_em, "
                "finalizado_em) VALUES (?, ?, ?, ?, ?, ?)",
                [
                    uuid4(),
                    sincronizacao_id,
                    numero_tentativa,
                    codigo_resultado.value,
                    iniciado_em,
                    finalizado_em,
                ],
            )

    def listar_tentativas(self, sincronizacao_id: UUID) -> tuple[TentativaColeta, ...]:
        """Lista as tentativas de uma sincronização, em ordem crescente de número."""

        with abrir_conexao(self._caminho) as conexao:
            linhas = conexao.execute(
                "SELECT id, sincronizacao_id, numero_tentativa, codigo_resultado, "
                "iniciado_em, finalizado_em FROM tentativas_coleta_meteorologica "
                "WHERE sincronizacao_id = ? ORDER BY numero_tentativa ASC",
                [sincronizacao_id],
            ).fetchall()
        return tuple(
            TentativaColeta(
                id=UUID(str(linha[0])),
                sincronizacao_id=UUID(str(linha[1])),
                numero_tentativa=int(linha[2]),
                codigo_resultado=CodigoResultadoTentativa(str(linha[3])),
                iniciado_em=linha[4],
                finalizado_em=linha[5],
            )
            for linha in linhas
        )


class RepositorioCenariosSinteticosAtivados:
    """Registra quando/qual cenário sintético de contingência foi ativado (RESIL-13)."""

    def __init__(self, caminho: Path) -> None:
        """Vincula o repositório ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    def registrar(self, sincronizacao_id: UUID, identificador_cenario: str) -> None:
        """Persiste a ativação de um cenário sintético, correlacionada à sua sincronização."""

        with abrir_conexao(self._caminho) as conexao:
            conexao.execute(
                "INSERT INTO cenarios_sinteticos_ativados "
                "(id, sincronizacao_id, identificador_cenario) VALUES (?, ?, ?)",
                [uuid4(), sincronizacao_id, identificador_cenario],
            )
