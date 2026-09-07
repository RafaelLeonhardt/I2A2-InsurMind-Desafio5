"""Testes do recurso REST/JSON do detalhe individual de um resultado (DETALHE-01..05)."""

import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_criticas import (
    RepositorioAvaliacoesCriticas,
)
from central_preventiva.adaptadores.persistencia.repositorio_decisoes_humanas import (
    RepositorioDecisoesHumanas,
)
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    MensagemAprovada,
    RepositorioEntregasSimuladas,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
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
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.avaliador_elegibilidade import (
    OPERANDO_AREA_AFETADA,
    OPERANDO_COBERTURA_EXIGIDA,
)
from central_preventiva.dominio.avaliador_risco import Criterio
from central_preventiva.dominio.decisao_humana import ResultadoDecisaoHumana
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

TIPO_PROBLEMA = "application/problem+json"
REGRA_ID = UUID("33333333-3333-3333-3333-333333333333")
REGRA_VERSAO = 4
EVENTO = EventoMeteorologico(
    id=uuid4(),
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


def preparar_banco(tmp_path: Path) -> Path:
    """Aplica as migrações versionadas e semeia evento/regra em um banco temporário."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    RepositorioEventosMeteorologicos(caminho).salvar(EVENTO)
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
            "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
            "VALUES (?, 'chuva_intensa', 50.0, '9990001', 'residencial', 'alagamento', "
            "6, 'sms', ?, 'ativa')",
            [REGRA_ID, REGRA_VERSAO],
        )
    return caminho


def cliente_para(caminho: Path) -> TestClient:
    """Compõe a aplicação real apontada ao banco temporário do teste."""

    configuracao = Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5151",
        caminho_banco=caminho,
    )
    return TestClient(criar_aplicacao(configuracao))


def criar_execucao(caminho: Path) -> UUID:
    """Cria uma execução concluída, mesmo estado usado pelos testes de 4.1."""

    return RepositorioExecucaoPreventiva(caminho).criar(EstadoExecucao.CONCLUIDA)


def elegibilidade_para(caminho: Path, execucao_id: UUID, canal: str) -> UUID:
    """Insere um item do público elegível, no formato que 2.5 grava."""

    id_registro = uuid4()
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO elegibilidades_historicas "
            "(id, execucao_id, evento_id, regra_id, segurado_id, "
            "apolice_id, elegivel, criterios, canal, nome_segurado, justificativa) "
            "VALUES (?, ?, ?, ?, ?, ?, true, ?, ?, 'Marina Teste', "
            "'Atende integralmente aos critérios da regra ativa.')",
            [
                id_registro,
                execucao_id,
                EVENTO.id,
                REGRA_ID,
                uuid4(),
                uuid4(),
                serializar_criterios(CRITERIOS),
                canal,
            ],
        )
    return id_registro


def test_mensagem_de_email_aprovada_e_simulada_devolve_200_com_o_detalhe(
    tmp_path: Path,
) -> None:
    """DETALHE-01/02: caminho feliz de e-mail expõe todos os campos exigidos pelo AC."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho)
    elegibilidade_id = elegibilidade_para(caminho, execucao_id, "email")
    mensagens = RepositorioMensagens(caminho)
    mensagem_id = mensagens.criar(execucao_id, elegibilidade_id, Canal.EMAIL)
    versao_id = mensagens.salvar_versao(
        mensagem_id, 1, SaidaCanal(corpo="Chuva forte.", assunto="Alerta"), 100.0,
        "gpt-4o-mini", "v1", 5, 5, True, None,
    )
    RepositorioAvaliacoesCriticas(caminho).salvar(versao_id, True, (), "gpt-4o-mini", 80.0)
    RepositorioDecisoesHumanas(caminho).salvar(
        mensagem_id, versao_id, "administrador", ResultadoDecisaoHumana.APROVAR, None
    )
    mensagens.transicionar(mensagem_id, 1, EstadoMensagem.APROVADA)
    mensagens.transicionar(mensagem_id, 2, EstadoMensagem.SIMULADA_ENTREGUE)
    RepositorioEntregasSimuladas(caminho).criar_lote(
        execucao_id,
        [
            MensagemAprovada(
                mensagem_id, Canal.EMAIL, SaidaCanal(corpo="Chuva forte.", assunto="Alerta")
            )
        ],
    )

    resposta = cliente_para(caminho).get(
        f"/api/v1/execucoes/{execucao_id}/mensagens/{mensagem_id}/detalhe"
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["mensagem_id"] == str(mensagem_id)
    assert corpo["nome_segurado"] == "Marina Teste"
    assert corpo["canal"] == "email"
    assert corpo["estado"] == "simulada_entregue"
    assert corpo["evento"]["id"] == str(EVENTO.id)
    assert corpo["regra_versao"] == REGRA_VERSAO
    assert corpo["apresentacao_simulada"]["assunto"] == "Alerta"
    assert corpo["apresentacao_simulada"]["corpo"] == "Chuva forte."
    assert corpo["apresentacao_simulada"]["rotulo"] == "simulada"
    assert len(corpo["versoes"]) == 1
    assert corpo["versoes"][0]["avaliacao_critica"]["aprovada"] is True
    assert corpo["versoes"][0]["decisoes_humanas"][0]["resultado"] == "aprovar"


def test_mensagem_de_whatsapp_devolve_limite_sem_assunto_nem_telefone(tmp_path: Path) -> None:
    """DETALHE-03: WhatsApp expõe corpo+limite, sem assunto nem qualquer campo de telefone."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho)
    elegibilidade_id = elegibilidade_para(caminho, execucao_id, "whatsapp")
    mensagem_id = RepositorioMensagens(caminho).criar(execucao_id, elegibilidade_id, Canal.WHATSAPP)

    resposta = cliente_para(caminho).get(
        f"/api/v1/execucoes/{execucao_id}/mensagens/{mensagem_id}/detalhe"
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["canal"] == "whatsapp"
    assert corpo["limite_canal_assunto"] is None
    assert corpo["limite_canal_corpo"] > 0
    assert "telefone" not in resposta.text.lower()
    assert "celular" not in resposta.text.lower()


def test_mensagem_inexistente_devolve_404_correlacionado(tmp_path: Path) -> None:
    """Mensagem inexistente é 404 `problem+json`, com impacto e próxima ação."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho)

    resposta = cliente_para(caminho).get(
        f"/api/v1/execucoes/{execucao_id}/mensagens/{uuid4()}/detalhe"
    )

    assert resposta.status_code == 404
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    corpo = resposta.json()
    assert corpo["codigo"] == "mensagem_nao_encontrada"
    assert corpo["correlacao_id"]
    assert corpo["impacto"] == "Nenhum detalhe pode ser exibido."


def test_mensagem_de_outra_execucao_devolve_a_mesma_resposta_404(tmp_path: Path) -> None:
    """DETALHE-05: mensagem de outra execução devolve resposta idêntica à inexistente."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho)
    outra_execucao_id = criar_execucao(caminho)
    elegibilidade_id = elegibilidade_para(caminho, outra_execucao_id, "sms")
    mensagem_de_outra = RepositorioMensagens(caminho).criar(
        outra_execucao_id, elegibilidade_id, Canal.SMS
    )

    resposta_de_outra_execucao = cliente_para(caminho).get(
        f"/api/v1/execucoes/{execucao_id}/mensagens/{mensagem_de_outra}/detalhe"
    )
    resposta_inexistente = cliente_para(caminho).get(
        f"/api/v1/execucoes/{execucao_id}/mensagens/{uuid4()}/detalhe"
    )

    assert resposta_de_outra_execucao.status_code == resposta_inexistente.status_code == 404
    corpo_outra = dict(resposta_de_outra_execucao.json())
    corpo_inexistente = dict(resposta_inexistente.json())
    # A `ocorrencia` ecoa de volta o próprio `mensagem_id` que o chamador enviou — não revela
    # nada novo, já que o chamador já conhecia esse valor. O que precisa ser idêntico é o
    # `codigo`/`impacto`/`proxima_acao`: nenhuma pista que distinga "existe em outro contexto"
    # de "nunca existiu" (DETALHE-05, AD-011).
    assert corpo_outra["codigo"] == corpo_inexistente["codigo"]
    assert corpo_outra["impacto"] == corpo_inexistente["impacto"]
    assert corpo_outra["proxima_acao"] == corpo_inexistente["proxima_acao"]
    modelo_ocorrencia = re.sub(r"'[0-9a-f-]{36}'", "'X'", corpo_outra["ocorrencia"])
    assert re.sub(r"'[0-9a-f-]{36}'", "'X'", corpo_inexistente["ocorrencia"]) == modelo_ocorrencia


def test_identificador_invalido_devolve_422_correlacionado(tmp_path: Path) -> None:
    """Identificador malformado é 422 `problem+json`, não 500."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho)

    resposta = cliente_para(caminho).get(
        f"/api/v1/execucoes/{execucao_id}/mensagens/nao-e-uuid/detalhe"
    )

    assert resposta.status_code == 422
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "identificador_invalido"
