"""Testes dos repositórios de candidatos e resultados de elegibilidade (ELEG-04..07)."""

from pathlib import Path
from uuid import uuid4

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RepositorioCandidatosElegibilidade,
    RepositorioElegibilidades,
)
from central_preventiva.dominio.avaliador_elegibilidade import ResultadoElegibilidade
from central_preventiva.dominio.avaliador_risco import Criterio

AREA = "9990001"


def preparar_banco(tmp_path: Path) -> Path:
    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    return caminho


def inserir_segurado(
    caminho: Path,
    canal: str = "whatsapp",
    participa: bool = True,
    area: str = AREA,
) -> str:
    id_segurado = str(uuid4())
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO segurados (id, nome, codigo_ibge_area, canal_preferido, "
            "participa_de_alertas) VALUES (?, 'Pessoa Teste', ?, ?, ?)",
            [id_segurado, area, canal, participa],
        )
    return id_segurado


def inserir_apolice(
    caminho: Path,
    segurado_id: str,
    area: str = AREA,
    tipo: str = "residencial",
    situacao: str = "ativa",
    coberturas: tuple[str, ...] = ("alagamento",),
) -> str:
    id_apolice = str(uuid4())
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO apolices (id, segurado_id, numero, tipo, situacao, "
            "vigencia_inicio, vigencia_fim, coberturas, endereco_risco_sintetico, "
            "codigo_ibge_area) VALUES (?, ?, 'NUM-TESTE', ?, ?, '2026-01-01', "
            "'2026-12-31', ?, 'Rua Teste', ?)",
            [id_apolice, segurado_id, tipo, situacao, list(coberturas), area],
        )
    return id_apolice


def inserir_regra(caminho: Path) -> str:
    id_regra = str(uuid4())
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO regras (id, evento_tipo, limiar_meteorologico, area_aplicavel, "
            "apolice_tipo, cobertura_exigida, antecedencia_horas, canal, versao, estado) "
            "VALUES (?, 'chuva_intensa', 50.0, ?, 'residencial', 'alagamento', 24, "
            "'whatsapp', 1, 'ativa')",
            [id_regra, AREA],
        )
    return id_regra


def inserir_evento(caminho: Path) -> str:
    id_evento = str(uuid4())
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO eventos_meteorologicos (id, tipo, area, periodo_inicio, "
            "periodo_fim, intensidade, proveniencia, instante_observado) VALUES "
            "(?, 'chuva_intensa', ?, '2026-03-10 06:00:00', '2026-03-10 18:00:00', "
            "72.5, 'sintetico', '2026-03-09 18:00:00')",
            [id_evento, AREA],
        )
    return id_evento


RESULTADO_INCLUIDO = ResultadoElegibilidade(
    elegivel=True,
    criterios=(
        Criterio(
            operando="área afetada",
            valor_observado=AREA,
            atende=True,
            justificativa="Área da apólice corresponde à área do evento.",
        ),
    ),
    canal="whatsapp",
    motivo="incluido",
    justificativa="Segurado e apólice atendem integralmente aos critérios da regra ativa.",
)


def test_listar_candidatos_retorna_segurado_e_apolice_da_area(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_segurado = inserir_segurado(caminho, canal="sms", participa=True)
    id_apolice = inserir_apolice(caminho, id_segurado, tipo="residencial")

    candidatos = RepositorioCandidatosElegibilidade(caminho).listar_candidatos(AREA)

    assert len(candidatos) == 1
    candidato = candidatos[0]
    assert str(candidato.segurado_id) == id_segurado
    assert str(candidato.apolice_id) == id_apolice
    assert candidato.canal_preferido == "sms"
    assert candidato.participa_de_alertas is True
    assert candidato.apolice_tipo == "residencial"
    assert candidato.apolice_situacao == "ativa"
    assert candidato.coberturas == ("alagamento",)


def test_listar_candidatos_ignora_apolice_de_outra_area(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_segurado = inserir_segurado(caminho, area="9990002")
    inserir_apolice(caminho, id_segurado, area="9990002")

    candidatos = RepositorioCandidatosElegibilidade(caminho).listar_candidatos(AREA)

    assert candidatos == []


def test_listar_candidatos_com_segurado_e_duas_apolices_devolve_duas_linhas(
    tmp_path: Path,
) -> None:
    """Edge case da spec: mais de uma apólice ativa na área gera candidatos separados."""

    caminho = preparar_banco(tmp_path)
    id_segurado = inserir_segurado(caminho)
    inserir_apolice(caminho, id_segurado, situacao="ativa")
    inserir_apolice(caminho, id_segurado, situacao="cancelada")

    candidatos = RepositorioCandidatosElegibilidade(caminho).listar_candidatos(AREA)

    assert len(candidatos) == 2
    situacoes = {c.apolice_situacao for c in candidatos}
    assert situacoes == {"ativa", "cancelada"}


def test_salvar_persiste_um_resultado_por_combinacao(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_segurado = inserir_segurado(caminho)
    id_apolice = inserir_apolice(caminho, id_segurado)
    id_regra = inserir_regra(caminho)
    id_evento = inserir_evento(caminho)
    execucao_id = uuid4()

    id_registro = RepositorioElegibilidades(caminho).salvar(
        execucao_id, id_evento, id_regra, id_segurado, id_apolice, RESULTADO_INCLUIDO
    )

    assert id_registro is not None
    registro = RepositorioElegibilidades(caminho).obter_por_id(id_registro)
    assert registro is not None
    assert registro.execucao_id == execucao_id
    assert registro.elegivel is True
    assert registro.canal == "whatsapp"
    assert registro.criterios == RESULTADO_INCLUIDO.criterios
    assert registro.nome_segurado == "Pessoa Teste"
    assert registro.codigo_ibge_area == AREA
    assert registro.regra_versao == 1


def test_salvar_chamado_duas_vezes_para_a_mesma_combinacao_nao_duplica(
    tmp_path: Path,
) -> None:
    caminho = preparar_banco(tmp_path)
    id_segurado = inserir_segurado(caminho)
    id_apolice = inserir_apolice(caminho, id_segurado)
    id_regra = inserir_regra(caminho)
    id_evento = inserir_evento(caminho)
    execucao_id = uuid4()
    repo = RepositorioElegibilidades(caminho)

    primeiro = repo.salvar(
        execucao_id, id_evento, id_regra, id_segurado, id_apolice, RESULTADO_INCLUIDO
    )
    segundo = repo.salvar(
        execucao_id, id_evento, id_regra, id_segurado, id_apolice, RESULTADO_INCLUIDO
    )

    assert primeiro is not None
    assert segundo is None
    assert len(repo.listar_por_execucao(execucao_id)) == 1


def test_contar_por_execucao_conta_incluidos_e_excluidos(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)
    id_regra = inserir_regra(caminho)
    id_evento = inserir_evento(caminho)
    execucao_id = uuid4()
    repo = RepositorioElegibilidades(caminho)

    resultado_excluido = ResultadoElegibilidade(
        elegivel=False,
        criterios=(
            Criterio(
                operando="situação da apólice",
                valor_observado="cancelada",
                atende=False,
                justificativa="Apólice não está ativa (situação: cancelada).",
            ),
        ),
        canal="email",
        motivo="apolice_inativa",
        justificativa="Apólice não está ativa (situação: cancelada).",
    )

    id_segurado_1 = inserir_segurado(caminho)
    id_apolice_1 = inserir_apolice(caminho, id_segurado_1)
    repo.salvar(execucao_id, id_evento, id_regra, id_segurado_1, id_apolice_1, RESULTADO_INCLUIDO)

    id_segurado_2 = inserir_segurado(caminho)
    id_apolice_2 = inserir_apolice(caminho, id_segurado_2, situacao="cancelada")
    repo.salvar(execucao_id, id_evento, id_regra, id_segurado_2, id_apolice_2, resultado_excluido)

    contagem = repo.contar_por_execucao(execucao_id)

    assert contagem.incluidos == 1
    assert contagem.excluidos == 1


def test_listar_por_execucao_sem_nenhum_resultado_devolve_lista_vazia(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    assert RepositorioElegibilidades(caminho).listar_por_execucao(uuid4()) == []


def test_obter_por_id_inexistente_devolve_none(tmp_path: Path) -> None:
    caminho = preparar_banco(tmp_path)

    assert RepositorioElegibilidades(caminho).obter_por_id(uuid4()) is None


def test_linhas_semeadas_com_execucao_id_nulo_nao_aparecem_em_listar_por_execucao(
    tmp_path: Path,
) -> None:
    """Linhas semeadas (`execucao_id IS NULL`, migração `0006`) nunca são confundidas
    com o resultado de uma execução real."""

    caminho = tmp_path / "central_preventiva.duckdb"
    ExecutorMigracoes(caminho).aplicar_pendentes()
    id_segurado = inserir_segurado(caminho)
    id_apolice = inserir_apolice(caminho, id_segurado)
    id_regra = inserir_regra(caminho)
    id_evento = inserir_evento(caminho)
    with abrir_conexao(caminho) as conexao:
        conexao.execute(
            "INSERT INTO elegibilidades_historicas "
            "(id, execucao_id, evento_id, regra_id, segurado_id, apolice_id, elegivel, "
            "criterios, canal, justificativa) VALUES "
            "(?, NULL, ?, ?, ?, ?, true, '[]', 'whatsapp', 'seed')",
            [str(uuid4()), id_evento, id_regra, id_segurado, id_apolice],
        )

    assert RepositorioElegibilidades(caminho).listar_por_execucao(uuid4()) == []
