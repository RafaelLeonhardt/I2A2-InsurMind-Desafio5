"""Testes do caso de uso do detalhe individual de um resultado (DETALHE-01..05).

Os repositórios são os reais, sobre um banco temporário migrado: o detalhe é uma junção de
leitura pura sobre schema já garantido por 2.3/2.5/3.2/3.3/3.5/3.6, sem nenhuma escrita
própria a testar com dublê. Mesma escolha de `test_simulacao.py`.
"""

import dataclasses
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_criticas import (
    RepositorioAvaliacoesCriticas,
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
    DetalheResultado,
    PortasDetalheResultado,
    ServicoDetalheResultado,
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
from central_preventiva.dominio.validador_saida_canal import (
    Canal,
    LimitesCanal,
    SaidaCanal,
    ValidadorSaidaCanal,
)

EXECUCAO_ID = UUID("11111111-1111-1111-1111-111111111111")
OUTRA_EXECUCAO_ID = UUID("99999999-9999-9999-9999-999999999999")
EVENTO_ID = UUID("22222222-2222-2222-2222-222222222222")
REGRA_ID = UUID("33333333-3333-3333-3333-333333333333")
REGRA_VERSAO = 2
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
        self.eventos.salvar(EVENTO)
        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(
                "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
                "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
                "VALUES (?, 'chuva_intensa', 50.0, '9990001', 'residencial', 'alagamento', "
                "6, 'sms', ?, 'ativa')",
                [REGRA_ID, REGRA_VERSAO],
            )
            for execucao_id in (EXECUCAO_ID, OUTRA_EXECUCAO_ID):
                conexao.execute(
                    "INSERT INTO execucao_preventiva (id, estado, versao) "
                    "VALUES (?, 'concluida', 1)",
                    [execucao_id],
                )
        self.servico = ServicoDetalheResultado(
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

    def elegibilidade(
        self, canal: str = "sms", nome: str = "Pessoa Teste", execucao_id: UUID = EXECUCAO_ID
    ) -> UUID:
        """Insere um item do público elegível, no formato que 2.5 grava."""

        id_registro = uuid4()
        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(
                "INSERT INTO elegibilidades_historicas "
                "(id, execucao_id, evento_id, regra_id, segurado_id, "
                "apolice_id, elegivel, criterios, canal, nome_segurado, justificativa) "
                "VALUES (?, ?, ?, ?, ?, ?, true, ?, ?, ?, "
                "'Atende integralmente aos critérios da regra ativa.')",
                [
                    id_registro,
                    execucao_id,
                    EVENTO_ID,
                    REGRA_ID,
                    uuid4(),
                    uuid4(),
                    serializar_criterios(CRITERIOS),
                    canal,
                    nome,
                ],
            )
        return id_registro

    def mensagem(
        self, canal: Canal = Canal.SMS, execucao_id: UUID = EXECUCAO_ID, nome: str = "Pessoa Teste"
    ) -> UUID:
        """Cria uma mensagem vinculada a uma elegibilidade recém-semeada."""

        elegibilidade_id = self.elegibilidade(canal=canal.value, nome=nome, execucao_id=execucao_id)
        return self.mensagens.criar(execucao_id, elegibilidade_id, canal)


def test_detalhe_de_email_traz_assunto_corpo_segurado_evento_regra_e_aprovacoes(
    tmp_path: Path,
) -> None:
    """DETALHE-01/02: e-mail aprovado e simulado expõe tudo exigido pelo AC, rotulado."""

    cenario = Cenario(tmp_path)
    mensagem_id = cenario.mensagem(Canal.EMAIL, nome="Marina Teste")
    versao_id = cenario.mensagens.salvar_versao(
        mensagem_id=mensagem_id,
        numero_tentativa=1,
        conteudo=SaidaCanal(corpo="Chuva forte hoje na sua região.", assunto="Alerta preventivo"),
        duracao_ms=742.5,
        modelo=MODELO,
        versao_prompt=VERSAO_PROMPT,
        tokens_entrada=210,
        tokens_saida=64,
        valida=True,
        motivo_invalidez=None,
    )
    cenario.avaliacoes.salvar(
        versao_mensagem_id=versao_id, aprovada=True, motivos=(), modelo=MODELO, duracao_ms=90.0
    )
    cenario.decisoes.salvar(
        mensagem_id, versao_id, "administrador", ResultadoDecisaoHumana.APROVAR, None
    )
    cenario.mensagens.transicionar(mensagem_id, 1, EstadoMensagem.APROVADA)
    cenario.mensagens.transicionar(mensagem_id, 2, EstadoMensagem.SIMULADA_ENTREGUE)
    cenario.entregas.criar_lote(
        EXECUCAO_ID,
        [
            MensagemAprovada(
                mensagem_id,
                Canal.EMAIL,
                SaidaCanal(corpo="Chuva forte hoje na sua região.", assunto="Alerta preventivo"),
            )
        ],
    )

    detalhe = cenario.servico.obter(EXECUCAO_ID, mensagem_id)

    assert detalhe is not None
    assert detalhe.nome_segurado == "Marina Teste"
    assert detalhe.apolice_id is not None
    assert detalhe.canal is Canal.EMAIL
    assert detalhe.estado is EstadoMensagem.SIMULADA_ENTREGUE
    assert isinstance(detalhe.criado_em, datetime)
    assert isinstance(detalhe.atualizado_em, datetime)
    assert detalhe.evento is not None
    assert detalhe.evento.id == EVENTO_ID
    assert detalhe.regra_id == REGRA_ID
    assert detalhe.regra_versao == REGRA_VERSAO
    assert detalhe.apresentacao_simulada is not None
    assert detalhe.apresentacao_simulada.assunto == "Alerta preventivo"
    assert detalhe.apresentacao_simulada.corpo == "Chuva forte hoje na sua região."
    assert detalhe.apresentacao_simulada.rotulo == "simulada"
    assert len(detalhe.versoes) == 1
    assert detalhe.versoes[0].avaliacao_critica is not None
    assert detalhe.versoes[0].avaliacao_critica.avaliacao.aprovada is True
    assert len(detalhe.versoes[0].decisoes_humanas) == 1
    assert detalhe.versoes[0].decisoes_humanas[0].resultado is ResultadoDecisaoHumana.APROVAR


def test_detalhe_de_whatsapp_e_sms_traz_limite_validado_sem_campo_de_telefone(
    tmp_path: Path,
) -> None:
    """DETALHE-03: WhatsApp/SMS expõem corpo+limite configurado, sem assunto nem telefone."""

    cenario = Cenario(tmp_path)
    mensagem_whatsapp = cenario.mensagem(Canal.WHATSAPP)
    mensagem_sms = cenario.mensagem(Canal.SMS)

    detalhe_whatsapp = cenario.servico.obter(EXECUCAO_ID, mensagem_whatsapp)
    detalhe_sms = cenario.servico.obter(EXECUCAO_ID, mensagem_sms)

    assert detalhe_whatsapp is not None
    assert detalhe_whatsapp.limite_canal_corpo == LIMITES.whatsapp
    assert detalhe_whatsapp.limite_canal_assunto is None
    assert detalhe_sms is not None
    assert detalhe_sms.limite_canal_corpo == LIMITES.sms
    assert detalhe_sms.limite_canal_assunto is None
    nomes_dos_campos = {campo.name for campo in dataclasses.fields(DetalheResultado)}
    assert not any("telefone" in nome or "celular" in nome for nome in nomes_dos_campos)


def test_tres_versoes_com_duas_reprovacoes_ficam_relacionadas_na_ordem_correta(
    tmp_path: Path,
) -> None:
    """DETALHE-04: 2 reprovações + 1 aprovação final aparecem relacionadas, em ordem."""

    cenario = Cenario(tmp_path)
    mensagem_id = cenario.mensagem(Canal.SMS)

    versao_1 = cenario.mensagens.salvar_versao(
        mensagem_id, 1, SaidaCanal(corpo="Tentativa 1"), 100.0, MODELO, VERSAO_PROMPT, 5, 5,
        True, None,
    )
    cenario.avaliacoes.salvar(versao_1, False, (MOTIVO_TOM,), MODELO, 80.0)
    cenario.decisoes.salvar(
        mensagem_id, versao_1, "administrador", ResultadoDecisaoHumana.REGENERAR,
        "Tom alarmista.",
    )
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
    cenario.decisoes.salvar(
        mensagem_id, versao_3, "administrador", ResultadoDecisaoHumana.APROVAR, None
    )

    detalhe = cenario.servico.obter(EXECUCAO_ID, mensagem_id)

    assert detalhe is not None
    assert [v.versao.numero_tentativa for v in detalhe.versoes] == [1, 2, 3]
    assert [v.versao.id for v in detalhe.versoes] == [versao_1, versao_2, versao_3]
    assert detalhe.versoes[0].avaliacao_critica is not None
    assert detalhe.versoes[0].avaliacao_critica.avaliacao.aprovada is False
    assert detalhe.versoes[0].decisoes_humanas[0].resultado is ResultadoDecisaoHumana.REGENERAR
    assert detalhe.versoes[1].avaliacao_critica is not None
    assert detalhe.versoes[1].avaliacao_critica.avaliacao.aprovada is False
    assert detalhe.versoes[2].avaliacao_critica is not None
    assert detalhe.versoes[2].avaliacao_critica.avaliacao.aprovada is True
    assert detalhe.versoes[2].decisoes_humanas[0].resultado is ResultadoDecisaoHumana.APROVAR


def test_mensagem_de_outra_execucao_devolve_o_mesmo_none_que_inexistente(
    tmp_path: Path,
) -> None:
    """DETALHE-05: identificador de outra execução e identificador inexistente são
    indistinguíveis — os dois casos devolvem exatamente `None` (AD-011)."""

    cenario = Cenario(tmp_path)
    mensagem_da_outra_execucao = cenario.mensagem(Canal.SMS, execucao_id=OUTRA_EXECUCAO_ID)

    resultado_de_outra_execucao = cenario.servico.obter(EXECUCAO_ID, mensagem_da_outra_execucao)
    resultado_inexistente = cenario.servico.obter(EXECUCAO_ID, uuid4())

    assert resultado_de_outra_execucao is None
    assert resultado_inexistente is None


def test_mensagem_em_falhou_conteudo_traz_ultima_versao_e_a_excecao_associada(
    tmp_path: Path,
) -> None:
    """Edge Case: mensagem em exceção mostra a última versão e a exceção, sem inventar
    resultado."""

    cenario = Cenario(tmp_path)
    mensagem_id = cenario.mensagem(Canal.SMS)
    cenario.mensagens.salvar_versao(
        mensagem_id, 1, SaidaCanal(corpo="a" * 200), 100.0, MODELO, VERSAO_PROMPT, None, None,
        False, "limite_excedido:corpo:200:160",
    )
    cenario.excecoes.registrar(
        EXECUCAO_ID,
        "limite_conteudo_excedido",
        3,
        "A mensagem esgotou as tentativas de geração válida.",
        mensagem_id=mensagem_id,
    )
    cenario.mensagens.transicionar(mensagem_id, 1, EstadoMensagem.FALHOU_CONTEUDO)

    detalhe = cenario.servico.obter(EXECUCAO_ID, mensagem_id)

    assert detalhe is not None
    assert detalhe.estado is EstadoMensagem.FALHOU_CONTEUDO
    assert len(detalhe.versoes) == 1
    assert detalhe.versoes[0].versao.valida is False
    assert detalhe.excecao is not None
    assert detalhe.excecao.causa == "limite_conteudo_excedido"
    assert detalhe.excecao.impacto == "A mensagem esgotou as tentativas de geração válida."


def test_mensagem_sem_decisao_humana_ainda_nao_gera_erro(tmp_path: Path) -> None:
    """Edge Case: mensagem que nunca chegou a `aguardando_revisao` não tem decisão humana
    nem exceção — a ausência é representada sem erro técnico."""

    cenario = Cenario(tmp_path)
    mensagem_id = cenario.mensagem(Canal.SMS)
    cenario.mensagens.salvar_versao(
        mensagem_id, 1, SaidaCanal(corpo="Ainda gerando."), 100.0, MODELO, VERSAO_PROMPT, 5, 5,
        True, None,
    )

    detalhe = cenario.servico.obter(EXECUCAO_ID, mensagem_id)

    assert detalhe is not None
    assert detalhe.estado is EstadoMensagem.GERANDO
    assert len(detalhe.versoes) == 1
    assert detalhe.versoes[0].decisoes_humanas == ()
    assert detalhe.excecao is None
    assert detalhe.apresentacao_simulada is None
