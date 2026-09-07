"""Testes do recurso REST/JSON da revisão humana do lote (REVISAO-01, 12, 13, 14).

O banco é o real, temporário e migrado, e a aplicação é a real: só as chamadas de rede ficam
bloqueadas, para que nenhum teste toque a OpenAI.
"""

from datetime import UTC, datetime
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
from central_preventiva.composicao.api import criar_aplicacao
from central_preventiva.composicao.configuracao import Configuracao
from central_preventiva.dominio.avaliacao_critica import CategoriaCritica, MotivoCritica
from central_preventiva.dominio.avaliador_elegibilidade import OPERANDO_AREA_AFETADA
from central_preventiva.dominio.estados_execucao import EstadoExecucao
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

TIPO_PROBLEMA = "application/problem+json"
EVENTO_ID = UUID("44444444-4444-4444-4444-444444444444")
REGRA_ID = UUID("33333333-3333-3333-3333-333333333333")
AREA = "9990001"
MODELO = "gpt-4o-mini"


@pytest.fixture(autouse=True)
def _bloquear_chamadas_de_rede_reais(monkeypatch: pytest.MonkeyPatch) -> None:
    """Impede qualquer chamada HTTP real: a revisão nunca precisa da OpenAI."""

    async def _send_bloqueado(
        self: httpx.AsyncClient, request: httpx.Request, **_: object
    ) -> httpx.Response:
        raise AssertionError(f"chamada de rede real bloqueada em teste: {request.url}")

    monkeypatch.setattr(httpx.AsyncClient, "send", _send_bloqueado)


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


def semear_evento(caminho: Path) -> None:
    """Semeia o evento meteorológico de origem do lote."""

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


def semear_elegibilidade(caminho: Path, execucao_id: UUID, canal: str, nome: str) -> UUID:
    """Semeia um item incluído do público elegível, no formato que 2.5 persiste."""

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
                '[{"operando": "' + OPERANDO_AREA_AFETADA + '", '
                '"valor_observado": "9990001", "atende": true, '
                '"justificativa": "Área corresponde."}]',
                canal,
                nome,
            ],
        )
    return elegibilidade_id


def semear_mensagem(
    caminho: Path,
    execucao_id: UUID,
    canal: Canal = Canal.SMS,
    nome: str = "Pessoa Teste",
    aprovada_pelo_critico: bool = True,
    estado: EstadoMensagem = EstadoMensagem.AGUARDANDO_REVISAO,
) -> UUID:
    """Semeia uma mensagem com uma tentativa persistida e o estado final indicado."""

    elegibilidade_id = semear_elegibilidade(caminho, execucao_id, canal.value, nome)
    mensagens = RepositorioMensagens(caminho)
    mensagem_id = mensagens.criar(execucao_id, elegibilidade_id, canal)
    versao_id = mensagens.salvar_versao(
        mensagem_id=mensagem_id,
        numero_tentativa=1,
        conteudo=SaidaCanal(
            corpo=f"Chuva forte hoje na sua região, {nome}. Evite áreas alagadas.",
            assunto="Alerta preventivo" if canal is Canal.EMAIL else None,
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
        motivos=()
        if aprovada_pelo_critico
        else (MotivoCritica(CategoriaCritica.TOM, "Tom alarmista."),),
        modelo=MODELO,
        duracao_ms=90.0,
    )
    registro = mensagens.obter(mensagem_id)
    assert registro is not None
    if registro.estado is not estado:
        mensagens.transicionar(mensagem_id, registro.versao, estado)
    return mensagem_id


def criar_execucao(
    caminho: Path, estado: EstadoExecucao = EstadoExecucao.AGUARDANDO_REVISAO
) -> UUID:
    """Cria a execução do lote no estado indicado."""

    return RepositorioExecucaoPreventiva(caminho).criar(estado)


def estado_da_execucao(caminho: Path, execucao_id: UUID) -> EstadoExecucao:
    """Lê o estado agregado persistido da execução."""

    snapshot = RepositorioExecucaoPreventiva(caminho).buscar(execucao_id)
    assert snapshot is not None
    return snapshot.estado


def versao_de(caminho: Path, mensagem_id: UUID) -> int:
    """Lê a versão de concorrência otimista atual da mensagem."""

    registro = RepositorioMensagens(caminho).obter(mensagem_id)
    assert registro is not None
    return registro.versao


def test_get_devolve_o_lote_ordenado_com_todos_os_campos_do_ac(tmp_path: Path) -> None:
    """REVISAO-01/02/03: o `GET` traz cabeçalho e itens com atenção primeiro, e cada item
    expõe destinatário, conteúdo, versões, verificação determinística e avaliação crítica."""

    caminho = preparar_banco(tmp_path)
    semear_evento(caminho)
    execucao_id = criar_execucao(caminho)
    aprovada = semear_mensagem(caminho, execucao_id, Canal.SMS, "Aprovada")
    em_excecao = semear_mensagem(
        caminho,
        execucao_id,
        Canal.EMAIL,
        "Exceção",
        aprovada_pelo_critico=False,
        estado=EstadoMensagem.FALHOU_CONTEUDO,
    )

    resposta = cliente_para(caminho).get(f"/api/v1/execucoes/{execucao_id}/revisao")

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["execucao_id"] == str(execucao_id)
    assert corpo["estado"] == "aguardando_revisao"
    assert corpo["evento"]["id"] == str(EVENTO_ID)
    assert corpo["evento"]["tipo"] == "chuva_intensa"
    assert corpo["regra_id"] == str(REGRA_ID)
    assert corpo["regra_versao"] == 2
    assert corpo["total_publico_incluido"] == 2
    assert corpo["distribuicao_por_canal"] == [
        {"canal": "email", "total": 1},
        {"canal": "sms", "total": 1},
    ]
    assert corpo["aprovacoes_agenticas"] == 1
    assert corpo["itens_em_excecao"] == 1
    assert [item["mensagem_id"] for item in corpo["itens"]] == [
        str(em_excecao),
        str(aprovada),
    ]
    item = corpo["itens"][1]
    assert item["destinatario"]["nome_segurado"] == "Aprovada"
    assert item["destinatario"]["codigo_ibge_area"] == AREA
    assert item["origem"]["evento_id"] == str(EVENTO_ID)
    assert item["origem"]["criterios"][0]["operando"] == OPERANDO_AREA_AFETADA
    assert item["origem"]["criterios"][0]["atende"] is True
    assert item["versoes"][0]["corpo"].startswith("Chuva forte hoje")
    assert item["versoes"][0]["valida"] is True
    assert item["versoes"][0]["avaliacao_critica"]["aprovada"] is True
    assert item["versoes"][0]["avaliacao_critica"]["agente"] == "critico"
    assert item["decidivel"] is True
    assert item["pode_regenerar"] is True
    assert item["limite_tentativas"] == 3


def test_get_de_execucao_inexistente_devolve_404(tmp_path: Path) -> None:
    """AD-011: execução inexistente e execução de outro escopo respondem igual."""

    caminho = preparar_banco(tmp_path)

    resposta = cliente_para(caminho).get(f"/api/v1/execucoes/{uuid4()}/revisao")

    assert resposta.status_code == 404
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "execucao_inexistente"


def test_get_com_identificador_invalido_devolve_422(tmp_path: Path) -> None:
    """Um identificador que não é UUID é erro de requisição, não `404`."""

    resposta = cliente_para(preparar_banco(tmp_path)).get("/api/v1/execucoes/nao-uuid/revisao")

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "execucao_id_invalido"


def test_post_aplica_a_decisao_e_leva_a_execucao_a_aguardando_confirmacao(
    tmp_path: Path,
) -> None:
    """REVISAO-13/14: o envio aplicado consolida o lote e move o agregado."""

    caminho = preparar_banco(tmp_path)
    semear_evento(caminho)
    execucao_id = criar_execucao(caminho)
    aprovada = semear_mensagem(caminho, execucao_id, Canal.SMS, "Aprovada")
    rejeitada = semear_mensagem(caminho, execucao_id, Canal.EMAIL, "Rejeitada")

    resposta = cliente_para(caminho).post(
        f"/api/v1/execucoes/{execucao_id}/revisao/decisoes",
        headers={"Idempotency-Key": "chave-decisao-1"},
        json={
            "decisoes": [
                {
                    "mensagem_id": str(aprovada),
                    "versao_esperada": versao_de(caminho, aprovada),
                    "resultado": "aprovar",
                },
                {
                    "mensagem_id": str(rejeitada),
                    "versao_esperada": versao_de(caminho, rejeitada),
                    "resultado": "rejeitar",
                    "justificativa": "Inadequada para este público.",
                },
            ]
        },
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["estado"] == "aguardando_confirmacao"
    assert corpo["aplicadas"] == [str(aprovada), str(rejeitada)]
    assert corpo["recusadas"] == []
    assert corpo["mensagens_aprovadas"] == [str(aprovada)]
    assert estado_da_execucao(caminho, execucao_id) is EstadoExecucao.AGUARDANDO_CONFIRMACAO


def test_post_com_conflito_de_versao_devolve_409_sem_efeito_parcial(tmp_path: Path) -> None:
    """Teste independente do REVISAO-12: com uma `versao_esperada` desatualizada, o envio
    inteiro é recusado com `409` e o `GET` seguinte prova que nada foi aplicado."""

    caminho = preparar_banco(tmp_path)
    semear_evento(caminho)
    execucao_id = criar_execucao(caminho)
    primeira = semear_mensagem(caminho, execucao_id, Canal.SMS, "Primeira")
    segunda = semear_mensagem(caminho, execucao_id, Canal.EMAIL, "Segunda")
    cliente = cliente_para(caminho)

    resposta = cliente.post(
        f"/api/v1/execucoes/{execucao_id}/revisao/decisoes",
        headers={"Idempotency-Key": "chave-conflito"},
        json={
            "decisoes": [
                {
                    "mensagem_id": str(primeira),
                    "versao_esperada": versao_de(caminho, primeira),
                    "resultado": "aprovar",
                },
                {
                    "mensagem_id": str(segunda),
                    "versao_esperada": versao_de(caminho, segunda) + 5,
                    "resultado": "aprovar",
                },
            ]
        },
    )

    assert resposta.status_code == 409
    assert resposta.headers["content-type"].startswith(TIPO_PROBLEMA)
    assert resposta.json()["codigo"] == "conflito_versao"
    assert str(segunda) in resposta.json()["ocorrencia"]
    lote = cliente.get(f"/api/v1/execucoes/{execucao_id}/revisao").json()
    assert {item["estado"] for item in lote["itens"]} == {"aguardando_revisao"}
    assert all(item["decisoes"] == [] for item in lote["itens"])
    assert lote["estado"] == "aguardando_revisao"


def test_post_sem_justificativa_devolve_422_sem_aplicar_nada(tmp_path: Path) -> None:
    """REVISAO-06: a validação bloqueia o envio antes de qualquer mutação."""

    caminho = preparar_banco(tmp_path)
    semear_evento(caminho)
    execucao_id = criar_execucao(caminho)
    mensagem_id = semear_mensagem(caminho, execucao_id)
    cliente = cliente_para(caminho)

    resposta = cliente.post(
        f"/api/v1/execucoes/{execucao_id}/revisao/decisoes",
        headers={"Idempotency-Key": "chave-sem-motivo"},
        json={
            "decisoes": [
                {
                    "mensagem_id": str(mensagem_id),
                    "versao_esperada": versao_de(caminho, mensagem_id),
                    "resultado": "excluir",
                }
            ]
        },
    )

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "justificativa_obrigatoria"
    lote = cliente.get(f"/api/v1/execucoes/{execucao_id}/revisao").json()
    assert lote["itens"][0]["estado"] == "aguardando_revisao"


def test_post_sem_idempotency_key_devolve_422(tmp_path: Path) -> None:
    """AD-002: todo `POST` mutável exige `Idempotency-Key`."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho)

    resposta = cliente_para(caminho).post(
        f"/api/v1/execucoes/{execucao_id}/revisao/decisoes", json={"decisoes": []}
    )

    assert resposta.status_code == 422
    assert resposta.json()["codigo"] == "idempotency_key_ausente"


def test_post_reenviado_com_a_mesma_chave_devolve_a_resposta_registrada(
    tmp_path: Path,
) -> None:
    """AD-002/REVISAO-08: o reenvio idêntico devolve o mesmo corpo, sem reaplicar nada."""

    caminho = preparar_banco(tmp_path)
    semear_evento(caminho)
    execucao_id = criar_execucao(caminho)
    mensagem_id = semear_mensagem(caminho, execucao_id)
    cliente = cliente_para(caminho)
    corpo = {
        "decisoes": [
            {
                "mensagem_id": str(mensagem_id),
                "versao_esperada": versao_de(caminho, mensagem_id),
                "resultado": "regenerar",
                "justificativa": "Quero outra formulação.",
            }
        ]
    }

    primeira = cliente.post(
        f"/api/v1/execucoes/{execucao_id}/revisao/decisoes",
        headers={"Idempotency-Key": "chave-regenerar"},
        json=corpo,
    )
    segunda = cliente.post(
        f"/api/v1/execucoes/{execucao_id}/revisao/decisoes",
        headers={"Idempotency-Key": "chave-regenerar"},
        json=corpo,
    )

    assert primeira.status_code == 200
    assert segunda.status_code == 200
    assert primeira.json() == segunda.json()
    registro = RepositorioMensagens(caminho).obter(mensagem_id)
    assert registro is not None
    assert registro.tentativa_atual == 2


def test_post_com_a_mesma_chave_em_outra_execucao_devolve_409(tmp_path: Path) -> None:
    """Lição do `f2d9308`: o hash é escopado pelo alvo, então a mesma chave reusada em outra
    execução é conflito, nunca a resposta registrada da primeira."""

    caminho = preparar_banco(tmp_path)
    semear_evento(caminho)
    primeira_execucao = criar_execucao(caminho)
    segunda_execucao = criar_execucao(caminho)
    semear_mensagem(caminho, primeira_execucao, Canal.SMS, "Primeira")
    semear_mensagem(caminho, segunda_execucao, Canal.EMAIL, "Segunda")
    cliente = cliente_para(caminho)
    cliente.post(
        f"/api/v1/execucoes/{primeira_execucao}/revisao/decisoes",
        headers={"Idempotency-Key": "chave-compartilhada"},
        json={"decisoes": []},
    )

    resposta = cliente.post(
        f"/api/v1/execucoes/{segunda_execucao}/revisao/decisoes",
        headers={"Idempotency-Key": "chave-compartilhada"},
        json={"decisoes": []},
    )

    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "conflito_idempotencia"
    assert estado_da_execucao(caminho, segunda_execucao) is EstadoExecucao.AGUARDANDO_REVISAO


def test_post_em_execucao_fora_de_revisao_devolve_409(tmp_path: Path) -> None:
    """Terceiro Edge Case da spec: com regeneração ativa (`processando_mensagens`), nenhuma
    decisão nova é aceita."""

    caminho = preparar_banco(tmp_path)
    execucao_id = criar_execucao(caminho, EstadoExecucao.PROCESSANDO_MENSAGENS)

    resposta = cliente_para(caminho).post(
        f"/api/v1/execucoes/{execucao_id}/revisao/decisoes",
        headers={"Idempotency-Key": "chave-estado"},
        json={"decisoes": []},
    )

    assert resposta.status_code == 409
    assert resposta.json()["codigo"] == "estado_nao_revisavel"


def test_post_em_execucao_inexistente_devolve_404(tmp_path: Path) -> None:
    """AD-011: a resposta é a mesma do `GET` para execução desconhecida."""

    resposta = cliente_para(preparar_banco(tmp_path)).post(
        f"/api/v1/execucoes/{uuid4()}/revisao/decisoes",
        headers={"Idempotency-Key": "chave-inexistente"},
        json={"decisoes": []},
    )

    assert resposta.status_code == 404
    assert resposta.json()["codigo"] == "execucao_inexistente"


def test_post_recusa_item_ja_decidido_sem_impedir_os_demais(tmp_path: Path) -> None:
    """Segundo Edge Case da spec: a recusa do item já decidido vem no corpo da resposta, com
    motivo, e as demais decisões válidas do mesmo envio são aplicadas."""

    caminho = preparar_banco(tmp_path)
    semear_evento(caminho)
    execucao_id = criar_execucao(caminho)
    ja_decidida = semear_mensagem(
        caminho,
        execucao_id,
        Canal.SMS,
        "Já decidida",
        estado=EstadoMensagem.REJEITADA,
    )
    pendente = semear_mensagem(caminho, execucao_id, Canal.EMAIL, "Pendente")

    resposta = cliente_para(caminho).post(
        f"/api/v1/execucoes/{execucao_id}/revisao/decisoes",
        headers={"Idempotency-Key": "chave-ja-decidida"},
        json={
            "decisoes": [
                {
                    "mensagem_id": str(ja_decidida),
                    "versao_esperada": versao_de(caminho, ja_decidida),
                    "resultado": "aprovar",
                },
                {
                    "mensagem_id": str(pendente),
                    "versao_esperada": versao_de(caminho, pendente),
                    "resultado": "aprovar",
                },
            ]
        },
    )

    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["recusadas"] == [
        {"mensagem_id": str(ja_decidida), "motivo": "mensagem_ja_decidida"}
    ]
    assert corpo["aplicadas"] == [str(pendente)]
    assert corpo["estado"] == "aguardando_confirmacao"


def test_post_sem_nenhuma_aprovada_conclui_a_execucao(tmp_path: Path) -> None:
    """REVISAO-13: nenhuma aprovada conclui a execução sem simulação, e os motivos seguem
    consultáveis pelo `GET`."""

    caminho = preparar_banco(tmp_path)
    semear_evento(caminho)
    execucao_id = criar_execucao(caminho)
    mensagem_id = semear_mensagem(caminho, execucao_id)
    cliente = cliente_para(caminho)

    resposta = cliente.post(
        f"/api/v1/execucoes/{execucao_id}/revisao/decisoes",
        headers={"Idempotency-Key": "chave-conclui"},
        json={
            "decisoes": [
                {
                    "mensagem_id": str(mensagem_id),
                    "versao_esperada": versao_de(caminho, mensagem_id),
                    "resultado": "rejeitar",
                    "justificativa": "Não distingue do alerta oficial.",
                }
            ]
        },
    )

    assert resposta.status_code == 200
    assert resposta.json()["estado"] == "concluida"
    assert resposta.json()["mensagens_aprovadas"] == []
    assert estado_da_execucao(caminho, execucao_id) is EstadoExecucao.CONCLUIDA
    lote = cliente.get(f"/api/v1/execucoes/{execucao_id}/revisao").json()
    assert lote["itens"][0]["decisoes"] == [
        {
            "versao_mensagem_id": lote["itens"][0]["versoes"][0]["id"],
            "perfil_responsavel": "administrador",
            "resultado": "rejeitar",
            "justificativa": "Não distingue do alerta oficial.",
            "criado_em": lote["itens"][0]["decisoes"][0]["criado_em"],
        }
    ]
