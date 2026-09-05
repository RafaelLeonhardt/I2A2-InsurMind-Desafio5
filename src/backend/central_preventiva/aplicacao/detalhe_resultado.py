"""Caso de uso do detalhe individual de um resultado de simulação (DETALHE-01..05).

`ServicoDetalheResultado.obter` é uma junção de leitura pura sobre schema já existente de
2.3/2.5/3.2/3.3/3.5/3.6 — nenhuma migração nova, nenhuma escrita. A mensagem precisa pertencer
à `execucao_id` informada: uma mensagem que existe mas é de outra execução devolve exatamente
o mesmo `None` que uma mensagem inexistente (DETALHE-05, AD-011) — o roteador não tem como
distinguir os dois casos e portanto não pode vazar a existência cruzada de um registro.

SPEC_DEVIATION: o `design.md` lista `RepositorioAvaliacoesRisco` como fonte do evento e da
versão da regra. O evento completo (tipo, área, intensidade, período, proveniência) já vem de
`RepositorioEventosMeteorologicos.buscar_por_id` e a versão da regra já é um campo direto de
`RegistroElegibilidade` (2.5) — nenhum dos dois precisa do snapshot de avaliação de risco, que
traz só os critérios de relevância meteorológica, não pedidos por nenhum AC desta história.
Trocado por `RepositorioEventosMeteorologicos`, já reusado por 3.6 para o mesmo propósito.

SPEC_DEVIATION: o `design.md` não lista `RepositorioExcecoesOperacionais`, mas o Edge Case
"mensagem em exceção... mostra... a exceção associada" exige lê-la por `mensagem_id` — método
novo (`obter_por_mensagem`, extensão do repositório de 2.2/3.4), já que só existia `registrar`.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from central_preventiva.adaptadores.persistencia.repositorio_avaliacoes_criticas import (
    RegistroAvaliacaoCritica,
)
from central_preventiva.adaptadores.persistencia.repositorio_decisoes_humanas import (
    DecisaoHumana,
)
from central_preventiva.adaptadores.persistencia.repositorio_elegibilidade import (
    RegistroElegibilidade,
)
from central_preventiva.adaptadores.persistencia.repositorio_entregas_simuladas import (
    ApresentacaoSimulada,
    EntregaSimulada,
)
from central_preventiva.adaptadores.persistencia.repositorio_execucao_preventiva import (
    RegistroExcecaoOperacional,
)
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    RegistroMensagem,
    VersaoMensagem,
)
from central_preventiva.dominio.estados_mensagem import EstadoMensagem
from central_preventiva.dominio.evento_meteorologico import EventoMeteorologico
from central_preventiva.dominio.validador_saida_canal import Canal, ValidadorSaidaCanal


@dataclass(frozen=True, slots=True)
class VersaoDetalhada:
    """Uma tentativa de geração relacionada à sua avaliação crítica e decisões humanas
    (DETALHE-04): a mensagem com 2 reprovações + 1 aprovação final devolve 3 destas, na
    ordem cronológica em que ocorreram — nenhuma versão histórica é reescrita (AD-11)."""

    versao: VersaoMensagem
    avaliacao_critica: RegistroAvaliacaoCritica | None
    decisoes_humanas: tuple[DecisaoHumana, ...]


@dataclass(frozen=True, slots=True)
class DetalheResultado:
    """Tudo que originou uma mensagem simulada: identidade, conteúdo, origem e decisões."""

    mensagem_id: UUID
    execucao_id: UUID
    canal: Canal
    estado: EstadoMensagem
    limite_canal_corpo: int
    limite_canal_assunto: int | None
    criado_em: datetime
    atualizado_em: datetime
    nome_segurado: str
    apolice_id: UUID
    codigo_ibge_area: str
    evento: EventoMeteorologico | None
    regra_id: UUID
    regra_versao: int
    apresentacao_simulada: ApresentacaoSimulada | None
    versoes: tuple[VersaoDetalhada, ...]
    excecao: RegistroExcecaoOperacional | None


class _RepositorioMensagens(Protocol):
    """Porta mínima de `mensagens`/`versoes_mensagem` (3.2)."""

    def obter(self, mensagem_id: UUID) -> RegistroMensagem | None: ...

    def listar_versoes(self, mensagem_id: UUID) -> list[VersaoMensagem]: ...


class _RepositorioAvaliacoesCriticas(Protocol):
    """Porta mínima de `avaliacoes_criticas` (3.3)."""

    def obter_por_versao(
        self, versao_mensagem_id: UUID
    ) -> RegistroAvaliacaoCritica | None: ...


class _RepositorioDecisoesHumanas(Protocol):
    """Porta mínima de `decisoes_humanas` (3.5)."""

    def obter_por_mensagem(self, mensagem_id: UUID) -> list[DecisaoHumana]: ...


class _RepositorioEntregasSimuladas(Protocol):
    """Porta mínima de `entregas_simuladas` (3.6)."""

    def listar_por_execucao(self, execucao_id: UUID) -> list[EntregaSimulada]: ...


class _RepositorioElegibilidades(Protocol):
    """Porta mínima do público elegível preservado pela execução (2.5)."""

    def obter_por_id(self, id_registro: UUID) -> RegistroElegibilidade | None: ...


class _RepositorioEventos(Protocol):
    """Porta mínima do evento meteorológico referenciado pelo snapshot (2.2)."""

    def buscar_por_id(self, id: UUID) -> EventoMeteorologico | None: ...  # noqa: A002


class _RepositorioExcecoesOperacionais(Protocol):
    """Porta mínima de leitura de `excecoes_operacionais` por mensagem (4.2)."""

    def obter_por_mensagem(self, mensagem_id: UUID) -> RegistroExcecaoOperacional | None: ...


@dataclass(frozen=True, slots=True)
class PortasDetalheResultado:
    """Agrupa as portas de que o detalhe do resultado individual depende."""

    mensagens: _RepositorioMensagens
    avaliacoes: _RepositorioAvaliacoesCriticas
    decisoes: _RepositorioDecisoesHumanas
    entregas: _RepositorioEntregasSimuladas
    elegibilidades: _RepositorioElegibilidades
    eventos: _RepositorioEventos
    excecoes: _RepositorioExcecoesOperacionais
    validador: ValidadorSaidaCanal


class ServicoDetalheResultado:
    """Junta a origem completa de uma mensagem simulada, sem nenhuma escrita."""

    def __init__(self, portas: PortasDetalheResultado) -> None:
        """Guarda as portas de leitura usadas pelo detalhe."""

        self._portas = portas

    def obter(self, execucao_id: UUID, mensagem_id: UUID) -> DetalheResultado | None:
        """Devolve o detalhe completo, ou `None` se a mensagem não existir ou não
        pertencer à `execucao_id` informada (DETALHE-05) — resposta idêntica nos dois
        casos, para nunca revelar que um identificador existe em outro contexto."""

        registro = self._portas.mensagens.obter(mensagem_id)
        if registro is None or registro.execucao_id != execucao_id:
            return None

        elegibilidade = self._portas.elegibilidades.obter_por_id(registro.elegibilidade_id)
        assert elegibilidade is not None, (
            f"elegibilidade {registro.elegibilidade_id} da mensagem {mensagem_id} não encontrada"
        )
        evento = self._portas.eventos.buscar_por_id(elegibilidade.evento_id)

        entregas_execucao = self._portas.entregas.listar_por_execucao(execucao_id)
        apresentacao = next(
            (
                entrega.apresentacao
                for entrega in entregas_execucao
                if entrega.mensagem_id == mensagem_id
            ),
            None,
        )

        decisoes_da_mensagem = self._portas.decisoes.obter_por_mensagem(mensagem_id)
        versoes = tuple(
            VersaoDetalhada(
                versao=versao,
                avaliacao_critica=self._portas.avaliacoes.obter_por_versao(versao.id),
                decisoes_humanas=tuple(
                    decisao
                    for decisao in decisoes_da_mensagem
                    if decisao.versao_mensagem_id == versao.id
                ),
            )
            for versao in self._portas.mensagens.listar_versoes(mensagem_id)
        )

        return DetalheResultado(
            mensagem_id=registro.id,
            execucao_id=registro.execucao_id,
            canal=registro.canal,
            estado=registro.estado,
            limite_canal_corpo=self._portas.validador.limite_corpo(registro.canal),
            limite_canal_assunto=self._portas.validador.limite_assunto(registro.canal),
            criado_em=registro.criado_em,
            atualizado_em=registro.atualizado_em,
            nome_segurado=elegibilidade.nome_segurado,
            apolice_id=elegibilidade.apolice_id,
            codigo_ibge_area=elegibilidade.codigo_ibge_area,
            evento=evento,
            regra_id=elegibilidade.regra_id,
            regra_versao=elegibilidade.regra_versao,
            apresentacao_simulada=apresentacao,
            versoes=versoes,
            excecao=self._portas.excecoes.obter_por_mensagem(mensagem_id)
            if registro.estado
            in (EstadoMensagem.FALHOU_CONTEUDO, EstadoMensagem.FALHOU_INTEGRACAO_IA)
            else None,
        )
