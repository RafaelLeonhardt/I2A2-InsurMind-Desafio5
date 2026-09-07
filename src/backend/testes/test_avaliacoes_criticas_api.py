"""Testes do recurso REST/JSON do detalhe de uma avaliação crítica (CRIT-08, CRIT-09)."""

from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

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
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.avaliacao_critica import CategoriaCritica, MotivoCritica
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

TIPO_PROBLEMA = "application/problem+json"

CORPO = "Chuva forte prevista hoje na sua região. Evite áreas alagadas."


def preparar_banco(tmp_path: Path) -> Path:
    """Aplica as migrações versionadas em um banco temporário do teste."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def cliente_para(caminho: Path) -> TestClient:
    """Compõe a aplicação real apontada ao banco temporário do teste."""

    configuracao = Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5151",
        caminho_banco=caminho,
    )
    return TestClient(criar_aplicacao(configuracao))


def criar_versao(
    caminho: Path,
    valida: bool = True,
    motivo_invalidez: str | None = None,
) -> tuple[UUID, UUID]:
    """Cria uma mensagem em `criticando` com uma versão persistida, e devolve os dois ids."""

    execucao_id = RepositorioExecucaoPreventiva(caminho).criar(
        EstadoExecucao.PROCESSANDO_MENSAGENS
    )
    repo = RepositorioMensagens(caminho)
    mensagem_id = repo.criar(execucao_id, uuid4(), Canal.SMS)
    versao_id = repo.salvar_versao(
        mensagem_id=mensagem_id,
        numero_tentativa=1,
        conteudo=SaidaCanal(corpo=CORPO),
        duracao_ms=742.5,
        modelo="gpt-4o-mini",
        versao_prompt="v1",
        tokens_entrada=210,
        tokens_saida=64,
        valida=valida,
        motivo_invalidez=motivo_invalidez,
    )
    if valida:
        repo.transicionar(mensagem_id, 1, EstadoMensagem.CRITICANDO)
    return mensagem_id, versao_id


def caminho_de(mensagem_id: UUID | str, versao_id: UUID | str) -> str:
    """Monta a URL do detalhe da avaliação."""

    return f"/api/v1/mensagens/{mensagem_id}/versoes/{versao_id}/avaliacao-critica"


def test_avaliacao_reprovada_expoe_versao_criterios_decisao_motivos_e_proveniencia(
    tmp_path: Path,
) -> None:
    """CRIT-08: o detalhe traz versão, critérios, decisão, motivos, agente, modelo e duração."""

    caminho = preparar_banco(tmp_path)
    mensagem_id, versao_id = criar_versao(caminho)
    RepositorioAvaliacoesCriticas(caminho).salvar(
        versao_mensagem_id=versao_id,
        aprovada=False,
        motivos=(
            MotivoCritica(CategoriaCritica.TOM, "O texto usa tom alarmista, não preventivo."),
            MotivoCritica(CategoriaCritica.PROMESSA_INDEVIDA, "Promete indenização integral."),
        ),
        modelo="gpt-4o-mini",
        duracao_ms=91.25,
    )

    resposta = cliente_para(caminho).get(caminho_de(mensagem_id, versao_id))

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["mensagem_id"] == str(mensagem_id)
    assert corpo["versao_mensagem_id"] == str(versao_id)
    assert corpo["numero_tentativa"] == 1
    assert corpo["criterios"] == [
        "tom",
        "utilidade",
        "clareza",
        "seguranca",
        "promessa_indevida",
        "distincao_oficial",
        "adequacao_canal",
    ]
    assert corpo["aprovada"] is False
    assert corpo["motivos"] == [
        {"categoria": "tom", "justificativa": "O texto usa tom alarmista, não preventivo."},
        {"categoria": "promessa_indevida", "justificativa": "Promete indenização integral."},
    ]
    assert corpo["agente"] == "critico"
    assert corpo["modelo"] == "gpt-4o-mini"
    assert corpo["duracao_ms"] == 91.25
    assert corpo["criado_em"]


def test_detalhe_separa_a_decisao_do_agente_da_validacao_deterministica(
    tmp_path: Path,
) -> None:
    """CRIT-09: a origem agêntica e a origem determinística vêm em campos distintos, com
    o veredito estrutural de 3.2 preservado ao lado da decisão do crítico."""

    caminho = preparar_banco(tmp_path)
    mensagem_id, versao_id = criar_versao(caminho)
    RepositorioAvaliacoesCriticas(caminho).salvar(
        versao_mensagem_id=versao_id,
        aprovada=True,
        motivos=(),
        modelo="gpt-4o-mini",
        duracao_ms=12.0,
    )

    corpo = cliente_para(caminho).get(caminho_de(mensagem_id, versao_id)).json()

    assert corpo["origem"] == "agente_ia"
    assert corpo["validacao_deterministica"] == {
        "origem": "regras_deterministicas",
        "valida": True,
        "motivo_invalidez": None,
    }
    assert corpo["origem"] != corpo["validacao_deterministica"]["origem"]


def test_aprovacao_do_critico_nao_apaga_o_motivo_da_recusa_deterministica(
    tmp_path: Path,
) -> None:
    """CRIT-04, CRIT-09: mesmo com o crítico aprovando, o veredito determinístico da
    versão continua exposto como está — a aprovação textual não o sobrepõe."""

    caminho = preparar_banco(tmp_path)
    mensagem_id, versao_id = criar_versao(
        caminho, valida=False, motivo_invalidez="limite_excedido:corpo:161:160"
    )
    RepositorioAvaliacoesCriticas(caminho).salvar(
        versao_mensagem_id=versao_id,
        aprovada=True,
        motivos=(),
        modelo="gpt-4o-mini",
        duracao_ms=8.0,
    )

    corpo = cliente_para(caminho).get(caminho_de(mensagem_id, versao_id)).json()

    assert corpo["aprovada"] is True
    assert corpo["validacao_deterministica"]["valida"] is False
    assert (
        corpo["validacao_deterministica"]["motivo_invalidez"]
        == "limite_excedido:corpo:161:160"
    )


def test_aprovacao_devolve_decisao_sem_motivos(tmp_path: Path) -> None:
    """CRIT-08: uma aprovação aparece com a lista de motivos vazia, não omitida."""

    caminho = preparar_banco(tmp_path)
    mensagem_id, versao_id = criar_versao(caminho)
    RepositorioAvaliacoesCriticas(caminho).salvar(versao_id, True, (), "gpt-4o-mini", 30.0)

    corpo = cliente_para(caminho).get(caminho_de(mensagem_id, versao_id)).json()

    assert corpo["aprovada"] is True
    assert corpo["motivos"] == []


def test_versao_ainda_nao_avaliada_devolve_404_correlacionado(tmp_path: Path) -> None:
    """T5: versão sem avaliação é 404 `problem+json`, com impacto e próxima ação."""

    caminho = preparar_banco(tmp_path)
    mensagem_id, versao_id = criar_versao(caminho)

    resposta = cliente_para(caminho).get(caminho_de(mensagem_id, versao_id))

    assert resposta.status_code == 404
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    corpo = resposta.json()
    assert corpo["codigo"] == "avaliacao_inexistente"
    assert corpo["correlacao_id"]
    assert corpo["impacto"]
    assert corpo["proxima_acao"]


def test_mensagem_inexistente_devolve_404_correlacionado(tmp_path: Path) -> None:
    """Mensagem inexistente é 404 `problem+json`, nunca 500."""

    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(caminho_de(uuid4(), uuid4()))

    assert resposta.status_code == 404
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "mensagem_inexistente"


def test_versao_de_outra_mensagem_responde_como_versao_inexistente(tmp_path: Path) -> None:
    """AD-011: uma versão que existe mas pertence a outra mensagem devolve exatamente a
    mesma resposta de uma versão que não existe."""

    caminho = preparar_banco(tmp_path)
    mensagem_id, _ = criar_versao(caminho)
    _, versao_de_outra = criar_versao(caminho)
    RepositorioAvaliacoesCriticas(caminho).salvar(
        versao_de_outra, False, (MotivoCritica(CategoriaCritica.TOM, "Tom alarmista."),),
        "gpt-4o-mini", 10.0,
    )
    cliente = cliente_para(caminho)

    de_outra = cliente.get(caminho_de(mensagem_id, versao_de_outra))
    inexistente = cliente.get(caminho_de(mensagem_id, uuid4()))

    assert de_outra.status_code == inexistente.status_code == 404
    assert de_outra.json()["codigo"] == inexistente.json()["codigo"] == "versao_inexistente"
    assert de_outra.json()["ocorrencia"] != ""
    assert de_outra.json()["impacto"] == inexistente.json()["impacto"]
    assert de_outra.json()["proxima_acao"] == inexistente.json()["proxima_acao"]


def test_identificador_invalido_devolve_422_correlacionado(tmp_path: Path) -> None:
    """Identificador malformado é 422 `problem+json`, não 500."""

    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(caminho_de("nao-e-uuid", uuid4()))

    assert resposta.status_code == 422
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "identificador_invalido"


def test_consultas_repetidas_devolvem_o_mesmo_detalhe_sem_reavaliar(tmp_path: Path) -> None:
    """CRIT-08: o detalhe é leitura do que está persistido; consultar não reavalia nada."""

    caminho = preparar_banco(tmp_path)
    mensagem_id, versao_id = criar_versao(caminho)
    repo = RepositorioAvaliacoesCriticas(caminho)
    repo.salvar(versao_id, False, (MotivoCritica(CategoriaCritica.CLAREZA, "Ambígua."),),
                "gpt-4o-mini", 44.0)
    cliente = cliente_para(caminho)

    primeira = cliente.get(caminho_de(mensagem_id, versao_id))
    segunda = cliente.get(caminho_de(mensagem_id, versao_id))

    assert primeira.json() == segunda.json()
    registro = repo.obter_por_versao(versao_id)
    assert registro is not None
    assert registro.duracao_ms == 44.0
