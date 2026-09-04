"""Testes do recurso REST/JSON da simulação local (SIMUL-01, 03, 06, 07, 08, 10, 11).

O banco é o real, temporário e migrado, e a aplicação é a real: só as chamadas de rede ficam
bloqueadas — o que, nesta história, também é a prova de que nenhum conector de canal é tocado,
porque qualquer chamada HTTP real quebraria o teste.
"""

import ast
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_criticas import (
    RepositorioAvaliacoesCriticas,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    RepositorioExecucaoPreventiva,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    RepositorioMensagens,
)
from central_preventiva.adaptadores.persistencia.serializacao_criterios import (
    serializar_criterios,
)
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.avaliador_elegibilidade import OPERANDO_AREA_AFETADA
from central_preventiva.dominio.avaliador_risco import Criterio
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

TIPO_PROBLEMA = "application/problem+json"
EVENTO_ID = UUID("44444444-4444-4444-4444-444444444444")
REGRA_ID = UUID("33333333-3333-3333-3333-333333333333")
AREA = "9990001"
MODELO = "gpt-4o-mini"
CORPO_SMS = "Chuva forte hoje na sua região. Evite áreas alagadas."
ASSUNTO_EMAIL = "Aviso preventivo da sua seguradora"
CRITERIOS = (Criterio(OPERANDO_AREA_AFETADA, AREA, True, "Área corresponde."),)


@pytest.fixture(autouse=True)
def _bloquear_chamadas_de_rede_reais(monkeypatch: pytest.MonkeyPatch) -> None:
    """Impede qualquer chamada HTTP real: a simulação é inteiramente local (SIMUL-05)."""

    async def _send_bloqueado(
        self: httpx.AsyncClient, request: httpx.Request, **_: object
    ) -> httpx.Response:
        raise AssertionError(f"chamada de rede real bloqueada em teste: {request.url}")

    monkeypatch.setattr(httpx.AsyncClient, "send", _send_bloqueado)


def preparar_banco(tmp_path: Path) -> Path:
    """Aplica as migrações versionadas em um banco temporário do teste."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO eventos_meteorologicos "
            "(id, tipo, area, periodo_inicio, periodo_fim, intensidade, proveniencia, "
            "instante_observado) VALUES (?, 'chuva_intensa', ?, ?, ?, 62.5, 'real_inmet', ?)",
            [
                EVENTO_ID,
                AREA,
                datetime(2026, 9, 4, 12, 0, tzinfo=UTC),
                datetime(2026, 9, 4, 18, 0, tzinfo=UTC),
                datetime(2026, 9, 4, 18, 0, tzinfo=UTC),
            ],
        )
        conexao.execute(
            "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
            "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
            "VALUES (?, 'chuva_intensa', 50.0, ?, 'residencial', 'alagamento', 6, 'sms', "
            "2, 'ativa')",
            [REGRA_ID, AREA],
        )
    return caminho


def cliente_para(caminho: Path) -> TestClient:
    """Compõe a aplicação real apontada ao banco temporário do teste."""

    configuracao = Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        caminho_banco=caminho,
    )
    return TestClient(criar_aplicacao(configuracao))


def criar_execucao(caminho: Path, estado: EstadoExecucao) -> UUID:
    """Cria uma execução no estado indicado, na versão 1."""

    execucao_id = uuid4()
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO execucao_preventiva (id, estado, versao) VALUES (?, ?, 1)",
            [execucao_id, estado.value],
        )
    return execucao_id


def semear_mensagem(
    caminho: Path,
    execucao_id: UUID,
    canal: Canal = Canal.SMS,
    estado: EstadoMensagem = EstadoMensagem.APROVADA,
    nome: str = "Pessoa Teste",
    aprovada_pelo_critico: bool = True,
) -> UUID:
    """Semeia elegibilidade, mensagem e a tentativa avaliada, no formato de 2.5/3.2/3.3."""

    elegibilidade_id = uuid4()
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO elegibilidades_historicas "
            "(id, execucao_id, evento_id, regra_id, segurado_id, apolice_id, elegivel, "
            "criterios, canal, nome_segurado, justificativa) VALUES "
            "(?, ?, ?, ?, ?, ?, true, ?, ?, ?, 'Atende integralmente aos critérios.')",
            [
                elegibilidade_id,
                execucao_id,
                EVENTO_ID,
                REGRA_ID,
                uuid4(),
                uuid4(),
                serializar_criterios(CRITERIOS),
                canal.value,
                nome,
            ],
        )
    mensagens = RepositorioMensagens(caminho)
    mensagem_id = mensagens.criar(execucao_id, elegibilidade_id, canal)
    versao_id = mensagens.salvar_versao(
        mensagem_id=mensagem_id,
        numero_tentativa=1,
        conteudo=SaidaCanal(
            corpo=CORPO_SMS,
            assunto=ASSUNTO_EMAIL if canal is Canal.EMAIL else None,
        ),
        duracao_ms=742.5,
        modelo=MODELO,
        versao_prompt="v1",
        tokens_entrada=210,
        tokens_saida=64,
        valida=True,
        motivo_invalidez=None,
    )
    RepositorioAvaliacoesCriticas(caminho).salvar(
        versao_mensagem_id=versao_id,
        aprovada=aprovada_pelo_critico,
        motivos=(),
        modelo=MODELO,
        duracao_ms=90.0,
    )
    atual = mensagens.obter(mensagem_id)
    assert atual is not None
    if atual.estado is not estado:
        mensagens.transicionar(mensagem_id, atual.versao, estado)
    return mensagem_id


def confirmar(
    cliente: TestClient,
    execucao_id: UUID,
    *,
    versao_esperada: int = 1,
    reconhecimento: bool = True,
    chave: str = "chave-1",
) -> httpx.Response:
    """Envia a confirmação da simulação pela rota real."""

    return cliente.post(
        f"/api/v1/execucoes/{execucao_id}/confirmar-simulacao",
        json={
            "versao_esperada": versao_esperada,
            "reconhecimento_simulacao": reconhecimento,
        },
        headers={"Idempotency-Key": chave},
    )


# --- Resumo da confirmação (SIMUL-01, SIMUL-06, SIMUL-11) ---------------------------------


def test_resumo_traz_evento_regra_periodo_destinatarios_e_distribuicao_por_canal(
    tmp_path: Path,
) -> None:
    """SIMUL-01: o resumo mostra evento, regra, período, quantidade de destinatários e a
    distribuição entre WhatsApp, e-mail e SMS."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho, EstadoExecucao.AGUARDANDO_CONFIRMACAO)
    semear_mensagem(caminho, execucao_id, Canal.SMS, nome="Um")
    semear_mensagem(caminho, execucao_id, Canal.SMS, nome="Dois")
    semear_mensagem(caminho, execucao_id, Canal.EMAIL, nome="Três")

    resposta = cliente_para(caminho).get(f"/api/v1/execucoes/{execucao_id}/simulacao")

    corpo = resposta.json()
    assert resposta.status_code == 200
    assert corpo["estado"] == "aguardando_confirmacao"
    assert corpo["versao"] == 1
    assert corpo["evento"]["tipo"] == "chuva_intensa"
    assert corpo["evento"]["area"] == AREA
    inicio = datetime.fromisoformat(corpo["evento"]["periodo_inicio"])
    fim = datetime.fromisoformat(corpo["evento"]["periodo_fim"])
    assert inicio.date() == date(2026, 9, 4)
    assert fim - inicio == timedelta(hours=6)  # a janela observada do evento semeado
    assert corpo["regra_id"] == str(REGRA_ID)
    assert corpo["regra_versao"] == 2
    assert corpo["total_destinatarios"] == 3
    assert corpo["distribuicao_por_canal"] == [
        {"canal": "whatsapp", "total": 0},
        {"canal": "email", "total": 1},
        {"canal": "sms", "total": 2},
    ]
    assert corpo["entregas"] == []


def test_resumo_de_execucao_inexistente_e_404_com_problema(tmp_path: Path) -> None:
    """AD-011: a resposta é idêntica para inexistente e para fora de escopo."""

    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(f"/api/v1/execucoes/{uuid4()}/simulacao")

    assert resposta.status_code == 404
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "execucao_inexistente"


def test_resumo_com_identificador_invalido_e_422(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get("/api/v1/execucoes/nao-e-uuid/simulacao")

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "execucao_id_invalido"


# --- Confirmação (SIMUL-03, SIMUL-05, SIMUL-06) -------------------------------------------


def test_confirmacao_registra_as_entregas_rotuladas_como_simuladas(tmp_path: Path) -> None:
    """SIMUL-05/SIMUL-06: as entregas aparecem com a apresentação do canal, rotuladas como
    simuladas e sem nenhum campo de confirmação ou falha de provedor externo."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho, EstadoExecucao.AGUARDANDO_CONFIRMACAO)
    sms = semear_mensagem(caminho, execucao_id, Canal.SMS, nome="Um")
    email = semear_mensagem(caminho, execucao_id, Canal.EMAIL, nome="Dois")
    cliente = cliente_para(caminho)

    resposta = confirmar(cliente, execucao_id)

    corpo = resposta.json()
    assert resposta.status_code == 200
    assert corpo["estado"] == "concluida"
    assert set(corpo["mensagens_simuladas"]) == {str(sms), str(email)}
    assert len(corpo["entregas_criadas"]) == 2

    resumo = cliente.get(f"/api/v1/execucoes/{execucao_id}/simulacao").json()
    por_mensagem = {entrega["mensagem_id"]: entrega for entrega in resumo["entregas"]}
    assert resumo["estado"] == "concluida"
    assert set(por_mensagem) == {str(sms), str(email)}
    assert por_mensagem[str(sms)]["rotulo"] == "simulada"
    assert por_mensagem[str(sms)]["canal"] == "sms"
    assert por_mensagem[str(sms)]["corpo"] == CORPO_SMS
    assert por_mensagem[str(sms)]["assunto"] is None
    assert por_mensagem[str(email)]["assunto"] == ASSUNTO_EMAIL
    assert set(por_mensagem[str(sms)]) == {
        "id",
        "mensagem_id",
        "canal",
        "rotulo",
        "assunto",
        "corpo",
        "criado_em",
    }


def test_confirmacao_sem_reconhecimento_e_recusada_com_problema(tmp_path: Path) -> None:
    """SIMUL-03: mesmo por chamada direta à API, sem o reconhecimento nada é simulado."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho, EstadoExecucao.AGUARDANDO_CONFIRMACAO)
    semear_mensagem(caminho, execucao_id)
    cliente = cliente_para(caminho)

    resposta = confirmar(cliente, execucao_id, reconhecimento=False)

    assert resposta.status_code == 422
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "reconhecimento_obrigatorio"
    resumo = cliente.get(f"/api/v1/execucoes/{execucao_id}/simulacao").json()
    assert resumo["entregas"] == []
    assert resumo["estado"] == "aguardando_confirmacao"


def test_confirmacao_sem_idempotency_key_e_recusada(tmp_path: Path) -> None:
    """AD-002: todo `POST` mutável exige a chave de idempotência."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho, EstadoExecucao.AGUARDANDO_CONFIRMACAO)
    semear_mensagem(caminho, execucao_id)

    resposta = cliente_para(caminho).post(
        f"/api/v1/execucoes/{execucao_id}/confirmar-simulacao",
        json={"versao_esperada": 1, "reconhecimento_simulacao": True},
    )

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "idempotency_key_ausente"


def test_confirmacao_com_versao_desatualizada_e_409(tmp_path: Path) -> None:
    """SIMUL-08: `versao_esperada` desatualizada é conflito, sem reclamar nada."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho, EstadoExecucao.AGUARDANDO_CONFIRMACAO)
    semear_mensagem(caminho, execucao_id)
    cliente = cliente_para(caminho)

    resposta = confirmar(cliente, execucao_id, versao_esperada=99)

    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "conflito_versao"
    assert cliente.get(f"/api/v1/execucoes/{execucao_id}/simulacao").json()["entregas"] == []


def test_repetir_a_mesma_chave_devolve_a_resposta_registrada(tmp_path: Path) -> None:
    """SIMUL-07: o replay devolve a simulação já registrada, sem segunda entrega."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho, EstadoExecucao.AGUARDANDO_CONFIRMACAO)
    semear_mensagem(caminho, execucao_id)
    cliente = cliente_para(caminho)
    primeira = confirmar(cliente, execucao_id)

    segunda = confirmar(cliente, execucao_id)

    assert segunda.status_code == 200
    assert segunda.json() == primeira.json()
    resumo = cliente.get(f"/api/v1/execucoes/{execucao_id}/simulacao").json()
    assert len(resumo["entregas"]) == 1


def test_segunda_confirmacao_com_chave_nova_e_409_sem_duplicar_entregas(
    tmp_path: Path,
) -> None:
    """SIMUL-08: a segunda confirmação do mesmo lote recebe 409 e nada é duplicado."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho, EstadoExecucao.AGUARDANDO_CONFIRMACAO)
    semear_mensagem(caminho, execucao_id)
    cliente = cliente_para(caminho)
    confirmar(cliente, execucao_id, chave="chave-a")

    resposta = confirmar(cliente, execucao_id, chave="chave-b")

    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "estado_nao_confirmavel"
    resumo = cliente.get(f"/api/v1/execucoes/{execucao_id}/simulacao").json()
    assert len(resumo["entregas"]) == 1


def test_mesma_chave_em_outra_execucao_e_conflito_de_idempotencia(tmp_path: Path) -> None:
    """AD-002 e L-027: a chave é escopada pelo alvo, então reusá-la em outra execução é
    conflito, nunca a resposta silenciosa da primeira execução."""

    caminho = preparar_banco(tmp_path)
    primeira = criar_execucao(caminho, EstadoExecucao.AGUARDANDO_CONFIRMACAO)
    segunda = criar_execucao(caminho, EstadoExecucao.AGUARDANDO_CONFIRMACAO)
    semear_mensagem(caminho, primeira, nome="Um")
    semear_mensagem(caminho, segunda, nome="Dois")
    cliente = cliente_para(caminho)
    confirmar(cliente, primeira, chave="chave-compartilhada")

    resposta = confirmar(cliente, segunda, chave="chave-compartilhada")

    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "conflito_idempotencia"
    resumo = cliente.get(f"/api/v1/execucoes/{segunda}/simulacao").json()
    assert resumo["entregas"] == []
    assert resumo["estado"] == "aguardando_confirmacao"


def test_confirmacao_de_execucao_inexistente_e_404(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = confirmar(cliente_para(caminho), uuid4())

    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "execucao_inexistente"


def test_confirmacao_de_lote_sem_nenhuma_aprovada_e_422(tmp_path: Path) -> None:
    """Segundo Edge Case da spec: sem aprovada, erro claro e nenhuma simulação vazia."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho, EstadoExecucao.AGUARDANDO_CONFIRMACAO)
    semear_mensagem(caminho, execucao_id, estado=EstadoMensagem.REJEITADA)
    cliente = cliente_para(caminho)

    resposta = confirmar(cliente, execucao_id)

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "nenhuma_mensagem_aprovada"
    resumo = cliente.get(f"/api/v1/execucoes/{execucao_id}/simulacao").json()
    assert resumo["entregas"] == []
    assert resumo["estado"] == "aguardando_confirmacao"


def test_confirmacao_fora_de_aguardando_confirmacao_e_409(tmp_path: Path) -> None:
    """SIMUL-01/SIMUL-02: o gate agregado separado é `aguardando_confirmacao`."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho, EstadoExecucao.AGUARDANDO_REVISAO)
    semear_mensagem(caminho, execucao_id)

    resposta = confirmar(cliente_para(caminho), execucao_id)

    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "estado_nao_confirmavel"


# --- Nova tentativa e navegação correlacionada (SIMUL-10, SIMUL-11) -----------------------


def test_nova_tentativa_cria_execucao_correlacionada_navegavel_nos_dois_sentidos(
    tmp_path: Path,
) -> None:
    """SIMUL-10/SIMUL-11: a nova execução aponta para a origem e a origem lista a retentativa,
    cada uma com seu próprio estado, sem mesclar históricos."""

    caminho = preparar_banco(tmp_path)
    origem_id = criar_execucao(caminho, EstadoExecucao.AGUARDANDO_CONFIRMACAO)
    semear_mensagem(caminho, origem_id)
    RepositorioExecucaoPreventiva(caminho).transicionar(
        origem_id, 1, EstadoExecucao.FALHOU_SIMULACAO
    )
    cliente = cliente_para(caminho)

    resposta = cliente.post(
        f"/api/v1/execucoes/{origem_id}/nova-tentativa-simulacao",
        headers={"Idempotency-Key": "chave-retry"},
    )

    corpo = resposta.json()
    nova_id = corpo["execucao_id"]
    assert resposta.status_code == 202
    assert corpo["execucao_origem_id"] == str(origem_id)
    assert nova_id != str(origem_id)

    resumo_nova = cliente.get(f"/api/v1/execucoes/{nova_id}/simulacao").json()
    resumo_origem = cliente.get(f"/api/v1/execucoes/{origem_id}/simulacao").json()
    assert resumo_nova["execucao_origem_id"] == str(origem_id)
    assert resumo_nova["estado"] == "aguardando_geracao"
    assert resumo_nova["retentativas"] == []
    assert resumo_origem["retentativas"] == [nova_id]
    assert resumo_origem["execucao_origem_id"] is None
    assert resumo_origem["estado"] == "falhou_simulacao"


def test_nova_tentativa_de_origem_nao_terminal_e_409(tmp_path: Path) -> None:
    """SIMUL-10: a nova tentativa só parte de `falhou_simulacao`."""

    caminho = preparar_banco(tmp_path)
    origem_id = criar_execucao(caminho, EstadoExecucao.AGUARDANDO_CONFIRMACAO)
    semear_mensagem(caminho, origem_id)

    resposta = cliente_para(caminho).post(
        f"/api/v1/execucoes/{origem_id}/nova-tentativa-simulacao",
        headers={"Idempotency-Key": "chave-retry"},
    )

    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "origem_nao_retentavel"


def test_nova_tentativa_com_snapshot_incompleto_e_422(tmp_path: Path) -> None:
    """SIMUL-10: snapshot inválido é recusado antes de criar qualquer execução."""

    caminho = preparar_banco(tmp_path)
    origem_id = criar_execucao(caminho, EstadoExecucao.FALHOU_SIMULACAO)

    resposta = cliente_para(caminho).post(
        f"/api/v1/execucoes/{origem_id}/nova-tentativa-simulacao",
        headers={"Idempotency-Key": "chave-retry"},
    )

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "snapshot_invalido"


def test_nova_tentativa_de_execucao_inexistente_e_404(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).post(
        f"/api/v1/execucoes/{uuid4()}/nova-tentativa-simulacao",
        headers={"Idempotency-Key": "chave-retry"},
    )

    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "execucao_inexistente"


# --- Fronteira do gancho de teste ---------------------------------------------------------


def test_composicao_http_nunca_passa_o_gancho_de_falha_de_teste() -> None:
    """O `injecao_falha_teste` de `ServicoSimulacao.confirmar` é exclusivo de teste: nenhuma
    composição de produção o fornece, e por isso não existe caminho de produção capaz de
    forçar o rollback artificialmente."""

    composicoes = [
        Path("central_preventiva/adaptadores/http/simulacao.py"),
        Path("central_preventiva/composicao/api.py"),
    ]

    for modulo in composicoes:
        arvore = ast.parse(modulo.read_text(encoding="utf-8"))
        referencias = [
            no
            for no in ast.walk(arvore)
            if (isinstance(no, ast.Name) and no.id == "injecao_falha_teste")
            or (isinstance(no, ast.keyword) and no.arg == "injecao_falha_teste")
            or (isinstance(no, ast.arg) and no.arg == "injecao_falha_teste")
        ]
        assert referencias == [], f"{modulo} referencia o gancho de teste em código executável"
