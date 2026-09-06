"""Testes do recurso REST/JSON da explicação acessível de um comunicado
(EXPLICACAO-01..05).
"""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

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
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    MensagemAprovada,
    RepositorioEntregasSimuladas,
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
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)
from central_preventiva.dominio.montador_contexto_agente import ContextoAgente
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

TIPO_PROBLEMA = "application/problem+json"
EXECUCAO_ID = UUID("11111111-1111-1111-1111-111111111111")
EVENTO_ID = UUID("22222222-2222-2222-2222-222222222222")
REGRA_ID = UUID("33333333-3333-3333-3333-333333333333")
REGRA_VERSAO = 7
CARLOS_ID = UUID("44444444-4444-4444-4444-444444444444")
OUTRO_SEGURADO_ID = UUID("55555555-5555-5555-5555-555555555555")
MODELO = "gpt-4o-mini"
VERSAO_PROMPT = "v1"

EVENTO = EventoMeteorologico(
    id=EVENTO_ID,
    tipo=TipoEventoMeteorologico.GRANIZO,
    area="9990001",
    periodo_inicio=datetime(2026, 9, 5, 9, 0, tzinfo=UTC),
    periodo_fim=datetime(2026, 9, 5, 12, 0, tzinfo=UTC),
    intensidade=71.0,
    proveniencia=ProvenienciaEvento.SINTETICO,
    instante_observado=datetime(2026, 9, 5, 12, 0, tzinfo=UTC),
)

CRITERIOS = (
    Criterio(OPERANDO_AREA_AFETADA, "9990001", True, "Área corresponde."),
    Criterio(OPERANDO_COBERTURA_EXIGIDA, "alagamento", True, "Possui cobertura."),
)

CONTEXTO_MINIMO = ContextoAgente(
    evento="granizo",
    localizacao_aproximada="9990001",
    coberturas_relevantes=("alagamento",),
    canal="whatsapp",
    orientacoes_seguranca=("Evite áreas alagadas.",),
)
CATEGORIAS_USADAS = ("evento", "localizacao_aproximada", "coberturas_relevantes", "canal")
CATEGORIAS_NAO_USADAS = ("documentos", "dados_financeiros")


def cliente_para(caminho: Path) -> TestClient:
    """Compõe a aplicação real apontada ao banco temporário do teste."""

    configuracao = Configuracao(
        host_api="127.0.0.1", origem_frontend="http://127.0.0.1:5173", caminho_banco=caminho
    )
    return TestClient(criar_aplicacao(configuracao))


class Semente:
    """Prepara um banco temporário migrado com um comunicado explicável completo."""

    def __init__(self, tmp_path: Path) -> None:
        self.caminho = tmp_path / "central_preventiva.duckdb"
        ExecutorMigracoes(self.caminho).aplicar_pendentes()
        self.mensagens = RepositorioMensagens(self.caminho)
        self.avaliacoes = RepositorioAvaliacoesCriticas(self.caminho)
        self.decisoes = RepositorioDecisoesHumanas(self.caminho)
        self.entregas = RepositorioEntregasSimuladas(self.caminho)
        self.eventos = RepositorioEventosMeteorologicos(self.caminho)
        self.contextos = RepositorioContextosAgente(self.caminho)
        self.eventos.salvar(EVENTO)
        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(
                "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
                "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
                "VALUES (?, 'granizo', 50.0, '9990001', 'residencial', 'alagamento', "
                "6, 'whatsapp', ?, 'ativa')",
                [REGRA_ID, REGRA_VERSAO],
            )
            conexao.execute(
                "INSERT INTO execucao_preventiva (id, estado, versao) "
                "VALUES (?, 'concluida', 1)",
                [EXECUCAO_ID],
            )

    def elegibilidade(self, segurado_id: UUID = CARLOS_ID) -> UUID:
        id_registro = uuid4()
        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(
                "INSERT INTO elegibilidades_historicas "
                "(id, execucao_id, evento_id, regra_id, segurado_id, "
                "apolice_id, elegivel, criterios, canal, nome_segurado, justificativa) "
                "VALUES (?, ?, ?, ?, ?, ?, true, ?, 'whatsapp', 'Carlos Teste', "
                "'Atende integralmente aos critérios da regra ativa.')",
                [
                    id_registro,
                    EXECUCAO_ID,
                    EVENTO_ID,
                    REGRA_ID,
                    segurado_id,
                    uuid4(),
                    serializar_criterios(CRITERIOS),
                ],
            )
        return id_registro

    def comunicado_completo(self, segurado_id: UUID = CARLOS_ID) -> UUID:
        """Cria uma mensagem aprovada, criticada e simulada; devolve o `entrega_simulada_id`."""

        elegibilidade_id = self.elegibilidade(segurado_id)
        self.contextos.salvar(
            EXECUCAO_ID,
            elegibilidade_id,
            CONTEXTO_MINIMO,
            CATEGORIAS_USADAS,
            CATEGORIAS_NAO_USADAS,
        )
        mensagem_id = self.mensagens.criar(EXECUCAO_ID, elegibilidade_id, Canal.WHATSAPP)
        versao_id = self.mensagens.salvar_versao(
            mensagem_id, 1, SaidaCanal(corpo="Granizo previsto na sua região."), 100.0, MODELO,
            VERSAO_PROMPT, 5, 5, True, None,
        )
        self.avaliacoes.salvar(versao_id, True, (), MODELO, 80.0)
        self.decisoes.salvar(
            mensagem_id, versao_id, "administrador", ResultadoDecisaoHumana.APROVAR, None
        )
        self.mensagens.transicionar(mensagem_id, 1, EstadoMensagem.APROVADA)
        self.mensagens.transicionar(mensagem_id, 2, EstadoMensagem.SIMULADA_ENTREGUE)
        self.entregas.criar_lote(
            EXECUCAO_ID,
            [
                MensagemAprovada(
                    mensagem_id, Canal.WHATSAPP, SaidaCanal(corpo="Granizo previsto na sua região.")
                )
            ],
        )
        entrega = next(
            entrega
            for entrega in self.entregas.listar_por_execucao(EXECUCAO_ID)
            if entrega.mensagem_id == mensagem_id
        )
        return entrega.id


def test_explicacao_completa_traz_secoes_deterministica_e_agente_com_contexto_e_previa(
    tmp_path: Path,
) -> None:
    """EXPLICACAO-01..04: `200` com evento/regra, agente, contexto e prévia fiel."""

    semente = Semente(tmp_path)
    entrega_id = semente.comunicado_completo()
    cliente = cliente_para(semente.caminho)

    resposta = cliente.get(f"/api/v1/segurados/{CARLOS_ID}/comunicados/{entrega_id}/explicacao")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["entrega_simulada_id"] == str(entrega_id)
    assert corpo["execucao_origem_id"] is None
    assert corpo["evento_e_regra"]["origem"] == "deterministica"
    assert corpo["evento_e_regra"]["evento"]["tipo"] == "granizo"
    assert corpo["evento_e_regra"]["regra_id"] == str(REGRA_ID)
    assert corpo["evento_e_regra"]["regra_versao"] == REGRA_VERSAO
    assert corpo["agente"]["origem"] == "agente"
    assert corpo["agente"]["status"] == "completa"
    assert corpo["agente"]["causa_excecao"] is None
    assert len(corpo["agente"]["tentativas"]) == 1
    tentativa = corpo["agente"]["tentativas"][0]
    assert tentativa["origem_regeneracao"] == "primeira_tentativa"
    assert tentativa["avaliacao_critica"]["aprovada"] is True
    assert tentativa["decisoes_humanas"][0]["resultado"] == "aprovar"
    assert corpo["contexto"]["categorias_usadas"] == list(CATEGORIAS_USADAS)
    assert corpo["contexto"]["categorias_nao_usadas"] == list(CATEGORIAS_NAO_USADAS)
    assert "documentos" not in corpo["contexto"]["categorias_usadas"]
    assert corpo["apresentacao_simulada"]["corpo"] == "Granizo previsto na sua região."
    assert corpo["apresentacao_simulada"]["rotulo"] == "simulada"


def test_comunicado_de_outro_segurado_devolve_404_generico(tmp_path: Path) -> None:
    """AD-011: comunicado de outro segurado e inexistente devolvem a mesma resposta `404`."""

    semente = Semente(tmp_path)
    entrega_de_outro = semente.comunicado_completo(segurado_id=OUTRO_SEGURADO_ID)
    cliente = cliente_para(semente.caminho)

    resposta_de_outro = cliente.get(
        f"/api/v1/segurados/{CARLOS_ID}/comunicados/{entrega_de_outro}/explicacao"
    )
    resposta_inexistente = cliente.get(
        f"/api/v1/segurados/{CARLOS_ID}/comunicados/{uuid4()}/explicacao"
    )

    assert resposta_de_outro.status_code == 404
    assert resposta_de_outro.headers["content-type"] == TIPO_PROBLEMA
    assert resposta_de_outro.json()["codigo"] == "explicacao_nao_encontrada"
    assert resposta_inexistente.status_code == 404
    assert resposta_inexistente.json()["codigo"] == "explicacao_nao_encontrada"


def test_identificador_invalido_devolve_422(tmp_path: Path) -> None:
    """Um identificador que não é UUID válido devolve `422`, não `500`."""

    semente = Semente(tmp_path)
    cliente = cliente_para(semente.caminho)

    resposta = cliente.get(f"/api/v1/segurados/nao-e-um-uuid/comunicados/{uuid4()}/explicacao")

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "identificador_invalido"
