"""Testes do recurso REST/JSON da lista de comunicados do segurado
(COMUNICADOS-01, COMUNICADOS-02)."""

from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    MensagemAprovada,
    RepositorioEntregasSimuladas,
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
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.avaliador_elegibilidade import (
    OPERANDO_AREA_AFETADA,
    OPERANDO_COBERTURA_EXIGIDA,
)
from central_preventiva.dominio.avaliador_risco import Criterio
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

TIPO_PROBLEMA = "application/problem+json"
EXECUCAO_ID = UUID("11111111-1111-1111-1111-111111111111")
CARLOS_ID = UUID("44444444-4444-4444-4444-444444444444")
OUTRO_SEGURADO_ID = UUID("55555555-5555-5555-5555-555555555555")
CRITERIOS = (
    Criterio(OPERANDO_AREA_AFETADA, "9990001", True, "Área corresponde."),
    Criterio(OPERANDO_COBERTURA_EXIGIDA, "alagamento", True, "Possui cobertura."),
)


def preparar_banco(tmp_path: Path) -> Path:
    """Aplica as migrações versionadas e semeia regra/execução em um banco temporário."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
            "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
            "VALUES (?, 'chuva_intensa', 50.0, '9990001', 'residencial', 'alagamento', "
            "6, 'sms', 1, 'ativa')",
            [uuid4()],
        )
        conexao.execute(
            "INSERT INTO execucao_preventiva (id, estado, versao) VALUES (?, 'concluida', 1)",
            [EXECUCAO_ID],
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


def criar_entrega(
    caminho: Path,
    canal: Canal = Canal.SMS,
    corpo: str = "Chuva forte hoje.",
    assunto: str | None = None,
    segurado_id: UUID = CARLOS_ID,
    estado: EstadoMensagem = EstadoMensagem.SIMULADA_ENTREGUE,
) -> UUID:
    """Semeia elegibilidade+mensagem+entrega simulada para o segurado informado."""

    elegibilidade_id = uuid4()
    with abrir_conexao(caminho) as conexao:
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
    mensagens = RepositorioMensagens(caminho)
    mensagem_id = mensagens.criar(EXECUCAO_ID, elegibilidade_id, canal)
    conteudo = SaidaCanal(corpo=corpo, assunto=assunto)
    [entrega_id] = RepositorioEntregasSimuladas(caminho).criar_lote(
        EXECUCAO_ID, [MensagemAprovada(mensagem_id, canal, conteudo)]
    )
    if estado is not EstadoMensagem.GERANDO:
        mensagens.transicionar(mensagem_id, 1, estado)
    return entrega_id


def test_listar_devolve_200_com_lista_vazia_sem_comunicados(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/comunicados")

    assert resposta.status_code == 200
    assert resposta.json() == {"comunicados": []}


def test_listar_devolve_canal_assunto_data_e_visualizacao_nula_de_cada_comunicado(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    entrega_id = criar_entrega(
        caminho, canal=Canal.EMAIL, corpo="Chuva forte.", assunto="Aviso preventivo"
    )

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/comunicados")

    assert resposta.status_code == 200
    [item] = resposta.json()["comunicados"]
    assert item["entrega_simulada_id"] == str(entrega_id)
    assert item["canal"] == "email"
    assert item["assunto_ou_resumo"] == "Aviso preventivo"
    assert item["visualizacao"] is None


def test_listar_traz_visualizacao_registrada_quando_ja_visualizado(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    entrega_id = criar_entrega(caminho)
    visualizacao = RepositorioVisualizacoesComunicado(caminho).registrar_primeira_visualizacao(
        entrega_id, CARLOS_ID
    )

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/comunicados")

    assert resposta.status_code == 200
    [item] = resposta.json()["comunicados"]
    assert item["visualizacao"] == {
        "id": str(visualizacao.id),
        "visualizada_em": visualizacao.visualizada_em.isoformat(),
    }


def test_listar_nao_devolve_comunicados_de_outro_segurado(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    criar_entrega(caminho, segurado_id=OUTRO_SEGURADO_ID)

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/comunicados")

    assert resposta.status_code == 200
    assert resposta.json() == {"comunicados": []}


def test_listar_com_identificador_invalido_devolve_422(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get("/api/v1/segurados/nao-e-um-uuid/comunicados")

    assert resposta.status_code == 422
    assert resposta.headers["content-type"] == TIPO_PROBLEMA
    assert resposta.json()["codigo"] == "identificador_invalido"
