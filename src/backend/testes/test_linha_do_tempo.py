"""Testes do caso de uso da linha do tempo ponta a ponta (TIMELINE-01..09).

Os repositórios são os reais, sobre um banco temporário migrado: a linha do tempo é uma
agregação de leitura pura sobre schema já garantido por 2.1–2.6/3.1–3.6/4.3, sem nenhuma
escrita própria a testar com dublê.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_criticas import (
    RepositorioAvaliacoesCriticas,
)
from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_risco import (
    RepositorioAvaliacoesRisco,
)
from central_preventiva.adaptadores.persistencia.repositorio_decisoes_humanas import (
    RepositorioDecisoesHumanas,
)
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RepositorioElegibilidades,
)
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    MensagemAprovada,
    RepositorioEntregasSimuladas,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    RepositorioExcecoesOperacionais,
    RepositorioExecucaoPreventiva,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    RepositorioMensagens,
)
from central_preventiva.adaptadores.persistencia.repositorio_visualizacoes_comunicado import (
    RepositorioVisualizacoesComunicado,
)
from central_preventiva.adaptadores.persistencia.serializacao_criterios import (
    serializar_criterios,
)
from central_preventiva.aplicacao.linha_do_tempo import (
    TIPO_CRITICA,
    TIPO_DECISAO_HUMANA,
    TIPO_ELEGIBILIDADE,
    TIPO_EXCECAO,
    TIPO_EXECUCAO,
    TIPO_GERACAO,
    TIPO_RISCO,
    TIPO_SIMULACAO,
    TIPO_VISUALIZACAO,
    PortasLinhaDoTempo,
    ServicoLinhaDoTempo,
)
from central_preventiva.dominio.avaliacao_critica import CategoriaCritica, MotivoCritica
from central_preventiva.dominio.avaliador_risco import ResultadoAvaliacaoRisco
from central_preventiva.dominio.decisao_humana import ResultadoDecisaoHumana
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

REGRA_ID = UUID("33333333-3333-3333-3333-333333333333")
REGRA_VERSAO = 2
EVENTO_ID = uuid4()
MODELO = "gpt-4o-mini"
VERSAO_PROMPT = "v1"
MOTIVO_TOM = MotivoCritica(CategoriaCritica.TOM, "O texto usa tom alarmista.")


class Cenario:
    """Reúne o caso de uso real e os repositórios reais sobre um banco temporário migrado."""

    def __init__(self, tmp_path: Path, estado: EstadoExecucao = EstadoExecucao.CONCLUIDA) -> None:
        """Migra o banco, semeia a regra e cria a execução no estado informado."""

        self.caminho = tmp_path / "central_preventiva.duckdb"
        ExecutorMigracoes(self.caminho).aplicar_pendentes()
        self.execucoes = RepositorioExecucaoPreventiva(self.caminho)
        self.avaliacoes_risco = RepositorioAvaliacoesRisco(self.caminho)
        self.elegibilidades = RepositorioElegibilidades(self.caminho)
        self.mensagens = RepositorioMensagens(self.caminho)
        self.avaliacoes_criticas = RepositorioAvaliacoesCriticas(self.caminho)
        self.decisoes = RepositorioDecisoesHumanas(self.caminho)
        self.excecoes = RepositorioExcecoesOperacionais(self.caminho)
        self.entregas = RepositorioEntregasSimuladas(self.caminho)
        self.visualizacoes = RepositorioVisualizacoesComunicado(self.caminho)
        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(
                "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
                "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
                "VALUES (?, 'chuva_intensa', 50.0, '9990001', 'residencial', 'alagamento', "
                "6, 'sms', ?, 'ativa')",
                [REGRA_ID, REGRA_VERSAO],
            )
        self.execucao_id = self.execucoes.criar(estado)
        self.servico = ServicoLinhaDoTempo(
            PortasLinhaDoTempo(
                execucoes=self.execucoes,
                avaliacoes_risco=self.avaliacoes_risco,
                elegibilidades=self.elegibilidades,
                mensagens=self.mensagens,
                avaliacoes_criticas=self.avaliacoes_criticas,
                decisoes=self.decisoes,
                excecoes=self.excecoes,
                entregas=self.entregas,
                visualizacoes=self.visualizacoes,
            )
        )

    def marco(self, marco: str, causa: str | None = None, execucao_id: UUID | None = None) -> None:
        """Registra um marco de execução (2.6)."""

        self.execucoes.registrar_marco(execucao_id or self.execucao_id, marco, causa)

    def risco(
        self,
        relevante: bool = True,
        regra_id: UUID | None = REGRA_ID,
        regra_versao: int | None = REGRA_VERSAO,
        motivo: str = "Chuva acima do limiar.",
        execucao_id: UUID | None = None,
    ) -> None:
        """Persiste a avaliação de risco/regra da execução (2.3)."""

        self.avaliacoes_risco.salvar(
            execucao_id or self.execucao_id,
            EVENTO_ID,
            regra_id,
            regra_versao,
            ResultadoAvaliacaoRisco(relevante=relevante, criterios=(), motivo=motivo),
        )

    def elegibilidade(
        self,
        canal: str = "sms",
        nome: str = "Pessoa Teste",
        elegivel: bool = True,
        execucao_id: UUID | None = None,
    ) -> UUID:
        """Insere um item do público elegível, no formato que 2.5 grava."""

        id_registro = uuid4()
        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(
                "INSERT INTO elegibilidades_historicas "
                "(id, execucao_id, evento_id, regra_id, segurado_id, "
                "apolice_id, elegivel, criterios, canal, nome_segurado, justificativa) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
                "'Atende integralmente aos critérios da regra ativa.')",
                [
                    id_registro,
                    execucao_id or self.execucao_id,
                    EVENTO_ID,
                    REGRA_ID,
                    uuid4(),
                    uuid4(),
                    elegivel,
                    serializar_criterios(()),
                    canal,
                    nome,
                ],
            )
        return id_registro

    def mensagem(
        self,
        canal: Canal = Canal.SMS,
        execucao_id: UUID | None = None,
        elegibilidade_id: UUID | None = None,
    ) -> UUID:
        """Cria uma mensagem vinculada a uma elegibilidade recém-semeada."""

        elegibilidade_id = elegibilidade_id or self.elegibilidade(
            canal=canal.value, execucao_id=execucao_id
        )
        return self.mensagens.criar(execucao_id or self.execucao_id, elegibilidade_id, canal)

    def versao(
        self,
        mensagem_id: UUID,
        numero_tentativa: int = 1,
        valida: bool = True,
        motivo_invalidez: str | None = None,
    ) -> UUID:
        """Persiste uma tentativa de geração (3.2)."""

        return self.mensagens.salvar_versao(
            mensagem_id, numero_tentativa, SaidaCanal(corpo="Chuva forte hoje."), 100.0,
            MODELO, VERSAO_PROMPT, 5, 5, valida, motivo_invalidez,
        )

    def critica(self, versao_id: UUID, aprovada: bool = True) -> None:
        """Persiste a avaliação crítica de uma versão (3.3)."""

        self.avaliacoes_criticas.salvar(
            versao_id, aprovada, () if aprovada else (MOTIVO_TOM,), MODELO, 80.0
        )

    def decisao(
        self,
        mensagem_id: UUID,
        versao_id: UUID,
        resultado: ResultadoDecisaoHumana = ResultadoDecisaoHumana.APROVAR,
        justificativa: str | None = None,
    ) -> None:
        """Persiste uma decisão humana sobre uma versão (3.5)."""

        self.decisoes.salvar(mensagem_id, versao_id, "administrador", resultado, justificativa)

    def entrega(
        self, mensagem_id: UUID, canal: Canal = Canal.SMS, execucao_id: UUID | None = None
    ) -> UUID:
        """Persiste a entrega simulada de uma mensagem aprovada (3.6)."""

        [entrega_id] = self.entregas.criar_lote(
            execucao_id or self.execucao_id,
            [MensagemAprovada(mensagem_id, canal, SaidaCanal(corpo="Chuva forte hoje."))],
        )
        return entrega_id

    def visualizar(self, entrega_id: UUID, segurado_id: UUID | None = None) -> None:
        """Registra a primeira visualização do comunicado (4.3)."""

        self.visualizacoes.registrar_primeira_visualizacao(entrega_id, segurado_id or uuid4())

    def excecao(
        self,
        causa: str,
        tentativas: int = 1,
        impacto: str = "Impacto.",
        mensagem_id: UUID | None = None,
        execucao_id: UUID | None = None,
    ) -> None:
        """Registra uma Exceção operacional, de execução ou de mensagem (2.2/3.4)."""

        self.excecoes.registrar(
            execucao_id or self.execucao_id, causa, tentativas, impacto, mensagem_id
        )

    def definir_timestamp(self, tabela: str, coluna: str, id_valor: UUID, quando: datetime) -> None:
        """Sobrescreve o timestamp de uma linha, para provar a ordenação cronológica real,
        sem depender da velocidade de inserção do teste."""

        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(f"UPDATE {tabela} SET {coluna} = ? WHERE id = ?", [quando, id_valor])


def test_execucao_completa_traz_todos_os_marcos_na_ordem_cronologica_correta(
    tmp_path: Path,
) -> None:
    """TIMELINE-01/02: coleta→risco→elegibilidade→geração→crítica→decisão→simulação→
    visualização aparecem todos, cada um com timestamp/ator/ação/resultado/correlação, em
    ordem cronológica não decrescente."""

    cenario = Cenario(tmp_path)

    cenario.marco("coleta_concluida")
    cenario.risco(relevante=True)
    elegibilidade_id = cenario.elegibilidade()
    mensagem_id = cenario.mensagem(elegibilidade_id=elegibilidade_id)
    versao_id = cenario.versao(mensagem_id)
    cenario.critica(versao_id, aprovada=True)
    cenario.decisao(mensagem_id, versao_id, ResultadoDecisaoHumana.APROVAR)
    cenario.mensagens.transicionar(mensagem_id, 1, EstadoMensagem.APROVADA)
    cenario.mensagens.transicionar(mensagem_id, 2, EstadoMensagem.SIMULADA_ENTREGUE)
    entrega_id = cenario.entrega(mensagem_id)
    cenario.visualizar(entrega_id)

    linha_do_tempo = cenario.servico.montar(cenario.execucao_id)

    assert linha_do_tempo is not None
    tipos_presentes = {marco.tipo for marco in linha_do_tempo.marcos}
    assert tipos_presentes == {
        TIPO_EXECUCAO,
        TIPO_RISCO,
        TIPO_ELEGIBILIDADE,
        TIPO_GERACAO,
        TIPO_CRITICA,
        TIPO_DECISAO_HUMANA,
        TIPO_SIMULACAO,
        TIPO_VISUALIZACAO,
    }
    timestamps = [marco.timestamp for marco in linha_do_tempo.marcos]
    assert timestamps == sorted(timestamps)
    for marco in linha_do_tempo.marcos:
        assert marco.timestamp is not None
        assert marco.ator
        assert marco.acao
        assert marco.resultado
        assert marco.correlacao
    marco_visualizacao = next(m for m in linha_do_tempo.marcos if m.tipo == TIPO_VISUALIZACAO)
    assert marco_visualizacao.resultado == "visualizada no portal"
    assert marco_visualizacao.mensagem_id == mensagem_id


def test_execucao_sem_risco_termina_no_motivo_sem_etapas_inexistentes(tmp_path: Path) -> None:
    """TIMELINE-03: `sem_risco` não produz nenhum marco de geração/crítica/decisão/simulação/
    visualização — só coleta e a avaliação de risco que a encerrou."""

    cenario = Cenario(tmp_path, estado=EstadoExecucao.SEM_RISCO)
    cenario.marco("coleta_concluida")
    cenario.risco(relevante=False, regra_id=None, regra_versao=None, motivo="sem_regra_ativa")
    cenario.marco(EstadoExecucao.SEM_RISCO.value)

    linha_do_tempo = cenario.servico.montar(cenario.execucao_id)

    assert linha_do_tempo is not None
    tipos_presentes = {marco.tipo for marco in linha_do_tempo.marcos}
    assert tipos_presentes == {TIPO_EXECUCAO, TIPO_RISCO}
    assert TIPO_GERACAO not in tipos_presentes
    assert TIPO_CRITICA not in tipos_presentes
    assert TIPO_SIMULACAO not in tipos_presentes
    assert TIPO_VISUALIZACAO not in tipos_presentes


def test_execucao_sem_elegiveis_termina_no_motivo_sem_etapas_inexistentes(
    tmp_path: Path,
) -> None:
    """TIMELINE-03: `sem_elegiveis` traz elegibilidade (todas excluídas), mas nada depois."""

    cenario = Cenario(tmp_path, estado=EstadoExecucao.SEM_ELEGIVEIS)
    cenario.marco("coleta_concluida")
    cenario.risco(relevante=True)
    cenario.elegibilidade(elegivel=False)
    cenario.marco(EstadoExecucao.SEM_ELEGIVEIS.value)

    linha_do_tempo = cenario.servico.montar(cenario.execucao_id)

    assert linha_do_tempo is not None
    tipos_presentes = {marco.tipo for marco in linha_do_tempo.marcos}
    assert tipos_presentes == {TIPO_EXECUCAO, TIPO_RISCO, TIPO_ELEGIBILIDADE}
    marco_elegibilidade = next(m for m in linha_do_tempo.marcos if m.tipo == TIPO_ELEGIBILIDADE)
    assert marco_elegibilidade.resultado == "excluído"


def test_mensagem_com_tres_tentativas_traz_versoes_avaliacoes_e_decisoes_na_ordem(
    tmp_path: Path,
) -> None:
    """TIMELINE-04: 3 tentativas (2 reprovadas + 1 aprovada) aparecem relacionadas à mensagem
    e à execução, na ordem cronológica real das tentativas."""

    cenario = Cenario(tmp_path)
    mensagem_id = cenario.mensagem()
    base = datetime(2026, 9, 1, 10, 0, tzinfo=UTC)

    versao_1 = cenario.versao(mensagem_id, numero_tentativa=1)
    cenario.critica(versao_1, aprovada=False)
    cenario.decisao(mensagem_id, versao_1, ResultadoDecisaoHumana.REGENERAR, "Tom alarmista.")
    cenario.mensagens.incrementar_tentativa(mensagem_id, 1)

    versao_2 = cenario.versao(mensagem_id, numero_tentativa=2)
    cenario.critica(versao_2, aprovada=False)
    cenario.decisao(mensagem_id, versao_2, ResultadoDecisaoHumana.REGENERAR, "Ainda alarmista.")
    cenario.mensagens.incrementar_tentativa(mensagem_id, 2)

    versao_3 = cenario.versao(mensagem_id, numero_tentativa=3)
    cenario.critica(versao_3, aprovada=True)
    cenario.decisao(mensagem_id, versao_3, ResultadoDecisaoHumana.APROVAR)

    # Timestamps explícitos: a ordem real de tentativa deve valer, não a ordem de inserção.
    for indice, versao_id in enumerate((versao_1, versao_2, versao_3)):
        cenario.definir_timestamp(
            "versoes_mensagem", "criado_em", versao_id, base + timedelta(minutes=indice)
        )

    linha_do_tempo = cenario.servico.montar(cenario.execucao_id)

    assert linha_do_tempo is not None
    marcos_geracao = [m for m in linha_do_tempo.marcos if m.tipo == TIPO_GERACAO]
    assert len(marcos_geracao) == 3
    assert [m.timestamp for m in marcos_geracao] == sorted(m.timestamp for m in marcos_geracao)
    assert all(m.mensagem_id == mensagem_id for m in marcos_geracao)
    assert [m.acao for m in marcos_geracao] == [
        "geração — tentativa 1",
        "geração — tentativa 2",
        "geração — tentativa 3",
    ]
    marcos_decisao = [m for m in linha_do_tempo.marcos if m.tipo == TIPO_DECISAO_HUMANA]
    assert [m.resultado for m in marcos_decisao] == ["regenerar", "regenerar", "aprovar"]


def test_execucao_correlacionada_navega_origem_e_retentativa_sem_misturar_marcos(
    tmp_path: Path,
) -> None:
    """TIMELINE-05: origem e retentativa mantêm IDs, estados e marcos separados nas duas
    direções."""

    cenario = Cenario(tmp_path, estado=EstadoExecucao.FALHOU_COLETA)
    cenario.marco("falhou_coleta", causa="TimeoutException")
    retentativa_id = cenario.execucoes.criar_correlacionada(
        EstadoExecucao.COLETANDO, cenario.execucao_id
    )
    cenario.marco("coleta_concluida", execucao_id=retentativa_id)

    linha_origem = cenario.servico.montar(cenario.execucao_id)
    linha_retentativa = cenario.servico.montar(retentativa_id)

    assert linha_origem is not None
    assert linha_retentativa is not None
    assert linha_origem.execucao_origem_id is None
    assert linha_origem.retentativas == (retentativa_id,)
    assert linha_retentativa.execucao_origem_id == cenario.execucao_id
    assert linha_retentativa.retentativas == ()
    assert {m.acao for m in linha_origem.marcos} == {"falhou_coleta"}
    assert {m.acao for m in linha_retentativa.marcos} == {"coleta_concluida"}


def test_comunicado_reaberto_tres_vezes_resulta_em_um_unico_marco_de_visualizacao(
    tmp_path: Path,
) -> None:
    """TIMELINE-06/07: reabrir o comunicado 3 vezes (via 4.3) nunca duplica o marco."""

    cenario = Cenario(tmp_path)
    mensagem_id = cenario.mensagem()
    entrega_id = cenario.entrega(mensagem_id)
    segurado_id = uuid4()

    cenario.visualizar(entrega_id, segurado_id)
    cenario.visualizar(entrega_id, segurado_id)
    cenario.visualizar(entrega_id, uuid4())

    linha_do_tempo = cenario.servico.montar(cenario.execucao_id)

    assert linha_do_tempo is not None
    marcos_visualizacao = [m for m in linha_do_tempo.marcos if m.tipo == TIPO_VISUALIZACAO]
    assert len(marcos_visualizacao) == 1


def test_excecao_de_execucao_e_de_mensagem_aparecem_intercaladas_na_ordem_real(
    tmp_path: Path,
) -> None:
    """Edge Case: exceções técnicas aparecem na ordem cronológica real, sem esconder nem
    reordenar para parecer um fluxo mais limpo."""

    cenario = Cenario(tmp_path)
    mensagem_id = cenario.mensagem()
    cenario.excecao("falha_da_execucao", tentativas=3, impacto="Impacto da execução.")
    cenario.excecao(
        "falha_da_mensagem", tentativas=1, impacto="Impacto da mensagem.", mensagem_id=mensagem_id
    )

    linha_do_tempo = cenario.servico.montar(cenario.execucao_id)

    assert linha_do_tempo is not None
    marcos_excecao = [m for m in linha_do_tempo.marcos if m.tipo == TIPO_EXCECAO]
    assert len(marcos_excecao) == 2
    excecao_mensagem = next(m for m in marcos_excecao if m.mensagem_id == mensagem_id)
    assert excecao_mensagem.resultado == "falha_da_mensagem"
    excecao_execucao = next(m for m in marcos_excecao if m.mensagem_id is None)
    assert excecao_execucao.resultado == "falha_da_execucao"


def test_execucao_inexistente_devolve_none(tmp_path: Path) -> None:
    """`montar` de uma execução inexistente devolve `None`, não erro técnico."""

    cenario = Cenario(tmp_path)

    assert cenario.servico.montar(uuid4()) is None
