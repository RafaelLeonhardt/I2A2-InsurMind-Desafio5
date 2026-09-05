"""Testes do recurso REST/JSON do comunicado e da primeira visualização (VISU-01, 04, 05)."""

from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
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
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

TIPO_PROBLEMA = "application/problem+json"
REGRA_ID = UUID("33333333-3333-3333-3333-333333333333")
CARLOS_ID = UUID("44444444-4444-4444-4444-444444444444")
OUTRO_SEGURADO_ID = UUID("55555555-5555-5555-5555-555555555555")
CRITERIOS = (
    Criterio(OPERANDO_AREA_AFETADA, "9990001", True, "Área corresponde."),
    Criterio(OPERANDO_COBERTURA_EXIGIDA, "alagamento", True, "Possui cobertura."),
)


def preparar_banco(tmp_path: Path) -> Path:
    """Aplica as migrações versionadas e semeia a regra em um banco temporário."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
            "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
            "VALUES (?, 'chuva_intensa', 50.0, '9990001', 'residencial', 'alagamento', "
            "6, 'sms', 1, 'ativa')",
            [REGRA_ID],
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


def criar_entrega(
    caminho: Path,
    estado: EstadoMensagem = EstadoMensagem.SIMULADA_ENTREGUE,
    segurado_id: UUID = CARLOS_ID,
) -> UUID:
    """Cria execução+elegibilidade+mensagem+entrega simulada para o segurado informado."""

    execucao_id = RepositorioExecucaoPreventiva(caminho).criar(EstadoExecucao.CONCLUIDA)
    evento_id = uuid4()
    elegibilidade_id = uuid4()
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO elegibilidades_historicas "
            "(id, execucao_id, evento_id, regra_id, segurado_id, "
            "apolice_id, elegivel, criterios, canal, nome_segurado, justificativa) "
            "VALUES (?, ?, ?, ?, ?, ?, true, ?, 'sms', 'Carlos Teste', "
            "'Atende integralmente aos critérios da regra ativa.')",
            [
                elegibilidade_id,
                execucao_id,
                evento_id,
                REGRA_ID,
                segurado_id,
                uuid4(),
                serializar_criterios(CRITERIOS),
            ],
        )
    mensagens = RepositorioMensagens(caminho)
    mensagem_id = mensagens.criar(execucao_id, elegibilidade_id, Canal.SMS)
    [entrega_id] = RepositorioEntregasSimuladas(caminho).criar_lote(
        execucao_id,
        [MensagemAprovada(mensagem_id, Canal.SMS, SaidaCanal(corpo="Chuva forte hoje."))],
    )
    if estado is not EstadoMensagem.GERANDO:
        mensagens.transicionar(mensagem_id, 1, estado)
    return entrega_id


def test_consultar_comunicado_devolve_200_com_conteudo_canal_e_natureza_simulada(
    tmp_path: Path,
) -> None:
    """P1 AC5: o comunicado mostra conteúdo, canal e natureza simulada."""

    caminho = preparar_banco(tmp_path)
    entrega_id = criar_entrega(caminho)

    resposta = cliente_para(caminho).get(
        f"/api/v1/segurados/{CARLOS_ID}/comunicados/{entrega_id}"
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["entrega_simulada_id"] == str(entrega_id)
    assert corpo["canal"] == "sms"
    assert corpo["corpo"] == "Chuva forte hoje."
    assert corpo["rotulo"] == "simulada"
    assert corpo["visualizacao"] is None


def test_registrar_visualizacao_devolve_200_e_e_idempotente_no_replay(tmp_path: Path) -> None:
    """VISU-01/02: a primeira chamada registra; reabrir devolve a mesma visualização."""

    caminho = preparar_banco(tmp_path)
    entrega_id = criar_entrega(caminho)
    cliente = cliente_para(caminho)

    primeira = cliente.post(
        f"/api/v1/segurados/{CARLOS_ID}/comunicados/{entrega_id}/visualizacao"
    )
    segunda = cliente.post(
        f"/api/v1/segurados/{CARLOS_ID}/comunicados/{entrega_id}/visualizacao"
    )

    assert primeira.status_code == segunda.status_code == 200
    assert primeira.json() == segunda.json()

    comunicado = cliente.get(
        f"/api/v1/segurados/{CARLOS_ID}/comunicados/{entrega_id}"
    ).json()
    assert comunicado["visualizacao"]["visualizada_em"] == primeira.json()["visualizada_em"]


def test_registrar_visualizacao_de_mensagem_nao_elegivel_devolve_409(tmp_path: Path) -> None:
    """VISU-04: mensagem em `falhou_conteudo` é recusada com erro de domínio explícito,
    application/problem+json, sem criar visualização."""

    caminho = preparar_banco(tmp_path)
    entrega_id = criar_entrega(caminho, estado=EstadoMensagem.FALHOU_CONTEUDO)

    resposta = cliente_para(caminho).post(
        f"/api/v1/segurados/{CARLOS_ID}/comunicados/{entrega_id}/visualizacao"
    )

    assert resposta.status_code == 409
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    corpo = resposta.json()
    assert corpo["codigo"] == "mensagem_nao_elegivel_para_comunicado"
    assert corpo["correlacao_id"]
    assert corpo["impacto"] == "Nenhuma visualização foi registrada."


def test_consultar_comunicado_de_outro_segurado_devolve_404_generico(tmp_path: Path) -> None:
    """VISU-05: comunicado de outro segurado devolve o mesmo 404 de um inexistente."""

    caminho = preparar_banco(tmp_path)
    entrega_de_outro = criar_entrega(caminho, segurado_id=OUTRO_SEGURADO_ID)
    cliente = cliente_para(caminho)

    resposta_de_outro = cliente.get(
        f"/api/v1/segurados/{CARLOS_ID}/comunicados/{entrega_de_outro}"
    )
    resposta_inexistente = cliente.get(
        f"/api/v1/segurados/{CARLOS_ID}/comunicados/{uuid4()}"
    )

    assert resposta_de_outro.status_code == resposta_inexistente.status_code == 404
    assert resposta_de_outro.json()["codigo"] == resposta_inexistente.json()["codigo"]


def test_registrar_visualizacao_de_outro_segurado_devolve_404_generico(
    tmp_path: Path,
) -> None:
    """VISU-05: o POST de visualização também aplica o mesmo isolamento por segurado."""

    caminho = preparar_banco(tmp_path)
    entrega_de_outro = criar_entrega(caminho, segurado_id=OUTRO_SEGURADO_ID)

    resposta = cliente_para(caminho).post(
        f"/api/v1/segurados/{CARLOS_ID}/comunicados/{entrega_de_outro}/visualizacao"
    )

    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "comunicado_nao_encontrado"


def test_identificador_invalido_devolve_422_correlacionado(tmp_path: Path) -> None:
    """Identificador malformado é 422 `problem+json`, não 500."""

    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(
        "/api/v1/segurados/nao-e-uuid/comunicados/nao-e-uuid"
    )

    assert resposta.status_code == 422
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "identificador_invalido"
