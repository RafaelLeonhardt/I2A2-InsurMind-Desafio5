"""Testes do recurso REST/JSON do alerta mais relevante do segurado ativo (VISAO-01, 06, 5.1)."""

from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RepositorioElegibilidades,
)
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    MensagemAprovada,
    RepositorioEntregasSimuladas,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import RepositorioMensagens
from central_preventiva.adaptadores.persistencia.repositorio_meteorologia import (
    RepositorioEventosMeteorologicos,
    RepositorioSincronizacoes,
)
from central_preventiva.aplicacao.portas_meteorologia import (
    EstadoSincronizacao,
    OrigemSincronizacao,
)
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.avaliador_elegibilidade import ResultadoElegibilidade
from central_preventiva.dominio.avaliador_risco import Criterio
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

TIPO_PROBLEMA = "application/problem+json"
REGRA_ID = UUID("33333333-3333-3333-3333-333333333333")
CARLOS_ID = UUID("44444444-4444-4444-4444-444444444444")
AREA = "9990001"

RESULTADO_INCLUIDO = ResultadoElegibilidade(
    elegivel=True,
    criterios=(Criterio("área afetada", AREA, True, "Área corresponde."),),
    canal="whatsapp",
    motivo="incluido",
    justificativa="Segurado e apólice atendem à regra ativa.",
)


def preparar_banco(tmp_path: Path) -> Path:
    """Aplica as migrações versionadas e semeia a regra em um banco temporário."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
            "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
            "VALUES (?, 'chuva_intensa', 50.0, ?, 'residencial', 'alagamento', 24, "
            "'whatsapp', 1, 'ativa')",
            [REGRA_ID, AREA],
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


def criar_elegibilidade_incluida(caminho: Path, segurado_id: UUID) -> UUID:
    """Persiste um evento real e uma elegibilidade `incluido` para o segurado informado."""

    evento = EventoMeteorologico(
        id=uuid4(),
        tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
        area=AREA,
        periodo_inicio=datetime(2026, 9, 4, 12, 0),
        periodo_fim=datetime(2026, 9, 4, 18, 0),
        intensidade=62.5,
        proveniencia=ProvenienciaEvento.REAL_INMET,
        instante_observado=datetime(2026, 9, 4, 18, 0),
    )
    RepositorioEventosMeteorologicos(caminho).salvar(evento)
    id_registro = RepositorioElegibilidades(caminho).salvar(
        uuid4(), evento.id, REGRA_ID, segurado_id, uuid4(), "Carlos Teste", RESULTADO_INCLUIDO
    )
    assert id_registro is not None
    return id_registro


def marcar_entrega_simulada(caminho: Path, elegibilidade_id: UUID) -> UUID:
    """Cria mensagem+entrega `simulada_entregue` para a elegibilidade (6.8)."""

    execucao_id = uuid4()
    mensagens = RepositorioMensagens(caminho)
    entregas = RepositorioEntregasSimuladas(caminho)
    mensagem_id = mensagens.criar(execucao_id, elegibilidade_id, Canal.WHATSAPP)
    [entrega_id] = entregas.criar_lote(
        execucao_id, [MensagemAprovada(mensagem_id, Canal.WHATSAPP, SaidaCanal(corpo="Corpo"))]
    )
    mensagens.transicionar(mensagem_id, 1, EstadoMensagem.SIMULADA_ENTREGUE)
    return entrega_id


def test_consultar_alerta_devolve_200_com_alerta_quando_existir(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    criar_elegibilidade_incluida(caminho, CARLOS_ID)

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/alerta-mais-relevante")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["alerta"] is not None
    alerta = corpo["alerta"]
    assert alerta["evento_tipo"] == "chuva_intensa"
    assert alerta["origem"] == "real_inmet"
    assert alerta["localizacao"] == AREA
    assert alerta["fonte_degradada"] is False
    # Contrato completo: prova que a rota não inverte/mistura os campos temporais e de
    # conteúdo ao traduzir o caso de uso para o corpo público (nenhum destes era lido
    # antes desta asserção).
    assert alerta["periodo_inicio"] == "2026-09-04T12:00:00"
    assert alerta["periodo_fim"] == "2026-09-04T18:00:00"
    assert alerta["instante_observado"] == "2026-09-04T18:00:00"
    assert "62.5" in alerta["severidade"]
    assert alerta["impactos_esperados"] == ["alagamento"]
    assert len(alerta["recomendacoes"]) > 0
    assert alerta["entrega_simulada_id"] is None


def test_consultar_alerta_com_entrega_simulada_devolve_entrega_simulada_id(
    tmp_path: Path,
) -> None:
    """6.8 (contrato de VISAO, campo aditivo): quando a elegibilidade já tem uma entrega
    `simulada_entregue`, a rota expõe o id certo, não nulo."""

    caminho = preparar_banco(tmp_path)
    elegibilidade_id = criar_elegibilidade_incluida(caminho, CARLOS_ID)
    entrega_id = marcar_entrega_simulada(caminho, elegibilidade_id)

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/alerta-mais-relevante")

    assert resposta.status_code == 200
    assert resposta.json()["alerta"]["entrega_simulada_id"] == str(entrega_id)


def test_consultar_alerta_de_evento_sintetico_devolve_origem_sintetico(
    tmp_path: Path,
) -> None:
    """A fronteira HTTP nunca rotula um cenário sintético como observação real (VISAO-02) —
    os demais testes desta rota só usam eventos `real_inmet`, o que deixaria a rota livre
    para hardcodar a origem sem que nenhum teste percebesse."""

    caminho = preparar_banco(tmp_path)
    evento = EventoMeteorologico(
        id=uuid4(),
        tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
        area=AREA,
        periodo_inicio=datetime(2026, 9, 4, 12, 0),
        periodo_fim=datetime(2026, 9, 4, 18, 0),
        intensidade=62.5,
        proveniencia=ProvenienciaEvento.SINTETICO,
        instante_observado=datetime(2026, 9, 4, 18, 0),
    )
    RepositorioEventosMeteorologicos(caminho).salvar(evento)
    RepositorioElegibilidades(caminho).salvar(
        uuid4(), evento.id, REGRA_ID, CARLOS_ID, uuid4(), "Carlos Teste", RESULTADO_INCLUIDO
    )

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/alerta-mais-relevante")

    assert resposta.status_code == 200
    assert resposta.json()["alerta"]["origem"] == "sintetico"


def test_consultar_alerta_com_fonte_degradada_devolve_fonte_degradada_true(
    tmp_path: Path,
) -> None:
    """A fronteira HTTP reflete a fonte degradada (VISAO-05) — os demais testes desta rota
    só cobrem a fonte operacional, o que deixaria a rota livre para hardcodar `false` sem
    que nenhum teste percebesse."""

    caminho = preparar_banco(tmp_path)
    criar_elegibilidade_incluida(caminho, CARLOS_ID)
    id_area = uuid4()
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO areas_monitoradas_inmet "
            "(id, codigo_estacao_inmet, nome_estacao, codigo_ibge_area, ativa) "
            "VALUES (?, 'A701', 'Estação de Teste', ?, true)",
            [id_area, AREA],
        )
    sincronizacoes = RepositorioSincronizacoes(caminho)
    sincronizacao = sincronizacoes.criar(
        uuid4(), id_area, OrigemSincronizacao.AUTOMATICA, EstadoSincronizacao.COLETANDO
    )
    sincronizacoes.atualizar_estado(sincronizacao.id, EstadoSincronizacao.FALHA)

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/alerta-mais-relevante")

    assert resposta.status_code == 200
    assert resposta.json()["alerta"]["fonte_degradada"] is True


def test_consultar_alerta_devolve_200_com_alerta_nulo_quando_nao_existir(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/alerta-mais-relevante")

    assert resposta.status_code == 200
    assert resposta.json() == {"alerta": None}


def test_consultar_alerta_de_outro_segurado_nao_vaza_para_o_segurado_consultado(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    criar_elegibilidade_incluida(caminho, uuid4())

    resposta = cliente_para(caminho).get(f"/api/v1/segurados/{CARLOS_ID}/alerta-mais-relevante")

    assert resposta.status_code == 200
    assert resposta.json() == {"alerta": None}


def test_consultar_alerta_com_identificador_invalido_devolve_422(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get("/api/v1/segurados/nao-e-um-uuid/alerta-mais-relevante")

    assert resposta.status_code == 422
    assert resposta.headers["content-type"] == TIPO_PROBLEMA
    assert resposta.json()["codigo"] == "identificador_invalido"
