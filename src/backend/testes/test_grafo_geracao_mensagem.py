"""Testes do grafo de uma mensagem: `gerar` (3.2), `criticar` (3.3) e o ciclo de 3.4.

O grafo compilado é exercitado de ponta a ponta com dublês: redator e crítico são sempre
falsos, então nenhum teste aqui chama a OpenAI real. A persistência entra pelo `CicloFalso`,
um modelo em memória do que os repositórios manteriam — os testes afirmam o estado alcançado
pela mensagem, não apenas a chamada feita.
"""

import asyncio
from typing import Any
from uuid import UUID

from central_preventiva.adaptadores.ia.agente_redator import RespostaRedator
from central_preventiva.aplicacao._retry import MAXIMO_TENTATIVAS
from central_preventiva.aplicacao.grafos.geracao_mensagem import (
    CAUSA_SAIDA_CRITICA_INVALIDA,
    MAXIMO_TENTATIVAS_MENSAGEM,
    DependenciasGrafo,
    DesfechoCritica,
    DesfechoGeracao,
    EstadoGrafoMensagem,
    ResultadoCritica,
    ResultadoGeracao,
    construir_grafo,
)
from central_preventiva.dominio.avaliacao_critica import (
    AvaliacaoCritica,
    CategoriaCritica,
    MotivoCritica,
)
from central_preventiva.dominio.estados_mensagem import (
    EstadoMensagem,
    eh_terminal_mensagem,
)
from central_preventiva.dominio.montador_contexto_agente import ContextoAgente
from central_preventiva.dominio.validador_saida_canal import (
    Canal,
    LimitesCanal,
    SaidaCanal,
    ValidadorSaidaCanal,
)

LIMITES = LimitesCanal(whatsapp=1024, sms=160, assunto_email=78, corpo_email=2000)

MENSAGEM_ID = UUID("aaaaaaaa-0000-0000-0000-000000000001")

CONTEXTO = ContextoAgente(
    evento="chuva_intensa",
    localizacao_aproximada="4314902",
    coberturas_relevantes=("alagamento",),
    canal="sms",
    orientacoes_seguranca=("Evite áreas alagadas.",),
)

CORPO_VALIDO = "Chuva forte prevista na sua região hoje. Evite áreas alagadas."


class RedatorFalso:
    """Dublê do agente redator: devolve respostas combinadas ou levanta erro de transporte."""

    def __init__(
        self, respostas: list[RespostaRedator] | None = None, erro: Exception | None = None
    ) -> None:
        self._respostas = respostas or []
        self._erro = erro
        self.chamadas = 0
        self.motivos_recebidos: list[tuple[MotivoCritica, ...]] = []

    @property
    def modelo(self) -> str:
        return "gpt-4o-mini"

    async def gerar(
        self,
        contexto: ContextoAgente,
        canal: Canal,
        motivos_anteriores: tuple[MotivoCritica, ...] = (),
    ) -> RespostaRedator:
        self.chamadas += 1
        self.motivos_recebidos.append(motivos_anteriores)
        if self._erro is not None:
            raise self._erro
        return self._respostas[min(self.chamadas - 1, len(self._respostas) - 1)]


class CriticoFalso:
    """Dublê do agente crítico: devolve avaliações combinadas ou erro de transporte."""

    def __init__(
        self,
        avaliacoes: list[AvaliacaoCritica | None] | None = None,
        erro: Exception | None = None,
    ) -> None:
        self._avaliacoes: list[AvaliacaoCritica | None] = (
            avaliacoes if avaliacoes is not None else [AvaliacaoCritica(True, ())]
        )
        self._erro = erro
        self.chamadas = 0
        self.conteudos: list[SaidaCanal] = []
        self.contextos: list[ContextoAgente] = []

    @property
    def modelo(self) -> str:
        return "gpt-4o-mini"

    async def avaliar(
        self, conteudo: SaidaCanal, canal: Canal, contexto: ContextoAgente
    ) -> AvaliacaoCritica | None:
        self.chamadas += 1
        self.conteudos.append(conteudo)
        self.contextos.append(contexto)
        if self._erro is not None:
            raise self._erro
        return self._avaliacoes[min(self.chamadas - 1, len(self._avaliacoes) - 1)]


class CicloFalso:
    """Modelo em memória dos marcos duráveis de uma mensagem (o que os repositórios fariam).

    Guarda o estado de conteúdo, a tentativa reservada, uma versão por tentativa, as
    avaliações persistidas e as exceções registradas. Recusa, como o banco recusaria,
    escrever sobre um estado terminal ou reservar uma quarta tentativa.
    """

    def __init__(self) -> None:
        self.estado = EstadoMensagem.GERANDO
        self.tentativa_atual = 1
        self.versoes: list[tuple[int, ResultadoGeracao]] = []
        self.avaliacoes: list[tuple[int, ResultadoCritica]] = []
        self.excecoes: list[tuple[str, int, tuple[MotivoCritica, ...]]] = []
        self.mensagens_recebidas: list[UUID] = []

    def registrar_geracao(
        self, mensagem_id: UUID, tentativa: int, resultado: ResultadoGeracao
    ) -> None:
        self._garantir_aberta(mensagem_id)
        if resultado.desfecho is DesfechoGeracao.FALHOU_INTEGRACAO_IA:
            self.excecoes.append(("falha_integracao_ia", tentativa, ()))
            self.estado = EstadoMensagem.FALHOU_INTEGRACAO_IA
            return
        self.versoes.append((tentativa, resultado))
        if resultado.desfecho is DesfechoGeracao.VALIDA:
            self.estado = EstadoMensagem.CRITICANDO

    def registrar_critica(
        self, mensagem_id: UUID, tentativa: int, critica: ResultadoCritica
    ) -> None:
        self._garantir_aberta(mensagem_id)
        if critica.desfecho is DesfechoCritica.FALHOU_INTEGRACAO_IA:
            self.excecoes.append(("falha_integracao_ia_critica", tentativa, ()))
            self.estado = EstadoMensagem.FALHOU_INTEGRACAO_IA
            return
        if critica.desfecho is DesfechoCritica.SAIDA_INVALIDA:
            return
        self.avaliacoes.append((tentativa, critica))
        if critica.desfecho is DesfechoCritica.APROVADA:
            self.estado = EstadoMensagem.AGUARDANDO_REVISAO

    def preparar_regeneracao(self, mensagem_id: UUID) -> int:
        self._garantir_aberta(mensagem_id)
        assert self.tentativa_atual < MAXIMO_TENTATIVAS_MENSAGEM, (
            "o grafo tentou reservar uma quarta tentativa"
        )
        self.tentativa_atual += 1
        self.estado = EstadoMensagem.GERANDO
        return self.tentativa_atual

    def esgotar_tentativas(
        self, mensagem_id: UUID, tentativa: int, motivos: tuple[MotivoCritica, ...]
    ) -> None:
        self._garantir_aberta(mensagem_id)
        self.excecoes.append(("falhou_conteudo", tentativa, motivos))
        self.estado = EstadoMensagem.FALHOU_CONTEUDO

    def _garantir_aberta(self, mensagem_id: UUID) -> None:
        self.mensagens_recebidas.append(mensagem_id)
        assert not eh_terminal_mensagem(self.estado), (
            f"o grafo escreveu sobre o terminal '{self.estado}'"
        )


async def sem_espera(_: float) -> None:
    """Substitui o backoff real para que o teste não durma de fato."""


def rodar(
    redator: RedatorFalso,
    critico: CriticoFalso,
    canal: Canal = Canal.SMS,
    ciclo: CicloFalso | None = None,
) -> dict[str, Any]:
    """Roda o grafo compilado uma vez e devolve o estado final completo."""

    grafo = construir_grafo(
        DependenciasGrafo(
            redator=redator,
            validador=ValidadorSaidaCanal(LIMITES),
            critico=critico,
            esperar=sem_espera,
        )
    )
    estado: EstadoGrafoMensagem = {
        "contexto": CONTEXTO,
        "canal": canal,
        "tentativa": 1,
        "mensagem_id": MENSAGEM_ID,
        "ciclo": ciclo if ciclo is not None else CicloFalso(),
    }
    final: Any = asyncio.run(grafo.ainvoke(estado))
    return final


def executar(redator: RedatorFalso, canal: Canal = Canal.SMS) -> ResultadoGeracao:
    """Roda o grafo compilado uma vez e devolve o resultado do nó `gerar`."""

    resultado = rodar(redator, CriticoFalso(), canal)["resultado"]
    assert isinstance(resultado, ResultadoGeracao)
    return resultado


def criticar(
    critico: CriticoFalso, corpo: str = CORPO_VALIDO, canal: Canal = Canal.SMS
) -> ResultadoCritica:
    """Roda o grafo com uma geração válida e devolve o resultado do nó `criticar`."""

    redator = RedatorFalso([RespostaRedator(SaidaCanal(corpo=corpo), 120, 40)])
    resultado = rodar(redator, critico, canal)["resultado_critica"]
    assert isinstance(resultado, ResultadoCritica)
    return resultado


def reprovacao(justificativa: str = "O texto usa tom alarmista.") -> AvaliacaoCritica:
    """Reprovação do crítico com um motivo categorizado, o formato exigido por CRIT-06."""

    return AvaliacaoCritica(
        aprovada=False, motivos=(MotivoCritica(CategoriaCritica.TOM, justificativa),)
    )


APROVACAO = AvaliacaoCritica(aprovada=True, motivos=())


def test_sucesso_na_primeira_chamada_com_saida_valida_devolve_desfecho_valido() -> None:
    """GERAR-05: uma chamada de transporte bem-sucedida com saída válida encerra o nó."""

    redator = RedatorFalso([RespostaRedator(SaidaCanal(corpo=CORPO_VALIDO), 120, 40)])

    resultado = executar(redator)

    assert redator.chamadas == 1
    assert resultado.desfecho is DesfechoGeracao.VALIDA
    assert resultado.saida == SaidaCanal(corpo=CORPO_VALIDO)
    assert resultado.motivo is None
    assert resultado.modelo == "gpt-4o-mini"
    assert resultado.tokens_entrada == 120
    assert resultado.tokens_saida == 40
    assert resultado.duracao_ms > 0


def test_falha_de_transporte_esgotada_devolve_falhou_integracao_ia_sem_excecao() -> None:
    """GERAR-05: tentativas de transporte esgotadas viram desfecho, nunca exceção não tratada."""

    redator = RedatorFalso(erro=TimeoutError("conexão expirou"))

    resultado = executar(redator)

    assert redator.chamadas == MAXIMO_TENTATIVAS
    assert resultado.desfecho is DesfechoGeracao.FALHOU_INTEGRACAO_IA
    assert resultado.saida is None
    assert resultado.motivo == "TimeoutError: conexão expirou"
    assert resultado.tokens_entrada is None
    assert resultado.tokens_saida is None


def test_falha_de_transporte_intermitente_ainda_gera_saida_valida() -> None:
    """A política de tentativas é a mesma de 2.2/3.1: falha momentânea não condena a mensagem."""

    class RedatorInstavel(RedatorFalso):
        async def gerar(
            self,
            contexto: ContextoAgente,
            canal: Canal,
            motivos_anteriores: tuple[MotivoCritica, ...] = (),
        ) -> RespostaRedator:
            self.chamadas += 1
            if self.chamadas == 1:
                raise TimeoutError("conexão expirou")
            return RespostaRedator(SaidaCanal(corpo=CORPO_VALIDO), 10, 5)

    redator = RedatorInstavel()

    resultado = executar(redator)

    assert redator.chamadas == 2
    assert resultado.desfecho is DesfechoGeracao.VALIDA


def test_saida_acima_do_limite_devolve_desfecho_invalido_com_motivo() -> None:
    """GERAR-09: saída acima do limite do canal é inválida, com motivo persistível."""

    redator = RedatorFalso([RespostaRedator(SaidaCanal(corpo="a" * 161), 100, 60)])

    resultado = executar(redator)

    assert resultado.desfecho is DesfechoGeracao.INVALIDA
    assert resultado.motivo == "limite_excedido:corpo:161:160"
    assert resultado.tokens_entrada == 100
    assert resultado.tokens_saida == 60


def test_saida_estruturalmente_vazia_devolve_desfecho_invalido_com_motivo() -> None:
    """GERAR-09: corpo em branco é campo obrigatório ausente, não sucesso."""

    redator = RedatorFalso([RespostaRedator(SaidaCanal(corpo="   "), 100, 2)])

    resultado = executar(redator)

    assert resultado.desfecho is DesfechoGeracao.INVALIDA
    assert resultado.motivo == "campo_obrigatorio_ausente:corpo"


def test_saida_ausente_devolve_desfecho_invalido_com_motivo() -> None:
    """GERAR-09: resposta sem conteúdo estruturado é inválida, não falha de integração."""

    redator = RedatorFalso([RespostaRedator(None, 100, 0)])

    resultado = executar(redator)

    assert resultado.desfecho is DesfechoGeracao.INVALIDA
    assert resultado.motivo == "saida_ausente"


def test_email_sem_assunto_devolve_desfecho_invalido() -> None:
    """GERAR-09: o veredito do canal e-mail vale igual dentro do grafo."""

    redator = RedatorFalso([RespostaRedator(SaidaCanal(corpo=CORPO_VALIDO, assunto=""), 1, 1)])

    resultado = executar(redator, Canal.EMAIL)

    assert resultado.desfecho is DesfechoGeracao.INVALIDA
    assert resultado.motivo == "campo_obrigatorio_ausente:assunto"


def test_saida_aprovada_pelo_critico_devolve_desfecho_aprovado_sem_motivos() -> None:
    """CRIT-05: aprovação do crítico é um desfecho próprio, com motivos vazios."""

    critico = CriticoFalso([AvaliacaoCritica(aprovada=True, motivos=())])

    resultado = criticar(critico)

    assert critico.chamadas == 1
    assert resultado.desfecho is DesfechoCritica.APROVADA
    assert resultado.motivos == ()
    assert resultado.causa is None
    assert resultado.modelo == "gpt-4o-mini"
    assert resultado.duracao_ms > 0


def test_saida_reprovada_devolve_motivos_estruturados_por_categoria() -> None:
    """CRIT-06: a reprovação carrega os motivos categorizados, não só a decisão."""

    critico = CriticoFalso(
        [
            AvaliacaoCritica(
                aprovada=False,
                motivos=(
                    MotivoCritica(CategoriaCritica.TOM, "O texto usa tom alarmista."),
                    MotivoCritica(
                        CategoriaCritica.PROMESSA_INDEVIDA, "Promete indenização integral."
                    ),
                ),
            )
        ]
    )

    resultado = criticar(critico)

    assert resultado.desfecho is DesfechoCritica.REPROVADA
    assert resultado.motivos == (
        MotivoCritica(CategoriaCritica.TOM, "O texto usa tom alarmista."),
        MotivoCritica(CategoriaCritica.PROMESSA_INDEVIDA, "Promete indenização integral."),
    )
    assert resultado.causa is None


def test_saida_do_critico_nao_interpretavel_e_falha_da_tentativa_nunca_aprovacao() -> None:
    """CRIT-07: saída inválida não vira aprovação nem reprovação estruturada."""

    critico = CriticoFalso([None])

    resultado = criticar(critico)

    assert resultado.desfecho is DesfechoCritica.SAIDA_INVALIDA
    assert resultado.desfecho is not DesfechoCritica.APROVADA
    assert resultado.motivos == ()
    assert resultado.causa == CAUSA_SAIDA_CRITICA_INVALIDA


def test_falha_de_transporte_da_critica_esgotada_devolve_falhou_integracao_ia() -> None:
    """Edge case da spec: falha de transporte do crítico segue o padrão de 3.2, sem
    terminal novo, e nunca é confundida com uma saída inválida de conteúdo."""

    critico = CriticoFalso(erro=TimeoutError("conexão expirou"))

    resultado = criticar(critico)

    assert critico.chamadas == MAXIMO_TENTATIVAS
    assert resultado.desfecho is DesfechoCritica.FALHOU_INTEGRACAO_IA
    assert resultado.motivos == ()
    assert resultado.causa == "TimeoutError: conexão expirou"


def test_falha_de_transporte_intermitente_da_critica_ainda_produz_avaliacao() -> None:
    """A política de tentativas do crítico é a mesma do redator: falha momentânea não
    condena a avaliação."""

    class CriticoInstavel(CriticoFalso):
        async def avaliar(
            self, conteudo: SaidaCanal, canal: Canal, contexto: ContextoAgente
        ) -> AvaliacaoCritica | None:
            self.chamadas += 1
            if self.chamadas == 1:
                raise TimeoutError("conexão expirou")
            return AvaliacaoCritica(aprovada=True, motivos=())

    critico = CriticoInstavel()

    resultado = criticar(critico)

    assert critico.chamadas == 2
    assert resultado.desfecho is DesfechoCritica.APROVADA


def test_grafo_nao_invoca_o_critico_para_saida_invalida_do_redator() -> None:
    """CRIT-04: uma mensagem já reprovada deterministicamente por 3.2 nunca chega ao
    crítico — o modelo não tem como sobrepor a validação objetiva, porque não é chamado."""

    redator = RedatorFalso([RespostaRedator(SaidaCanal(corpo="a" * 161), 100, 60)])
    critico = CriticoFalso([AvaliacaoCritica(aprovada=True, motivos=())])

    final = rodar(redator, critico)

    assert final["resultado"].desfecho is DesfechoGeracao.INVALIDA
    assert critico.chamadas == 0
    assert "resultado_critica" not in final


def test_grafo_nao_invoca_o_critico_quando_a_geracao_falha_por_transporte() -> None:
    """CRIT-04: sem saída gerada não há conteúdo a avaliar; o crítico não é chamado."""

    redator = RedatorFalso(erro=TimeoutError("conexão expirou"))
    critico = CriticoFalso()

    final = rodar(redator, critico)

    assert final["resultado"].desfecho is DesfechoGeracao.FALHOU_INTEGRACAO_IA
    assert critico.chamadas == 0
    assert "resultado_critica" not in final


def test_critico_recebe_exatamente_o_texto_gerado_e_o_contexto_minimo() -> None:
    """CRIT-01: o crítico recebe a mensagem validada e o mesmo contexto mínimo de 3.1."""

    critico = CriticoFalso()

    criticar(critico, corpo=CORPO_VALIDO)

    assert critico.conteudos == [SaidaCanal(corpo=CORPO_VALIDO)]
    assert critico.contextos == [CONTEXTO]


def test_reprovacao_com_tentativa_disponivel_regenera_com_os_motivos_da_reprovacao() -> None:
    """REGEN-01: reprovado o crítico na tentativa 1, o redator é chamado de novo recebendo
    os motivos daquela reprovação, e a versão anterior permanece registrada e intacta."""

    redator = RedatorFalso([RespostaRedator(SaidaCanal(corpo=CORPO_VALIDO), 120, 40)])
    critico = CriticoFalso([reprovacao("O texto usa tom alarmista."), APROVACAO])
    ciclo = CicloFalso()

    rodar(redator, critico, ciclo=ciclo)

    assert redator.chamadas == 2
    assert redator.motivos_recebidos == [
        (),
        (MotivoCritica(CategoriaCritica.TOM, "O texto usa tom alarmista."),),
    ]
    assert ciclo.tentativa_atual == 2
    assert [tentativa for tentativa, _ in ciclo.versoes] == [1, 2]
    assert ciclo.estado is EstadoMensagem.AGUARDANDO_REVISAO
    assert ciclo.excecoes == []


def test_reprovacao_deterministica_regenera_com_o_motivo_da_validacao_de_canal() -> None:
    """REGEN-01: a reprovação recuperável da validação determinística também consome a
    tentativa e alimenta a regeneração com o motivo estrutural, não só a do crítico."""

    redator = RedatorFalso(
        [
            RespostaRedator(SaidaCanal(corpo="a" * 161), 100, 60),
            RespostaRedator(SaidaCanal(corpo=CORPO_VALIDO), 100, 40),
        ]
    )
    ciclo = CicloFalso()

    rodar(redator, CriticoFalso([APROVACAO]), ciclo=ciclo)

    assert redator.chamadas == 2
    assert redator.motivos_recebidos[1] == (
        MotivoCritica(CategoriaCritica.ADEQUACAO_CANAL, "limite_excedido:corpo:161:160"),
    )
    assert ciclo.tentativa_atual == 2
    assert ciclo.estado is EstadoMensagem.AGUARDANDO_REVISAO


def test_aprovacao_na_primeira_tentativa_encerra_o_ciclo_sem_regenerar() -> None:
    """REGEN-03: aprovação válida encerra o item imediatamente, sem consumir tentativa."""

    redator = RedatorFalso([RespostaRedator(SaidaCanal(corpo=CORPO_VALIDO), 120, 40)])
    ciclo = CicloFalso()

    rodar(redator, CriticoFalso([APROVACAO]), ciclo=ciclo)

    assert redator.chamadas == 1
    assert ciclo.tentativa_atual == 1
    assert [tentativa for tentativa, _ in ciclo.avaliacoes] == [1]
    assert ciclo.estado is EstadoMensagem.AGUARDANDO_REVISAO
    assert ciclo.excecoes == []


def test_aprovacao_na_segunda_tentativa_encerra_sem_gastar_a_terceira() -> None:
    """REGEN-03: o ciclo para na aprovação, mesmo com uma tentativa ainda disponível."""

    redator = RedatorFalso([RespostaRedator(SaidaCanal(corpo=CORPO_VALIDO), 120, 40)])
    critico = CriticoFalso([reprovacao(), APROVACAO])
    ciclo = CicloFalso()

    rodar(redator, critico, ciclo=ciclo)

    assert redator.chamadas == 2
    assert critico.chamadas == 2
    assert ciclo.tentativa_atual == 2
    assert ciclo.estado is EstadoMensagem.AGUARDANDO_REVISAO
    assert ciclo.excecoes == []


def test_aprovacao_na_terceira_tentativa_encerra_em_aguardando_revisao() -> None:
    """Teste independente da spec (P1): reprovando as duas primeiras e aprovando a terceira,
    3 versões ficam persistidas, a mensagem alcança `aguardando_revisao` e nenhuma quarta
    tentativa é disparada."""

    redator = RedatorFalso([RespostaRedator(SaidaCanal(corpo=CORPO_VALIDO), 120, 40)])
    critico = CriticoFalso([reprovacao(), reprovacao(), APROVACAO])
    ciclo = CicloFalso()

    rodar(redator, critico, ciclo=ciclo)

    assert redator.chamadas == 3
    assert [tentativa for tentativa, _ in ciclo.versoes] == [1, 2, 3]
    assert ciclo.tentativa_atual == 3
    assert ciclo.estado is EstadoMensagem.AGUARDANDO_REVISAO
    assert ciclo.excecoes == []


def test_terceira_reprovacao_do_critico_leva_a_falhou_conteudo_sem_quarta_tentativa() -> None:
    """REGEN-02, REGEN-04: com três reprovações, o redator é chamado exatamente três vezes,
    a mensagem alcança `falhou_conteudo` e a `Exceção` carrega os motivos categorizados."""

    redator = RedatorFalso([RespostaRedator(SaidaCanal(corpo=CORPO_VALIDO), 120, 40)])
    critico = CriticoFalso([reprovacao("Promete indenização integral.")])
    ciclo = CicloFalso()

    rodar(redator, critico, ciclo=ciclo)

    assert redator.chamadas == MAXIMO_TENTATIVAS_MENSAGEM
    assert critico.chamadas == MAXIMO_TENTATIVAS_MENSAGEM
    assert ciclo.tentativa_atual == 3
    assert [tentativa for tentativa, _ in ciclo.versoes] == [1, 2, 3]
    assert ciclo.estado is EstadoMensagem.FALHOU_CONTEUDO
    assert ciclo.excecoes == [
        (
            "falhou_conteudo",
            3,
            (MotivoCritica(CategoriaCritica.TOM, "Promete indenização integral."),),
        )
    ]


def test_terceira_reprovacao_deterministica_leva_ao_mesmo_falhou_conteudo() -> None:
    """Primeiro Edge Case da spec: reprovada na tentativa 3 por falha determinística, o
    terminal é o mesmo `falhou_conteudo` — a fonte da reprovação não muda o estado final."""

    redator = RedatorFalso([RespostaRedator(SaidaCanal(corpo="   "), 100, 2)])
    critico = CriticoFalso([APROVACAO])
    ciclo = CicloFalso()

    rodar(redator, critico, ciclo=ciclo)

    assert redator.chamadas == MAXIMO_TENTATIVAS_MENSAGEM
    assert critico.chamadas == 0
    assert ciclo.estado is EstadoMensagem.FALHOU_CONTEUDO
    assert ciclo.excecoes == [
        (
            "falhou_conteudo",
            3,
            (
                MotivoCritica(
                    CategoriaCritica.ADEQUACAO_CANAL, "campo_obrigatorio_ausente:corpo"
                ),
            ),
        )
    ]


def test_saida_nao_interpretavel_do_critico_consome_tentativa_ate_falhou_conteudo() -> None:
    """CRIT-07 + REGEN-04: saída do crítico não interpretável nunca é aprovação e consome a
    tentativa como qualquer reprovação; três delas fecham o item em `falhou_conteudo`, sem
    nenhuma avaliação persistida."""

    redator = RedatorFalso([RespostaRedator(SaidaCanal(corpo=CORPO_VALIDO), 120, 40)])
    critico = CriticoFalso([None])
    ciclo = CicloFalso()

    rodar(redator, critico, ciclo=ciclo)

    assert critico.chamadas == MAXIMO_TENTATIVAS_MENSAGEM
    assert ciclo.avaliacoes == []
    assert ciclo.estado is EstadoMensagem.FALHOU_CONTEUDO


def test_falha_de_transporte_da_geracao_encerra_em_falhou_integracao_sem_regenerar() -> None:
    """REGEN-05: transporte esgotado na geração leva a `falhou_integracao_ia`, distinto de
    `falhou_conteudo`, e não consome nenhuma regeneração."""

    redator = RedatorFalso(erro=TimeoutError("conexão expirou"))
    ciclo = CicloFalso()

    rodar(redator, CriticoFalso(), ciclo=ciclo)

    assert ciclo.estado is EstadoMensagem.FALHOU_INTEGRACAO_IA
    assert ciclo.estado is not EstadoMensagem.FALHOU_CONTEUDO
    assert ciclo.tentativa_atual == 1
    assert ciclo.versoes == []
    assert [causa for causa, _, _ in ciclo.excecoes] == ["falha_integracao_ia"]


def test_falha_de_transporte_da_critica_na_terceira_tentativa_e_falhou_integracao() -> None:
    """Segundo Edge Case da spec: a falha de integração durante a própria terceira tentativa
    leva a `falhou_integracao_ia`, não a `falhou_conteudo` — os terminais permanecem
    distintos por causa."""

    redator = RedatorFalso([RespostaRedator(SaidaCanal(corpo=CORPO_VALIDO), 120, 40)])

    class CriticoQueFalhaNaTerceira(CriticoFalso):
        async def avaliar(
            self, conteudo: SaidaCanal, canal: Canal, contexto: ContextoAgente
        ) -> AvaliacaoCritica | None:
            self.chamadas += 1
            if self.chamadas > 2:
                raise TimeoutError("conexão expirou")
            return reprovacao()

    critico = CriticoQueFalhaNaTerceira()
    ciclo = CicloFalso()

    rodar(redator, critico, ciclo=ciclo)

    assert ciclo.tentativa_atual == 3
    assert ciclo.estado is EstadoMensagem.FALHOU_INTEGRACAO_IA
    assert ciclo.estado is not EstadoMensagem.FALHOU_CONTEUDO
    assert [causa for causa, _, _ in ciclo.excecoes] == ["falha_integracao_ia_critica"]


def test_ciclo_recebe_sempre_o_identificador_da_mensagem_em_curso() -> None:
    """REGEN-04: todo marco durável do ciclo é correlacionado à mensagem específica, que é
    o que permite a `Exceção` distinguir-se de uma exceção da execução inteira."""

    redator = RedatorFalso([RespostaRedator(SaidaCanal(corpo=CORPO_VALIDO), 120, 40)])
    critico = CriticoFalso([reprovacao()])
    ciclo = CicloFalso()

    rodar(redator, critico, ciclo=ciclo)

    assert ciclo.mensagens_recebidas
    assert set(ciclo.mensagens_recebidas) == {MENSAGEM_ID}
