"""Testes do caso de uso da explicação acessível de um comunicado (EXPLICACAO-01..05).

Os repositórios são os reais, sobre um banco temporário migrado — mesma escolha de
`test_detalhe_resultado.py`/`test_visualizacao_comunicado.py`, já que esta história reusa por
composição a mesma junção de dados de 4.2.
"""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_criticas import (
    RepositorioAvaliacoesCriticas,
)
from central_preventiva.adaptadores.persistencia.repositorio_contextos_agente import (
    RepositorioContextosAgente,
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
from central_preventiva.adaptadores.persistencia.repositorio_meteorologia import (
    RepositorioEventosMeteorologicos,
)
from central_preventiva.adaptadores.persistencia.serializacao_criterios import (
    serializar_criterios,
)
from central_preventiva.aplicacao.detalhe_resultado import (
    PortasDetalheResultado,
    ServicoDetalheResultado,
)
from central_preventiva.aplicacao.explicacao_comunicado import (
    OrigemInformacao,
    OrigemRegeneracao,
    PortasExplicacaoComunicado,
    ServicoExplicacaoComunicado,
    StatusProcedencia,
)
from central_preventiva.dominio.avaliacao_critica import CategoriaCritica, MotivoCritica
from central_preventiva.dominio.avaliador_elegibilidade import (
    OPERANDO_AREA_AFETADA,
    OPERANDO_COBERTURA_EXIGIDA,
)
from central_preventiva.dominio.avaliador_risco import Criterio
from central_preventiva.dominio.decisao_humana import ResultadoDecisaoHumana
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)
from central_preventiva.dominio.montador_contexto_agente import ContextoAgente
from central_preventiva.dominio.validador_saida_canal import (
    Canal,
    LimitesCanal,
    SaidaCanal,
    ValidadorSaidaCanal,
)

EXECUCAO_ID = UUID("11111111-1111-1111-1111-111111111111")
EXECUCAO_RETENTATIVA_ID = UUID("66666666-6666-6666-6666-666666666666")
EVENTO_ID = UUID("22222222-2222-2222-2222-222222222222")
REGRA_ID = UUID("33333333-3333-3333-3333-333333333333")
REGRA_VERSAO = 4
CARLOS_ID = UUID("44444444-4444-4444-4444-444444444444")
OUTRO_SEGURADO_ID = UUID("55555555-5555-5555-5555-555555555555")
MODELO = "gpt-4o-mini"
VERSAO_PROMPT = "v1"

LIMITES = LimitesCanal(whatsapp=1024, sms=160, assunto_email=78, corpo_email=2000)

EVENTO = EventoMeteorologico(
    id=EVENTO_ID,
    tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
    area="9990001",
    periodo_inicio=datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
    periodo_fim=datetime(2026, 9, 4, 18, 0, tzinfo=UTC),
    intensidade=62.5,
    proveniencia=ProvenienciaEvento.REAL_INMET,
    instante_observado=datetime(2026, 9, 4, 18, 0, tzinfo=UTC),
)

CRITERIOS = (
    Criterio(OPERANDO_AREA_AFETADA, "9990001", True, "Área corresponde."),
    Criterio(OPERANDO_COBERTURA_EXIGIDA, "alagamento", True, "Possui cobertura."),
)

MOTIVO_TOM = MotivoCritica(CategoriaCritica.TOM, "O texto usa tom alarmista.")

CONTEXTO_MINIMO = ContextoAgente(
    evento="chuva_intensa",
    localizacao_aproximada="9990001",
    coberturas_relevantes=("alagamento",),
    canal="sms",
    orientacoes_seguranca=("Evite áreas alagadas.",),
)
CATEGORIAS_USADAS = ("evento", "localizacao_aproximada", "coberturas_relevantes", "canal")
CATEGORIAS_NAO_USADAS = ("documentos", "dados_financeiros", "dados_de_pagamento")


class Cenario:
    """Reúne o caso de uso real e os repositórios reais sobre um banco temporário migrado."""

    def __init__(self, tmp_path: Path) -> None:
        """Migra o banco, semeia evento/regra/execução e compõe o serviço real."""

        self.caminho = tmp_path / "central_preventiva.duckdb"
        ExecutorMigracoes(self.caminho).aplicar_pendentes()
        self.mensagens = RepositorioMensagens(self.caminho)
        self.avaliacoes = RepositorioAvaliacoesCriticas(self.caminho)
        self.decisoes = RepositorioDecisoesHumanas(self.caminho)
        self.entregas = RepositorioEntregasSimuladas(self.caminho)
        self.elegibilidades = RepositorioElegibilidades(self.caminho)
        self.eventos = RepositorioEventosMeteorologicos(self.caminho)
        self.excecoes = RepositorioExcecoesOperacionais(self.caminho)
        self.contextos = RepositorioContextosAgente(self.caminho)
        self.execucoes = RepositorioExecucaoPreventiva(self.caminho)
        self.eventos.salvar(EVENTO)
        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(
                "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
                "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
                "VALUES (?, 'chuva_intensa', 50.0, '9990001', 'residencial', 'alagamento', "
                "6, 'sms', ?, 'ativa')",
                [REGRA_ID, REGRA_VERSAO],
            )
            conexao.execute(
                "INSERT INTO execucao_preventiva (id, estado, versao) "
                "VALUES (?, 'concluida', 1)",
                [EXECUCAO_ID],
            )
            conexao.execute(
                "INSERT INTO execucao_preventiva "
                "(id, estado, versao, execucao_origem_id) VALUES (?, 'concluida', 1, ?)",
                [EXECUCAO_RETENTATIVA_ID, EXECUCAO_ID],
            )
        detalhe = ServicoDetalheResultado(
            PortasDetalheResultado(
                mensagens=self.mensagens,
                avaliacoes=self.avaliacoes,
                decisoes=self.decisoes,
                entregas=self.entregas,
                elegibilidades=self.elegibilidades,
                eventos=self.eventos,
                excecoes=self.excecoes,
                validador=ValidadorSaidaCanal(LIMITES),
            )
        )
        self.servico = ServicoExplicacaoComunicado(
            PortasExplicacaoComunicado(
                entregas=self.entregas,
                mensagens=self.mensagens,
                elegibilidades=self.elegibilidades,
                detalhe=detalhe,
                contextos=self.contextos,
                execucoes=self.execucoes,
            )
        )

    def elegibilidade(
        self, segurado_id: UUID = CARLOS_ID, execucao_id: UUID = EXECUCAO_ID
    ) -> UUID:
        """Insere um item do público elegível, no formato que 2.5 grava."""

        id_registro = uuid4()
        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(
                "INSERT INTO elegibilidades_historicas "
                "(id, execucao_id, evento_id, regra_id, segurado_id, "
                "apolice_id, elegivel, criterios, canal, nome_segurado, justificativa) "
                "VALUES (?, ?, ?, ?, ?, ?, true, ?, 'sms', 'Carlos Teste', "
                "'Atende integralmente aos critérios da regra ativa.')",
                [
                    id_registro,
                    execucao_id,
                    EVENTO_ID,
                    REGRA_ID,
                    segurado_id,
                    uuid4(),
                    serializar_criterios(CRITERIOS),
                ],
            )
        return id_registro

    def mensagem_aprovada_e_simulada(
        self, segurado_id: UUID = CARLOS_ID, execucao_id: UUID = EXECUCAO_ID
    ) -> UUID:
        """Cria uma mensagem com uma tentativa aprovada, criticada e já simulada."""

        elegibilidade_id = self.elegibilidade(segurado_id=segurado_id, execucao_id=execucao_id)
        self.contextos.salvar(
            execucao_id, elegibilidade_id, CONTEXTO_MINIMO, CATEGORIAS_USADAS, CATEGORIAS_NAO_USADAS
        )
        mensagem_id = self.mensagens.criar(execucao_id, elegibilidade_id, Canal.SMS)
        versao_id = self.mensagens.salvar_versao(
            mensagem_id, 1, SaidaCanal(corpo="Chuva forte hoje."), 100.0, MODELO, VERSAO_PROMPT,
            5, 5, True, None,
        )
        self.avaliacoes.salvar(versao_id, True, (), MODELO, 80.0)
        self.decisoes.salvar(
            mensagem_id, versao_id, "administrador", ResultadoDecisaoHumana.APROVAR, None
        )
        self.mensagens.transicionar(mensagem_id, 1, EstadoMensagem.APROVADA)
        self.mensagens.transicionar(mensagem_id, 2, EstadoMensagem.SIMULADA_ENTREGUE)
        self.entregas.criar_lote(
            execucao_id,
            [MensagemAprovada(mensagem_id, Canal.SMS, SaidaCanal(corpo="Chuva forte hoje."))],
        )
        entregas_da_execucao = self.entregas.listar_por_execucao(execucao_id)
        entrega_da_mensagem = next(
            entrega for entrega in entregas_da_execucao if entrega.mensagem_id == mensagem_id
        )
        return entrega_da_mensagem.id


def test_explicacao_separa_evento_regra_deterministicos_de_redator_critico_e_aprovacao(
    tmp_path: Path,
) -> None:
    """EXPLICACAO-01/02: evento/regra rotulados DETERMINISTICA, redator/crítico/decisão
    humana rotulados AGENTE, com a decisão crítica e a aprovação humana visíveis."""

    cenario = Cenario(tmp_path)
    entrega_id = cenario.mensagem_aprovada_e_simulada()

    explicacao = cenario.servico.obter(CARLOS_ID, entrega_id)

    assert explicacao is not None
    assert explicacao.evento_e_regra.origem is OrigemInformacao.DETERMINISTICA
    assert explicacao.evento_e_regra.evento is not None
    assert explicacao.evento_e_regra.evento.id == EVENTO_ID
    assert explicacao.evento_e_regra.regra_id == REGRA_ID
    assert explicacao.evento_e_regra.regra_versao == REGRA_VERSAO
    assert explicacao.agente.origem is OrigemInformacao.AGENTE
    assert explicacao.agente.status is StatusProcedencia.COMPLETA
    assert len(explicacao.agente.tentativas) == 1
    tentativa = explicacao.agente.tentativas[0]
    assert tentativa.origem_regeneracao is OrigemRegeneracao.PRIMEIRA_TENTATIVA
    assert tentativa.modelo_redator == MODELO
    assert tentativa.avaliacao_critica is not None
    assert tentativa.avaliacao_critica.avaliacao.aprovada is True
    assert len(tentativa.decisoes_humanas) == 1
    assert tentativa.decisoes_humanas[0].resultado is ResultadoDecisaoHumana.APROVAR


def test_duas_tentativas_reprovadas_por_critico_mostram_regeneracao_automatica(
    tmp_path: Path,
) -> None:
    """EXPLICACAO-02, Edge Case: a regeneração automática do ciclo crítico (3.4, sem decisão
    humana de regenerar) é distinta da regeneração solicitada por decisão humana (3.5)."""

    cenario = Cenario(tmp_path)
    elegibilidade_id = cenario.elegibilidade()
    mensagem_id = cenario.mensagens.criar(EXECUCAO_ID, elegibilidade_id, Canal.SMS)

    versao_1 = cenario.mensagens.salvar_versao(
        mensagem_id, 1, SaidaCanal(corpo="Tentativa 1"), 100.0, MODELO, VERSAO_PROMPT, 5, 5,
        True, None,
    )
    cenario.avaliacoes.salvar(versao_1, False, (MOTIVO_TOM,), MODELO, 80.0)
    cenario.mensagens.incrementar_tentativa(mensagem_id, 1)

    versao_2 = cenario.mensagens.salvar_versao(
        mensagem_id, 2, SaidaCanal(corpo="Tentativa 2"), 100.0, MODELO, VERSAO_PROMPT, 5, 5,
        True, None,
    )
    cenario.avaliacoes.salvar(versao_2, False, (MOTIVO_TOM,), MODELO, 80.0)
    cenario.decisoes.salvar(
        mensagem_id, versao_2, "administrador", ResultadoDecisaoHumana.REGENERAR,
        "Ainda alarmista.",
    )
    cenario.mensagens.incrementar_tentativa(mensagem_id, 2)

    versao_3 = cenario.mensagens.salvar_versao(
        mensagem_id, 3, SaidaCanal(corpo="Tentativa 3"), 100.0, MODELO, VERSAO_PROMPT, 5, 5,
        True, None,
    )
    cenario.avaliacoes.salvar(versao_3, True, (), MODELO, 80.0)

    entregas_falsas_id = uuid4()
    # A entrega simulada só existe depois de simulada_entregue; aqui inserimos diretamente
    # para consultar a explicação sem levar a mensagem ao fim do ciclo completo de 3.6.
    with abrir_conexao(cenario.caminho) as conexao:
        conexao.execute(
            "INSERT INTO entregas_simuladas (id, execucao_id, mensagem_id, canal, "
            "apresentacao) VALUES (?, ?, ?, 'sms', ?)",
            [
                entregas_falsas_id,
                EXECUCAO_ID,
                mensagem_id,
                '{"corpo": "Tentativa 3"}',
            ],
        )

    explicacao = cenario.servico.obter(CARLOS_ID, entregas_falsas_id)

    assert explicacao is not None
    assert [t.numero_tentativa for t in explicacao.agente.tentativas] == [1, 2, 3]
    origens = [t.origem_regeneracao for t in explicacao.agente.tentativas]
    assert origens == [
        OrigemRegeneracao.PRIMEIRA_TENTATIVA,
        OrigemRegeneracao.AUTOMATICA,
        OrigemRegeneracao.HUMANA,
    ]


def test_categorias_usadas_e_nao_usadas_do_contexto_minimo_aparecem_sem_dado_sensivel(
    tmp_path: Path,
) -> None:
    """EXPLICACAO-03: categorias usadas/não usadas aparecem, sem documentos/dados
    financeiros/pagamentos/credenciais nem o prompt completo."""

    cenario = Cenario(tmp_path)
    entrega_id = cenario.mensagem_aprovada_e_simulada()

    explicacao = cenario.servico.obter(CARLOS_ID, entrega_id)

    assert explicacao is not None
    assert explicacao.contexto is not None
    assert explicacao.contexto.categorias_usadas == CATEGORIAS_USADAS
    assert explicacao.contexto.categorias_nao_usadas == CATEGORIAS_NAO_USADAS
    assert "documentos" not in explicacao.contexto.categorias_usadas
    assert "dados_financeiros" not in explicacao.contexto.categorias_usadas


def test_previa_da_mensagem_final_e_copia_exata_da_entrega_simulada(tmp_path: Path) -> None:
    """EXPLICACAO-04: a prévia corresponde exatamente à versão aprovada e simulada."""

    cenario = Cenario(tmp_path)
    entrega_id = cenario.mensagem_aprovada_e_simulada()

    explicacao = cenario.servico.obter(CARLOS_ID, entrega_id)

    assert explicacao is not None
    assert explicacao.apresentacao_simulada is not None
    assert explicacao.apresentacao_simulada.corpo == "Chuva forte hoje."
    assert explicacao.apresentacao_simulada.rotulo == "simulada"


def test_avaliacao_critica_ausente_de_tentativa_intermediaria_mostra_procedencia_parcial(
    tmp_path: Path,
) -> None:
    """EXPLICACAO-05: lacuna de dado (avaliação crítica intermediária ausente) mostra
    `Procedência parcial`, sem preencher com inferência."""

    cenario = Cenario(tmp_path)
    elegibilidade_id = cenario.elegibilidade()
    mensagem_id = cenario.mensagens.criar(EXECUCAO_ID, elegibilidade_id, Canal.SMS)
    cenario.mensagens.salvar_versao(
        mensagem_id, 1, SaidaCanal(corpo="Tentativa 1"), 100.0, MODELO, VERSAO_PROMPT, 5, 5,
        True, None,
    )
    # Nenhuma avaliação crítica salva para a versão 1 (dado de teste simulando lacuna).
    cenario.mensagens.incrementar_tentativa(mensagem_id, 1)
    versao_2 = cenario.mensagens.salvar_versao(
        mensagem_id, 2, SaidaCanal(corpo="Tentativa 2"), 100.0, MODELO, VERSAO_PROMPT, 5, 5,
        True, None,
    )
    cenario.avaliacoes.salvar(versao_2, True, (), MODELO, 80.0)

    entrega_id = uuid4()
    with abrir_conexao(cenario.caminho) as conexao:
        conexao.execute(
            "INSERT INTO entregas_simuladas (id, execucao_id, mensagem_id, canal, "
            "apresentacao) VALUES (?, ?, ?, 'sms', ?)",
            [
                entrega_id,
                EXECUCAO_ID,
                mensagem_id,
                '{"corpo": "Tentativa 2"}',
            ],
        )

    explicacao = cenario.servico.obter(CARLOS_ID, entrega_id)

    assert explicacao is not None
    assert explicacao.agente.status is StatusProcedencia.PARCIAL
    assert explicacao.agente.tentativas[0].avaliacao_critica is None
    assert explicacao.agente.causa_excecao is None


def test_mensagem_em_falhou_integracao_ia_mostra_excecao_sem_secao_de_critica_vazia(
    tmp_path: Path,
) -> None:
    """Edge Case: mensagem que nunca chegou a `criticando` mostra `Exceção`, com a causa
    sanitizada — não uma seção de crítica vazia parecendo incompleta por engano."""

    cenario = Cenario(tmp_path)
    elegibilidade_id = cenario.elegibilidade()
    mensagem_id = cenario.mensagens.criar(EXECUCAO_ID, elegibilidade_id, Canal.SMS)
    cenario.mensagens.salvar_versao(
        mensagem_id, 1, SaidaCanal(corpo=""), 100.0, MODELO, VERSAO_PROMPT, None, None,
        False, "falha_integracao_openai",
    )
    cenario.excecoes.registrar(
        EXECUCAO_ID,
        "falha_integracao_ia",
        3,
        "A geração falhou por indisponibilidade do provedor de IA.",
        mensagem_id=mensagem_id,
    )
    cenario.mensagens.transicionar(mensagem_id, 1, EstadoMensagem.FALHOU_INTEGRACAO_IA)

    entrega_id = uuid4()
    with abrir_conexao(cenario.caminho) as conexao:
        conexao.execute(
            "INSERT INTO entregas_simuladas (id, execucao_id, mensagem_id, canal, "
            "apresentacao) VALUES (?, ?, ?, 'sms', ?)",
            [
                entrega_id,
                EXECUCAO_ID,
                mensagem_id,
                '{"corpo": ""}',
            ],
        )

    explicacao = cenario.servico.obter(CARLOS_ID, entrega_id)

    assert explicacao is not None
    assert explicacao.agente.status is StatusProcedencia.EXCECAO
    assert explicacao.agente.causa_excecao == "falha_integracao_ia"


def test_execucao_correlacionada_e_indicada_sem_misturar_com_a_origem(tmp_path: Path) -> None:
    """Edge Case: comunicado de uma execução correlacionada (retentativa) indica isso,
    sem misturar proveniência da execução de origem com a da retentativa."""

    cenario = Cenario(tmp_path)
    entrega_da_origem = cenario.mensagem_aprovada_e_simulada()
    entrega_da_retentativa = cenario.mensagem_aprovada_e_simulada(
        execucao_id=EXECUCAO_RETENTATIVA_ID
    )

    explicacao_origem = cenario.servico.obter(CARLOS_ID, entrega_da_origem)
    explicacao_retentativa = cenario.servico.obter(CARLOS_ID, entrega_da_retentativa)

    assert explicacao_origem is not None
    assert explicacao_origem.execucao_origem_id is None
    assert explicacao_retentativa is not None
    assert explicacao_retentativa.execucao_origem_id == EXECUCAO_ID
    assert explicacao_retentativa.execucao_id == EXECUCAO_RETENTATIVA_ID


def test_obter_de_comunicado_de_outro_segurado_devolve_none(tmp_path: Path) -> None:
    """`obter` de uma entrega que pertence a outro segurado devolve `None` (AD-011)."""

    cenario = Cenario(tmp_path)
    entrega_id = cenario.mensagem_aprovada_e_simulada(segurado_id=OUTRO_SEGURADO_ID)

    assert cenario.servico.obter(CARLOS_ID, entrega_id) is None
    assert cenario.servico.obter(CARLOS_ID, uuid4()) is None
