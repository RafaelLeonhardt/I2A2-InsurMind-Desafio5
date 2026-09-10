"""Testes do repositório de entregas simuladas (SIMUL-05, SIMUL-06, SIMUL-07).

O banco é o real, temporário e migrado: a `UNIQUE (mensagem_id)` e a atomicidade dentro da
transação do chamador são garantias do próprio DuckDB — testá-las com dublê provaria pouco.
"""

from dataclasses import fields
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    ROTULO_SIMULADA,
    EntregaSimuladaJaExiste,
    MensagemAprovada,
    RepositorioEntregasSimuladas,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import RepositorioMensagens
from central_preventiva.adaptadores.persistencia.serializacao_criterios import (
    serializar_criterios,
)
from central_preventiva.adaptadores.persistencia.transacao import TransacaoDuckDB
from central_preventiva.dominio.avaliador_elegibilidade import (
    OPERANDO_AREA_AFETADA,
    OPERANDO_COBERTURA_EXIGIDA,
)
from central_preventiva.dominio.avaliador_risco import Criterio
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

EXECUCAO_ID = UUID("11111111-1111-1111-1111-111111111111")
OUTRA_EXECUCAO_ID = UUID("99999999-9999-9999-9999-999999999999")
CARLOS_ID = UUID("44444444-4444-4444-4444-444444444444")
OUTRO_SEGURADO_ID = UUID("55555555-5555-5555-5555-555555555555")
CORPO_SMS = "Chuva forte hoje na sua região. Evite áreas alagadas."
CORPO_EMAIL = "Prezada, previsão de chuva intensa na sua região nas próximas horas."
ASSUNTO_EMAIL = "Aviso preventivo da sua seguradora"
CORPO_LONGO_WHATSAPP = (
    "Atenção: previsão de chuva intensa na sua região nas próximas seis horas, com risco "
    "de alagamento em vias e áreas baixas. Evite deslocamentos desnecessários."
)
CRITERIOS = (
    Criterio(OPERANDO_AREA_AFETADA, "9990001", True, "Área corresponde."),
    Criterio(OPERANDO_COBERTURA_EXIGIDA, "alagamento", True, "Possui cobertura."),
)


class CenarioSegurado:
    """Semeia regra/execução/elegibilidade/mensagem reais, para exercitar a junção de
    `listar_por_segurado` com as tabelas de outras histórias (2.4, 2.5, 3.2)."""

    def __init__(self, tmp_path: Path) -> None:
        """Migra o banco e monta os repositórios reais sobre ele."""

        self.caminho = preparar(tmp_path)
        self.mensagens = RepositorioMensagens(self.caminho)
        self.entregas = RepositorioEntregasSimuladas(self.caminho)
        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(
                "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
                "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
                "VALUES (?, 'chuva_intensa', 50.0, '9990001', 'residencial', 'alagamento', "
                "6, 'sms', 1, 'ativa')",
                [uuid4()],
            )
            conexao.execute(
                "INSERT INTO execucao_preventiva (id, estado, versao) "
                "VALUES (?, 'concluida', 1)",
                [EXECUCAO_ID],
            )

    def entrega(
        self,
        canal: Canal,
        conteudo: SaidaCanal,
        segurado_id: UUID = CARLOS_ID,
        estado: EstadoMensagem = EstadoMensagem.SIMULADA_ENTREGUE,
    ) -> UUID:
        """Semeia elegibilidade+mensagem+entrega simulada para o segurado informado."""

        elegibilidade_id = uuid4()
        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(
                "INSERT INTO elegibilidades_historicas "
                "(id, execucao_id, evento_id, regra_id, segurado_id, "
                "apolice_id, elegivel, criterios, canal, nome_segurado, justificativa) "
                "VALUES (?, ?, ?, ?, ?, ?, true, ?, ?, 'Carlos Teste', "
                "'Atende integralmente aos critérios da regra ativa.')",
                [
                    elegibilidade_id,
                    EXECUCAO_ID,
                    uuid4(),
                    uuid4(),
                    segurado_id,
                    uuid4(),
                    serializar_criterios(CRITERIOS),
                    canal.value,
                ],
            )
        mensagem_id = self.mensagens.criar(EXECUCAO_ID, elegibilidade_id, canal)
        [entrega_id] = self.entregas.criar_lote(
            EXECUCAO_ID, [MensagemAprovada(mensagem_id, canal, conteudo)]
        )
        if estado is not EstadoMensagem.GERANDO:
            self.mensagens.transicionar(mensagem_id, 1, estado)
        return entrega_id


def preparar(tmp_path: Path) -> Path:
    """Aplica as migrações versionadas em um banco temporário do teste."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def contar(caminho: Path) -> int:
    """Conta todas as entregas simuladas persistidas no banco do teste."""

    with abrir_conexao(caminho) as conexao:
        linha = conexao.execute("SELECT count(*) FROM entregas_simuladas").fetchone()
    assert linha is not None
    return int(linha[0])


def test_criar_lote_cria_uma_entrega_por_mensagem_com_o_conteudo_aprovado(
    tmp_path: Path,
) -> None:
    """SIMUL-05: uma entrega por mensagem e canal, com a apresentação copiada do conteúdo já
    aprovado — corpo no SMS, assunto e corpo no e-mail, sem transformação."""

    caminho = preparar(tmp_path)
    repositorio = RepositorioEntregasSimuladas(caminho)
    mensagem_sms = uuid4()
    mensagem_email = uuid4()

    criadas = repositorio.criar_lote(
        EXECUCAO_ID,
        [
            MensagemAprovada(mensagem_sms, Canal.SMS, SaidaCanal(corpo=CORPO_SMS)),
            MensagemAprovada(
                mensagem_email,
                Canal.EMAIL,
                SaidaCanal(corpo=CORPO_EMAIL, assunto=ASSUNTO_EMAIL),
            ),
        ],
    )

    entregas = repositorio.listar_por_execucao(EXECUCAO_ID)
    assert len(criadas) == 2
    assert [entrega.id for entrega in entregas] == criadas
    assert [entrega.mensagem_id for entrega in entregas] == [mensagem_sms, mensagem_email]
    assert [entrega.canal for entrega in entregas] == [Canal.SMS, Canal.EMAIL]
    assert [entrega.execucao_id for entrega in entregas] == [EXECUCAO_ID, EXECUCAO_ID]
    assert entregas[0].apresentacao.corpo == CORPO_SMS
    assert entregas[0].apresentacao.assunto is None
    assert entregas[1].apresentacao.corpo == CORPO_EMAIL
    assert entregas[1].apresentacao.assunto == ASSUNTO_EMAIL


def test_toda_entrega_e_rotulada_como_simulada(tmp_path: Path) -> None:
    """SIMUL-06: a entrega é rotulada como simulada e não carrega confirmação nem falha de
    provedor externo — não existe campo onde inventá-las."""

    caminho = preparar(tmp_path)
    repositorio = RepositorioEntregasSimuladas(caminho)
    repositorio.criar_lote(
        EXECUCAO_ID,
        [MensagemAprovada(uuid4(), Canal.WHATSAPP, SaidaCanal(corpo=CORPO_SMS))],
    )

    entrega = repositorio.listar_por_execucao(EXECUCAO_ID)[0]

    assert entrega.apresentacao.rotulo == ROTULO_SIMULADA == "simulada"
    assert {campo.name for campo in fields(entrega.apresentacao)} == {
        "canal",
        "corpo",
        "assunto",
        "rotulo",
    }


def test_criar_lote_participa_da_transacao_do_chamador(tmp_path: Path) -> None:
    """SIMUL-05: as entregas entram na transação já aberta pelo chamador — uma falha depois
    da inserção desfaz o lote inteiro, sem entrega parcial."""

    caminho = preparar(tmp_path)
    repositorio = RepositorioEntregasSimuladas(caminho)
    transacao = TransacaoDuckDB(caminho)

    def inserir_e_falhar(conexao: object) -> None:
        repositorio.criar_lote(
            EXECUCAO_ID,
            [
                MensagemAprovada(uuid4(), Canal.SMS, SaidaCanal(corpo=CORPO_SMS)),
                MensagemAprovada(uuid4(), Canal.SMS, SaidaCanal(corpo=CORPO_SMS)),
            ],
            conexao,  # pyright: ignore[reportArgumentType]
        )
        raise RuntimeError("falha local durante a simulação")

    with pytest.raises(RuntimeError):
        transacao.executar(inserir_e_falhar)

    assert contar(caminho) == 0
    assert repositorio.listar_por_execucao(EXECUCAO_ID) == []


def test_criar_lote_commitado_na_transacao_do_chamador_persiste_o_lote(
    tmp_path: Path,
) -> None:
    """A contraprova do teste anterior: sem falha, a mesma transação confirma as entregas."""

    caminho = preparar(tmp_path)
    repositorio = RepositorioEntregasSimuladas(caminho)

    TransacaoDuckDB(caminho).executar(
        lambda conexao: repositorio.criar_lote(
            EXECUCAO_ID,
            [MensagemAprovada(uuid4(), Canal.SMS, SaidaCanal(corpo=CORPO_SMS))],
            conexao,
        )
    )

    assert contar(caminho) == 1


def test_listar_por_execucao_nao_mistura_entregas_de_outra_execucao(
    tmp_path: Path,
) -> None:
    """Cada simulação é independente da outra (terceiro Edge Case da spec)."""

    caminho = preparar(tmp_path)
    repositorio = RepositorioEntregasSimuladas(caminho)
    mensagem_da_execucao = uuid4()
    repositorio.criar_lote(
        EXECUCAO_ID,
        [MensagemAprovada(mensagem_da_execucao, Canal.SMS, SaidaCanal(corpo=CORPO_SMS))],
    )
    repositorio.criar_lote(
        OUTRA_EXECUCAO_ID,
        [MensagemAprovada(uuid4(), Canal.SMS, SaidaCanal(corpo=CORPO_SMS))],
    )

    entregas = repositorio.listar_por_execucao(EXECUCAO_ID)

    assert [entrega.mensagem_id for entrega in entregas] == [mensagem_da_execucao]
    assert contar(caminho) == 2


def test_segunda_entrega_da_mesma_mensagem_e_recusada_sem_duplicar(
    tmp_path: Path,
) -> None:
    """SIMUL-07: a `UNIQUE (mensagem_id)` (AD-010) impede uma segunda entrega da mesma
    mensagem, e a recusa chega ao chamador como erro próprio, não como falha genérica."""

    caminho = preparar(tmp_path)
    repositorio = RepositorioEntregasSimuladas(caminho)
    mensagem_id = uuid4()
    repositorio.criar_lote(
        EXECUCAO_ID, [MensagemAprovada(mensagem_id, Canal.SMS, SaidaCanal(corpo=CORPO_SMS))]
    )

    with pytest.raises(EntregaSimuladaJaExiste) as capturado:
        repositorio.criar_lote(
            EXECUCAO_ID,
            [MensagemAprovada(mensagem_id, Canal.SMS, SaidaCanal(corpo=CORPO_SMS))],
        )

    assert capturado.value.execucao_id == EXECUCAO_ID
    assert contar(caminho) == 1


def test_obter_por_id_le_a_entrega_isoladamente(tmp_path: Path) -> None:
    """4.3: o comunicado se resolve por `entrega_simulada_id`, sem conhecer a execução
    de antemão."""

    caminho = preparar(tmp_path)
    repositorio = RepositorioEntregasSimuladas(caminho)
    mensagem_id = uuid4()
    [entrega_id] = repositorio.criar_lote(
        EXECUCAO_ID, [MensagemAprovada(mensagem_id, Canal.SMS, SaidaCanal(corpo=CORPO_SMS))]
    )

    entrega = repositorio.obter_por_id(entrega_id)

    assert entrega is not None
    assert entrega.id == entrega_id
    assert entrega.mensagem_id == mensagem_id
    assert entrega.execucao_id == EXECUCAO_ID


def test_obter_por_id_devolve_none_para_identificador_inexistente(tmp_path: Path) -> None:
    """`obter_por_id` nunca inventa uma entrega — devolve `None` para um id desconhecido."""

    caminho = preparar(tmp_path)
    repositorio = RepositorioEntregasSimuladas(caminho)

    assert repositorio.obter_por_id(uuid4()) is None


def test_listar_por_segurado_isola_por_segurado_e_deriva_assunto_ou_resumo_por_canal(
    tmp_path: Path,
) -> None:
    """COMUNICADOS-01: só entregas do segurado informado, e-mail com assunto real,
    WhatsApp/SMS com resumo truncado do corpo quando ele excede o tamanho fixo."""

    cenario = CenarioSegurado(tmp_path)
    entrega_email = cenario.entrega(
        Canal.EMAIL, SaidaCanal(corpo=CORPO_EMAIL, assunto=ASSUNTO_EMAIL)
    )
    entrega_whatsapp = cenario.entrega(Canal.WHATSAPP, SaidaCanal(corpo=CORPO_LONGO_WHATSAPP))
    cenario.entrega(Canal.SMS, SaidaCanal(corpo=CORPO_SMS), segurado_id=OUTRO_SEGURADO_ID)

    entregas = cenario.entregas.listar_por_segurado(CARLOS_ID)

    assert [entrega.id for entrega in entregas] == [entrega_email, entrega_whatsapp]
    assert entregas[0].assunto_ou_resumo == ASSUNTO_EMAIL
    assert entregas[1].assunto_ou_resumo == CORPO_LONGO_WHATSAPP[:60].rstrip() + "…"
    assert len(entregas[1].assunto_ou_resumo) <= 61


def test_listar_por_segurado_nao_trunca_corpo_curto_do_sms(tmp_path: Path) -> None:
    """Um corpo dentro do limite não ganha reticências nem é cortado."""

    cenario = CenarioSegurado(tmp_path)
    corpo_curto = "Chuva leve hoje."
    cenario.entrega(Canal.SMS, SaidaCanal(corpo=corpo_curto))

    [entrega] = cenario.entregas.listar_por_segurado(CARLOS_ID)

    assert entrega.assunto_ou_resumo == corpo_curto


def test_listar_por_segurado_sem_comunicados_devolve_lista_vazia(tmp_path: Path) -> None:
    """Segurado sem nenhuma entrega simulada recebe lista vazia, não erro."""

    cenario = CenarioSegurado(tmp_path)

    assert cenario.entregas.listar_por_segurado(CARLOS_ID) == []


def test_listar_por_segurado_exclui_mensagem_ainda_nao_simulada_entregue(
    tmp_path: Path,
) -> None:
    """Edge Case da spec.md: uma execução ainda em andamento (mensagem não
    `simulada_entregue`) não aparece na lista de comunicados."""

    cenario = CenarioSegurado(tmp_path)
    cenario.entrega(
        Canal.SMS, SaidaCanal(corpo=CORPO_SMS), estado=EstadoMensagem.REJEITADA
    )

    assert cenario.entregas.listar_por_segurado(CARLOS_ID) == []


def test_obter_id_mais_recente_por_elegibilidade_devolve_a_entrega_simulada_entregue(
    tmp_path: Path,
) -> None:
    """6.8 (ABRIREXP-01): elegibilidade com mensagem `simulada_entregue` devolve o id da
    entrega associada."""

    cenario = CenarioSegurado(tmp_path)
    elegibilidade_id = uuid4()
    _semear_mensagem_e_entrega(cenario, elegibilidade_id, Canal.SMS)
    entrega_id = cenario.entregas.listar_por_execucao(EXECUCAO_ID)[0].id

    resultado = cenario.entregas.obter_id_mais_recente_por_elegibilidade(elegibilidade_id)

    assert resultado == entrega_id


def test_obter_id_mais_recente_por_elegibilidade_sem_mensagem_devolve_none(
    tmp_path: Path,
) -> None:
    """6.8 (ABRIREXP-03): elegibilidade sem nenhuma mensagem não tem o que abrir — `None`,
    não um erro."""

    cenario = CenarioSegurado(tmp_path)

    assert cenario.entregas.obter_id_mais_recente_por_elegibilidade(uuid4()) is None


def test_obter_id_mais_recente_por_elegibilidade_mensagem_nao_entregue_devolve_none(
    tmp_path: Path,
) -> None:
    """6.8 (ABRIREXP-03): mensagem existe mas ainda não chegou a `simulada_entregue` (ex.:
    ainda `gerando`) — o alerta é "ainda_nao_simulado", o botão não deve aparecer."""

    cenario = CenarioSegurado(tmp_path)
    elegibilidade_id = uuid4()
    mensagem_id = cenario.mensagens.criar(EXECUCAO_ID, elegibilidade_id, Canal.SMS)
    cenario.entregas.criar_lote(
        EXECUCAO_ID, [MensagemAprovada(mensagem_id, Canal.SMS, SaidaCanal(corpo=CORPO_SMS))]
    )

    assert cenario.entregas.obter_id_mais_recente_por_elegibilidade(elegibilidade_id) is None


def test_obter_id_mais_recente_por_elegibilidade_com_dois_canais_devolve_o_mais_recente(
    tmp_path: Path,
) -> None:
    """6.8 (Tech Decision do design.md): uma elegibilidade com mensagens em dois canais
    (um por par elegibilidade+canal, migração `0010`) devolve a entrega mais recente."""

    cenario = CenarioSegurado(tmp_path)
    elegibilidade_id = uuid4()
    _semear_mensagem_e_entrega(cenario, elegibilidade_id, Canal.SMS)
    entrega_antiga_id = cenario.entregas.listar_por_execucao(EXECUCAO_ID)[0].id
    with abrir_conexao(cenario.caminho) as conexao:
        conexao.execute(
            "UPDATE entregas_simuladas SET criado_em = TIMESTAMP '2020-01-01 00:00:00' "
            "WHERE id = ?",
            [entrega_antiga_id],
        )
    _semear_mensagem_e_entrega(cenario, elegibilidade_id, Canal.EMAIL)
    entrega_recente_id = next(
        entrega.id
        for entrega in cenario.entregas.listar_por_execucao(EXECUCAO_ID)
        if entrega.id != entrega_antiga_id
    )

    resultado = cenario.entregas.obter_id_mais_recente_por_elegibilidade(elegibilidade_id)

    assert resultado == entrega_recente_id


def _semear_mensagem_e_entrega(
    cenario: CenarioSegurado, elegibilidade_id: UUID, canal: Canal
) -> UUID:
    """Cria mensagem (`simulada_entregue`) + entrega simulada para a elegibilidade dada,
    sem depender de uma linha de `elegibilidades_historicas` (AD-005: sem `REFERENCES`)."""

    mensagem_id = cenario.mensagens.criar(EXECUCAO_ID, elegibilidade_id, canal)
    [entrega_id] = cenario.entregas.criar_lote(
        EXECUCAO_ID, [MensagemAprovada(mensagem_id, canal, SaidaCanal(corpo=CORPO_SMS))]
    )
    cenario.mensagens.transicionar(mensagem_id, 1, EstadoMensagem.SIMULADA_ENTREGUE)
    return entrega_id


def test_listar_por_segurado_ordena_por_data_e_desempata_por_id(tmp_path: Path) -> None:
    """Edge Case da spec.md: duas entregas com a mesma data são ordenadas de forma
    determinística por um critério secundário estável (id), sem posição instável."""

    cenario = CenarioSegurado(tmp_path)
    entrega_alta = cenario.entrega(Canal.SMS, SaidaCanal(corpo="Primeira."))
    entrega_baixa = cenario.entrega(Canal.SMS, SaidaCanal(corpo="Segunda."))
    ids_ordenados = sorted([entrega_alta, entrega_baixa])
    with abrir_conexao(cenario.caminho) as conexao:
        conexao.execute(
            "UPDATE entregas_simuladas SET criado_em = TIMESTAMP '2026-01-01 00:00:00'"
        )

    entregas = cenario.entregas.listar_por_segurado(CARLOS_ID)

    assert [entrega.id for entrega in entregas] == ids_ordenados
