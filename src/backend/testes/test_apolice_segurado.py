"""Testes do caso de uso da apólice do segurado ativo e da explicação de critérios
(APOLICE-01..06, 5.3).

Os repositórios são os reais, sobre um banco temporário migrado — mesma escolha das
histórias anteriores do Épico 5.
"""

from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_apolices import (
    RepositorioApolices,
)
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RepositorioElegibilidades,
)
from central_preventiva.adaptadores.persistencia.repositorio_segurados import (
    RepositorioSegurados,
)
from central_preventiva.aplicacao.apolice_segurado import (
    ESTADO_EXPIRADA,
    PortasApoliceSegurado,
    ServicoApoliceSegurado,
)
from central_preventiva.dominio.avaliador_elegibilidade import (
    CandidatoElegibilidade,
    ResultadoElegibilidade,
    avaliar,
)
from central_preventiva.dominio.avaliador_risco import Criterio, RegraSnapshot
from central_preventiva.dominio.evento_meteorologico import (
    EventoMeteorologico,
    ProvenienciaEvento,
    TipoEventoMeteorologico,
)

AREA = "9990001"
SEGURADO_ID = uuid4()
OUTRO_SEGURADO_ID = uuid4()
REGRA_ID = uuid4()
EVENTO_ID = uuid4()

CRITERIOS_COMPLETOS = (
    Criterio("área afetada", AREA, True, "Área da apólice corresponde à área do evento."),
    Criterio("tipo da apólice", "residencial", True, "Tipo corresponde ao exigido."),
    Criterio("situação da apólice", "ativa", True, "Apólice está ativa."),
    Criterio("cobertura exigida", "alagamento", True, "Apólice possui a cobertura exigida."),
    Criterio("participação em alertas", "True", True, "Segurado participa de alertas."),
)

RESULTADO_INCLUIDO = ResultadoElegibilidade(
    elegivel=True,
    criterios=CRITERIOS_COMPLETOS,
    canal="whatsapp",
    motivo="incluido",
    justificativa="Segurado e apólice atendem integralmente aos critérios da regra ativa.",
)


class Contexto:
    """Reúne o caso de uso real e os repositórios reais sobre um banco temporário migrado."""

    def __init__(self, tmp_path: Path) -> None:
        """Migra o banco, semeia o segurado e compõe o serviço real."""

        self.caminho = tmp_path / "central_preventiva.duckdb"
        ExecutorMigracoes(self.caminho).aplicar_pendentes()
        self.apolices = RepositorioApolices(self.caminho)
        self.segurados = RepositorioSegurados(self.caminho)
        self.elegibilidades = RepositorioElegibilidades(self.caminho)
        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(
                "INSERT INTO segurados (id, nome, codigo_ibge_area, canal_preferido, "
                "participa_de_alertas) VALUES (?, 'Carlos Teste', ?, 'sms', true)",
                [SEGURADO_ID, AREA],
            )
            conexao.execute(
                "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
                "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
                "VALUES (?, 'chuva_intensa', 50.0, ?, 'residencial', 'alagamento', 24, "
                "'whatsapp', 1, 'ativa')",
                [REGRA_ID, AREA],
            )
        self.servico = ServicoApoliceSegurado(
            PortasApoliceSegurado(
                apolices=self.apolices,
                segurados=self.segurados,
                elegibilidades=self.elegibilidades,
            )
        )

    def criar_apolice(
        self,
        segurado_id: UUID = SEGURADO_ID,
        numero: str = "RES-0001",
        situacao: str = "ativa",
        vigencia_fim: str = "2030-12-31",
    ) -> UUID:
        id_apolice = uuid4()
        with abrir_conexao(self.caminho) as conexao:
            conexao.execute(
                "INSERT INTO apolices (id, segurado_id, numero, tipo, situacao, "
                "vigencia_inicio, vigencia_fim, coberturas, endereco_risco_sintetico, "
                "codigo_ibge_area) VALUES (?, ?, ?, 'residencial', ?, '2026-01-01', ?, "
                "['alagamento'], 'Rua Sintética, 123', ?)",
                [id_apolice, segurado_id, numero, situacao, vigencia_fim, AREA],
            )
        return id_apolice

    def criar_elegibilidade(
        self,
        segurado_id: UUID = SEGURADO_ID,
        criterios: tuple[Criterio, ...] = CRITERIOS_COMPLETOS,
        execucao_id: UUID | None = None,
    ) -> UUID:
        resultado = ResultadoElegibilidade(
            elegivel=True,
            criterios=criterios,
            canal="whatsapp",
            motivo="incluido",
            justificativa="Segurado e apólice atendem integralmente aos critérios da regra ativa.",
        )
        id_registro = self.elegibilidades.salvar(
            execucao_id or uuid4(), EVENTO_ID, REGRA_ID, segurado_id, uuid4(),
            "Carlos Teste", resultado,
        )
        assert id_registro is not None
        return id_registro


def test_obter_devolve_none_sem_nenhuma_apolice(tmp_path: Path) -> None:
    contexto = Contexto(tmp_path)

    assert contexto.servico.obter(SEGURADO_ID) is None


def test_obter_apolice_ativa_traz_todos_os_campos_do_ac(tmp_path: Path) -> None:
    contexto = Contexto(tmp_path)
    contexto.criar_apolice()

    apolice = contexto.servico.obter(SEGURADO_ID)

    assert apolice is not None
    assert apolice.numero == "RES-0001"
    assert apolice.tipo == "residencial"
    assert apolice.situacao == "ativa"
    assert apolice.estado_objetivo == "ativa"
    assert apolice.vigencia_inicio == date(2026, 1, 1)
    assert apolice.vigencia_fim == date(2030, 12, 31)
    assert apolice.endereco_risco_sintetico == "Rua Sintética, 123"
    assert apolice.coberturas == ("alagamento",)
    assert apolice.canal_preferido == "sms"
    assert apolice.participa_de_alertas is True


def test_obter_apolice_cancelada_traz_estado_objetivo_textual(tmp_path: Path) -> None:
    contexto = Contexto(tmp_path)
    contexto.criar_apolice(situacao="cancelada")

    apolice = contexto.servico.obter(SEGURADO_ID)

    assert apolice is not None
    assert apolice.situacao == "cancelada"
    assert apolice.estado_objetivo == "cancelada"


def test_obter_apolice_suspensa_traz_estado_objetivo_textual(tmp_path: Path) -> None:
    contexto = Contexto(tmp_path)
    contexto.criar_apolice(situacao="suspensa")

    apolice = contexto.servico.obter(SEGURADO_ID)

    assert apolice is not None
    assert apolice.estado_objetivo == "suspensa"


def test_obter_apolice_ativa_com_vigencia_expirada_traz_estado_expirada(
    tmp_path: Path,
) -> None:
    contexto = Contexto(tmp_path)
    contexto.criar_apolice(situacao="ativa", vigencia_fim="2020-01-01")

    apolice = contexto.servico.obter(SEGURADO_ID)

    assert apolice is not None
    assert apolice.situacao == "ativa"
    assert apolice.estado_objetivo == ESTADO_EXPIRADA


def test_obter_apolice_com_vigencia_fim_hoje_ainda_e_ativa(tmp_path: Path) -> None:
    """Fronteira exata: uma apólice que vence hoje ainda está dentro do período de
    vigência (spec: "fora do período de vigência atual") — só o dia seguinte expira."""

    contexto = Contexto(tmp_path)
    hoje = date.today().isoformat()
    contexto.criar_apolice(situacao="ativa", vigencia_fim=hoje)

    apolice = contexto.servico.obter(SEGURADO_ID)

    assert apolice is not None
    assert apolice.estado_objetivo == "ativa"


def test_obter_apolice_com_vigencia_fim_ontem_ja_expirou(tmp_path: Path) -> None:
    contexto = Contexto(tmp_path)
    ontem = (date.today() - timedelta(days=1)).isoformat()
    contexto.criar_apolice(situacao="ativa", vigencia_fim=ontem)

    apolice = contexto.servico.obter(SEGURADO_ID)

    assert apolice is not None
    assert apolice.estado_objetivo == ESTADO_EXPIRADA


def test_obter_de_outro_segurado_devolve_none(tmp_path: Path) -> None:
    contexto = Contexto(tmp_path)
    contexto.criar_apolice(segurado_id=OUTRO_SEGURADO_ID)

    assert contexto.servico.obter(SEGURADO_ID) is None


def test_obter_explicacao_de_elegibilidade_inexistente_devolve_none(tmp_path: Path) -> None:
    contexto = Contexto(tmp_path)

    assert contexto.servico.obter_explicacao(SEGURADO_ID, uuid4()) is None


def test_obter_explicacao_de_outro_segurado_devolve_none(tmp_path: Path) -> None:
    contexto = Contexto(tmp_path)
    id_registro = contexto.criar_elegibilidade(segurado_id=OUTRO_SEGURADO_ID)

    assert contexto.servico.obter_explicacao(SEGURADO_ID, id_registro) is None


def test_obter_explicacao_filtra_para_categorias_relevantes_a_apolice(
    tmp_path: Path,
) -> None:
    contexto = Contexto(tmp_path)
    id_registro = contexto.criar_elegibilidade()

    explicacao = contexto.servico.obter_explicacao(SEGURADO_ID, id_registro)

    assert explicacao is not None
    operandos = {criterio.operando for criterio in explicacao.criterios}
    assert operandos == {
        "área afetada", "tipo da apólice", "situação da apólice", "cobertura exigida",
    }
    assert "participação em alertas" not in operandos


PALAVRAS_PROIBIDAS_DE_COBERTURA = ("indeniza", "sinistro", "confirma cobertura", "garantimos")
"""Palavras que nenhuma justificativa de critério pode conter (APOLICE-02)."""


def test_justificativas_reais_do_avaliador_nunca_prometem_cobertura_indenizacao_ou_sinistro() -> (
    None
):
    """Varre o texto de PRODUÇÃO de `dominio/avaliador_elegibilidade.py` (não uma
    constante escrita pelo teste) nos ramos atende/não-atende dos 4 critérios relevantes
    à apólice — `obter_explicacao` só repassa esse texto, nunca o reescreve."""

    regra = RegraSnapshot(
        id=uuid4(),
        evento_tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
        limiar_meteorologico=50.0,
        area_aplicavel=AREA,
        apolice_tipo="residencial",
        cobertura_exigida="alagamento",
        versao=1,
    )
    evento = EventoMeteorologico(
        id=uuid4(),
        tipo=TipoEventoMeteorologico.CHUVA_INTENSA,
        area=AREA,
        periodo_inicio=datetime(2026, 3, 10, 6, 0),
        periodo_fim=datetime(2026, 3, 10, 18, 0),
        intensidade=72.5,
        proveniencia=ProvenienciaEvento.SINTETICO,
        instante_observado=datetime(2026, 3, 9, 18, 0),
    )
    candidato_base = CandidatoElegibilidade(
        segurado_id=uuid4(),
        apolice_id=uuid4(),
        nome_segurado="Pessoa Segurada Sintética",
        codigo_ibge_area=AREA,
        canal_preferido="whatsapp",
        participa_de_alertas=True,
        apolice_tipo="residencial",
        apolice_situacao="ativa",
        coberturas=("alagamento", "incendio"),
    )
    variantes = (
        candidato_base,
        replace(candidato_base, codigo_ibge_area="9990099"),
        replace(candidato_base, apolice_tipo="automovel"),
        replace(candidato_base, apolice_situacao="cancelada"),
        replace(candidato_base, coberturas=("incendio",)),
    )

    todas_justificativas: list[str] = []
    for candidato in variantes:
        resultado = avaliar(candidato, evento, regra)
        todas_justificativas.extend(criterio.justificativa for criterio in resultado.criterios)

    assert len(todas_justificativas) >= 20
    texto_completo = " ".join(todas_justificativas).lower()
    for palavra_proibida in PALAVRAS_PROIBIDAS_DE_COBERTURA:
        assert palavra_proibida not in texto_completo


def test_obter_explicacao_repassa_a_justificativa_de_producao_sem_reescreve_la(
    tmp_path: Path,
) -> None:
    """Confirma que `obter_explicacao` não introduz nenhum texto próprio — o critério
    devolvido é exatamente o snapshot persistido."""

    contexto = Contexto(tmp_path)
    id_registro = contexto.criar_elegibilidade()

    explicacao = contexto.servico.obter_explicacao(SEGURADO_ID, id_registro)

    assert explicacao is not None
    criterio_area = next(c for c in explicacao.criterios if c.operando == "área afetada")
    assert criterio_area.justificativa == "Área da apólice corresponde à área do evento."


def test_obter_explicacao_de_execucao_historica_ignora_alteracao_posterior_da_apolice(
    tmp_path: Path,
) -> None:
    """APOLICE-05: a explicação usa exclusivamente o snapshot de `criterios` — nunca
    `RepositorioApolices` atual, então uma mudança posterior na apólice não a afeta."""

    contexto = Contexto(tmp_path)
    contexto.criar_apolice(situacao="ativa")
    id_registro = contexto.criar_elegibilidade()

    explicacao_antes = contexto.servico.obter_explicacao(SEGURADO_ID, id_registro)
    assert explicacao_antes is not None
    situacao_no_snapshot_antes = next(
        c.valor_observado for c in explicacao_antes.criterios if c.operando == "situação da apólice"
    )

    with abrir_conexao(contexto.caminho) as conexao:
        conexao.execute(
            "UPDATE apolices SET situacao = 'cancelada' WHERE segurado_id = ?",
            [SEGURADO_ID],
        )

    explicacao_depois = contexto.servico.obter_explicacao(SEGURADO_ID, id_registro)
    apolice_atual = contexto.servico.obter(SEGURADO_ID)

    assert explicacao_depois is not None
    situacao_no_snapshot_depois = next(
        c.valor_observado
        for c in explicacao_depois.criterios
        if c.operando == "situação da apólice"
    )
    assert situacao_no_snapshot_depois == situacao_no_snapshot_antes == "ativa"
    assert apolice_atual is not None
    assert apolice_atual.situacao == "cancelada"
