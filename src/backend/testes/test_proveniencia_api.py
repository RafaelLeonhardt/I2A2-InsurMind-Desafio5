"""Testes do recurso REST/JSON de proveniência agêntica de uma mensagem (REGEN-07, 08)."""

from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from central_preventiva.adaptadores.ia.agente_redator import INSTRUCAO_SISTEMA
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_criticas import (
    RepositorioAvaliacoesCriticas,
)
from central_preventiva.adaptadores.persistencia.repositorio_contextos_agente import (
    RepositorioContextosAgente,
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
from central_preventiva.dominio.montador_contexto_agente import ContextoAgente
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

TIPO_PROBLEMA = "application/problem+json"

CHAVE_OPENAI = "sk-chave-secreta-de-teste"
NOME_SEGURADO = "Marina Sobrenome Silva"
TELEFONE_SEGURADO = "+5551999998888"

CONTEXTO = ContextoAgente(
    evento="chuva_intensa",
    localizacao_aproximada="9990001",
    coberturas_relevantes=("alagamento",),
    canal="sms",
    orientacoes_seguranca=("Evite áreas alagadas.",),
)

CATEGORIAS_USADAS = ("evento", "localizacao_aproximada", "coberturas", "canal", "orientacoes")
CATEGORIAS_NAO_USADAS = ("documentos", "dados_financeiros", "contato", "identificacao")


def preparar_banco(tmp_path: Path) -> Path:
    """Aplica as migrações versionadas em um banco temporário do teste."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def cliente_para(caminho: Path) -> TestClient:
    """Compõe a aplicação real apontada ao banco temporário, com chave configurada."""

    configuracao = Configuracao(
        host_api="127.0.0.1",
        origem_frontend="http://127.0.0.1:5173",
        caminho_banco=caminho,
        chave_openai=CHAVE_OPENAI,  # type: ignore[arg-type]
    )
    return TestClient(criar_aplicacao(configuracao))


def semear_ciclo_de_duas_tentativas(caminho: Path) -> tuple[UUID, UUID]:
    """Persiste uma mensagem com a tentativa 1 reprovada e a 2 aprovada.

    É exatamente o histórico que o ciclo automático da 3.4 deixa: duas versões, duas
    avaliações, nenhuma sobrescrita.
    """

    execucao_id = RepositorioExecucaoPreventiva(caminho).criar(
        EstadoExecucao.PROCESSANDO_MENSAGENS
    )
    elegibilidade_id = uuid4()
    RepositorioContextosAgente(caminho).salvar(
        execucao_id, elegibilidade_id, CONTEXTO, CATEGORIAS_USADAS, CATEGORIAS_NAO_USADAS
    )
    mensagens = RepositorioMensagens(caminho)
    avaliacoes = RepositorioAvaliacoesCriticas(caminho)
    mensagem_id = mensagens.criar(execucao_id, elegibilidade_id, Canal.SMS)

    primeira = mensagens.salvar_versao(
        mensagem_id=mensagem_id,
        numero_tentativa=1,
        conteudo=SaidaCanal(corpo="Alerta enfático demais."),
        duracao_ms=742.5,
        modelo="gpt-4o-mini",
        versao_prompt="v1",
        tokens_entrada=210,
        tokens_saida=64,
        valida=True,
        motivo_invalidez=None,
    )
    mensagens.transicionar(mensagem_id, 1, EstadoMensagem.CRITICANDO)
    avaliacoes.salvar(
        primeira,
        False,
        (MotivoCritica(CategoriaCritica.TOM, "O texto usa tom alarmista."),),
        "gpt-4o-mini",
        120.5,
    )
    mensagens.incrementar_tentativa(mensagem_id, 2)
    mensagens.transicionar(mensagem_id, 3, EstadoMensagem.GERANDO)

    segunda = mensagens.salvar_versao(
        mensagem_id=mensagem_id,
        numero_tentativa=2,
        conteudo=SaidaCanal(corpo="Chuva forte hoje. Evite áreas alagadas."),
        duracao_ms=310.0,
        modelo="gpt-4o-mini",
        versao_prompt="v1",
        tokens_entrada=190,
        tokens_saida=58,
        valida=True,
        motivo_invalidez=None,
    )
    mensagens.transicionar(mensagem_id, 4, EstadoMensagem.CRITICANDO)
    avaliacoes.salvar(segunda, True, (), "gpt-4o-mini", 95.0)
    mensagens.transicionar(mensagem_id, 5, EstadoMensagem.AGUARDANDO_REVISAO)
    return mensagem_id, elegibilidade_id


def test_proveniencia_traz_todos_os_campos_do_ac_por_tentativa(tmp_path: Path) -> None:
    """REGEN-07: agente, modelo, versão do prompt, categorias de entrada, saída, avaliação,
    tentativa, duração e métricas de uso, para cada tentativa produzida."""

    caminho = preparar_banco(tmp_path)
    mensagem_id, _ = semear_ciclo_de_duas_tentativas(caminho)

    resposta = cliente_para(caminho).get(f"/api/v1/mensagens/{mensagem_id}/proveniencia")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["mensagem_id"] == str(mensagem_id)
    assert corpo["tentativa_atual"] == 2
    assert corpo["limite_tentativas"] == 3
    assert corpo["categorias_entrada"]["usadas"] == list(CATEGORIAS_USADAS)
    assert corpo["categorias_entrada"]["nao_usadas"] == list(CATEGORIAS_NAO_USADAS)

    primeira, segunda = corpo["tentativas"]
    assert primeira["numero_tentativa"] == 1
    assert primeira["agente"] == "redator"
    assert primeira["modelo"] == "gpt-4o-mini"
    assert primeira["versao_prompt"] == "v1"
    assert primeira["saida"] == {"assunto": None, "corpo": "Alerta enfático demais."}
    assert primeira["valida"] is True
    assert primeira["motivo_invalidez"] is None
    assert primeira["duracao_ms"] == 742.5
    assert primeira["tokens_entrada"] == 210
    assert primeira["tokens_saida"] == 64
    assert primeira["avaliacao"]["agente"] == "critico"
    assert primeira["avaliacao"]["modelo"] == "gpt-4o-mini"
    assert primeira["avaliacao"]["aprovada"] is False
    assert primeira["avaliacao"]["motivos"] == [
        {"categoria": "tom", "justificativa": "O texto usa tom alarmista."}
    ]
    assert primeira["avaliacao"]["duracao_ms"] == 120.5

    assert segunda["numero_tentativa"] == 2
    assert segunda["saida"]["corpo"] == "Chuva forte hoje. Evite áreas alagadas."
    assert segunda["duracao_ms"] == 310.0
    assert segunda["tokens_entrada"] == 190
    assert segunda["avaliacao"]["aprovada"] is True
    assert segunda["avaliacao"]["motivos"] == []


def test_versao_reprovada_continua_consultavel_depois_da_regeneracao(
    tmp_path: Path,
) -> None:
    """REGEN-01 + REGEN-07: o histórico é imutável — a versão reprovada da tentativa 1
    continua na resposta com o conteúdo e o veredito originais, ao lado da tentativa 2."""

    caminho = preparar_banco(tmp_path)
    mensagem_id, _ = semear_ciclo_de_duas_tentativas(caminho)

    corpo = cliente_para(caminho).get(
        f"/api/v1/mensagens/{mensagem_id}/proveniencia"
    ).json()

    assert [item["numero_tentativa"] for item in corpo["tentativas"]] == [1, 2]
    assert corpo["tentativas"][0]["saida"]["corpo"] == "Alerta enfático demais."
    assert corpo["tentativas"][0]["avaliacao"]["aprovada"] is False


def test_proveniencia_nao_expoe_chave_contato_nem_prompt(tmp_path: Path) -> None:
    """REGEN-08: a resposta não carrega chave de API, contato ou identificação direta do
    segurado, nem o texto do prompt — só categorias de dado e o conteúdo produzido."""

    caminho = preparar_banco(tmp_path)
    mensagem_id, elegibilidade_id = semear_ciclo_de_duas_tentativas(caminho)

    bruto = cliente_para(caminho).get(f"/api/v1/mensagens/{mensagem_id}/proveniencia").text

    assert CHAVE_OPENAI not in bruto
    assert NOME_SEGURADO not in bruto
    assert TELEFONE_SEGURADO not in bruto
    assert INSTRUCAO_SISTEMA not in bruto
    assert "prompt" not in bruto.lower().replace("versao_prompt", "")
    assert str(elegibilidade_id) in bruto


def test_tentativa_ainda_nao_avaliada_traz_avaliacao_nula(tmp_path: Path) -> None:
    """REGEN-07: uma tentativa gerada e ainda não criticada aparece com avaliação nula,
    nunca com um veredito inventado."""

    caminho = preparar_banco(tmp_path)
    execucao_id = RepositorioExecucaoPreventiva(caminho).criar(
        EstadoExecucao.PROCESSANDO_MENSAGENS
    )
    mensagens = RepositorioMensagens(caminho)
    mensagem_id = mensagens.criar(execucao_id, uuid4(), Canal.EMAIL)
    mensagens.salvar_versao(
        mensagem_id=mensagem_id,
        numero_tentativa=1,
        conteudo=SaidaCanal(corpo="Corpo do e-mail.", assunto="Alerta preventivo"),
        duracao_ms=50.0,
        modelo="gpt-4o-mini",
        versao_prompt="v1",
        tokens_entrada=None,
        tokens_saida=None,
        valida=False,
        motivo_invalidez="limite_excedido:assunto:79:78",
    )

    corpo = cliente_para(caminho).get(
        f"/api/v1/mensagens/{mensagem_id}/proveniencia"
    ).json()

    tentativa = corpo["tentativas"][0]
    assert tentativa["avaliacao"] is None
    assert tentativa["valida"] is False
    assert tentativa["motivo_invalidez"] == "limite_excedido:assunto:79:78"
    assert tentativa["saida"]["assunto"] == "Alerta preventivo"
    assert tentativa["tokens_entrada"] is None


def test_mensagem_sem_tentativa_devolve_lista_vazia_sem_inventar_progresso(
    tmp_path: Path,
) -> None:
    """REGEN-07: antes da primeira versão, a proveniência é vazia, não ausente."""

    caminho = preparar_banco(tmp_path)
    execucao_id = RepositorioExecucaoPreventiva(caminho).criar(
        EstadoExecucao.PROCESSANDO_MENSAGENS
    )
    mensagem_id = RepositorioMensagens(caminho).criar(execucao_id, uuid4(), Canal.SMS)

    corpo = cliente_para(caminho).get(
        f"/api/v1/mensagens/{mensagem_id}/proveniencia"
    ).json()

    assert corpo["tentativas"] == []
    assert corpo["tentativa_atual"] == 1
    assert corpo["limite_tentativas"] == 3
    assert corpo["categorias_entrada"] == {"usadas": [], "nao_usadas": []}


def test_consultas_repetidas_devolvem_o_mesmo_conteudo(tmp_path: Path) -> None:
    """REGEN-07: a consulta é de leitura — não gera, não reavalia e não muda nada."""

    caminho = preparar_banco(tmp_path)
    mensagem_id, _ = semear_ciclo_de_duas_tentativas(caminho)
    cliente = cliente_para(caminho)

    primeira = cliente.get(f"/api/v1/mensagens/{mensagem_id}/proveniencia")
    segunda = cliente.get(f"/api/v1/mensagens/{mensagem_id}/proveniencia")

    assert primeira.json() == segunda.json()
    assert len(RepositorioMensagens(caminho).listar_versoes(mensagem_id)) == 2


def test_mensagem_inexistente_devolve_404_correlacionado(tmp_path: Path) -> None:
    """Mensagem inexistente é 404 `problem+json`, com impacto e próxima ação."""

    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(f"/api/v1/mensagens/{uuid4()}/proveniencia")

    assert resposta.status_code == 404
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    corpo = resposta.json()
    assert corpo["codigo"] == "mensagem_inexistente"
    assert corpo["correlacao_id"]
    assert corpo["impacto"] == "Nenhuma proveniência pode ser exibida."
    assert corpo["proxima_acao"]


def test_identificador_invalido_devolve_422_correlacionado(tmp_path: Path) -> None:
    """Identificador que não é UUID é 422 `problem+json`, sem tocar a persistência."""

    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get("/api/v1/mensagens/nao-e-uuid/proveniencia")

    assert resposta.status_code == 422
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "mensagem_id_invalido"
