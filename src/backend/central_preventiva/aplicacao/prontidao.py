"""Caso de uso de prontidão das dependências: registro em memória e consulta (GET)."""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

from central_preventiva.aplicacao.portas_prontidao import (
    EstadoDependencia,
    NomeDependencia,
    PortaSonda,
    ResultadoSonda,
)
from central_preventiva.dominio.estados_prontidao import EstadoProntidao

DEPENDENCIAS_EXTERNAS: tuple[NomeDependencia, ...] = ("inmet", "openai")
"""Dependências verificadas por chamada externa real, nunca computadas de forma síncrona."""

CAUSA_CREDENCIAL_AUSENTE = "Credencial ausente."
CAUSA_FALHA_INESPERADA = "Falha inesperada durante a verificação."

_TEXTOS: dict[tuple[NomeDependencia, EstadoProntidao], tuple[str, str]] = {
    ("backend", EstadoProntidao.DISPONIVEL): ("Nenhum.", "Nenhuma ação necessária."),
    ("banco_dados", EstadoProntidao.DISPONIVEL): ("Nenhum.", "Nenhuma ação necessária."),
    ("banco_dados", EstadoProntidao.INDISPONIVEL): (
        "Persistência local indisponível; a demonstração não pode gravar ou consultar dados.",
        "Verifique o banco de dados operacional local e tente novamente.",
    ),
    ("inmet", EstadoProntidao.VERIFICANDO): (
        "Verificação em andamento.",
        "Aguarde a conclusão ou consulte novamente em instantes.",
    ),
    ("inmet", EstadoProntidao.DISPONIVEL): ("Nenhum.", "Nenhuma ação necessária."),
    ("inmet", EstadoProntidao.DEGRADADA): (
        "Dados meteorológicos do INMET podem chegar com atraso durante a demonstração.",
        "Solicite uma nova verificação para confirmar se o INMET normalizou.",
    ),
    ("inmet", EstadoProntidao.INDISPONIVEL): (
        "Funcionalidades que dependem de dados meteorológicos do INMET ficam bloqueadas.",
        "Solicite uma nova verificação mais tarde ou prossiga sem esses dados.",
    ),
    ("openai", EstadoProntidao.VERIFICANDO): (
        "Verificação em andamento.",
        "Aguarde a conclusão ou consulte novamente em instantes.",
    ),
    ("openai", EstadoProntidao.DISPONIVEL): ("Nenhum.", "Nenhuma ação necessária."),
    ("openai", EstadoProntidao.DEGRADADA): (
        "A produção agêntica pode responder com atraso durante a demonstração.",
        "Solicite uma nova verificação para confirmar se a OpenAI normalizou.",
    ),
    ("openai", EstadoProntidao.INDISPONIVEL): (
        "Produção agêntica indisponível.",
        "Defina OPENAI_API_KEY e solicite uma nova verificação.",
    ),
}
_TEXTO_PADRAO = ("Estado inesperado.", "Solicite uma nova verificação.")


def _textos(nome: NomeDependencia, estado: EstadoProntidao) -> tuple[str, str]:
    """Devolve o impacto e a ação disponível padrão para o par dependência/estado."""

    return _TEXTOS.get((nome, estado), _TEXTO_PADRAO)


@dataclass(frozen=True, slots=True)
class PortasProntidao:
    """Agrupa as sondas de que a prontidão depende.

    `openai` é `None` quando não há credencial configurada: a decisão de reportar
    indisponibilidade sem qualquer chamada de rede pertence a esta camada, não à sonda.
    """

    backend: PortaSonda
    banco_dados: PortaSonda
    inmet: PortaSonda
    openai: PortaSonda | None


class RegistroProntidao:
    """Guarda o estado de prontidão das 4 dependências em memória, por processo.

    Recomputável, não persistido: um reinício do processo perde todo o histórico e a
    próxima consulta trata cada dependência como nunca verificada (ver Edge Cases do
    spec). Assume um único processo/worker local; não há coordenação entre processos.
    """

    def __init__(self) -> None:
        """Inicia o registro vazio, com um lock de coordenação por dependência externa."""

        self._estados: dict[NomeDependencia, EstadoDependencia] = {}
        self._chaves_em_voo: dict[NomeDependencia, str] = {}
        self._locks: dict[NomeDependencia, asyncio.Lock] = {
            "inmet": asyncio.Lock(),
            "openai": asyncio.Lock(),
        }

    def obter(self, nome: NomeDependencia) -> EstadoDependencia | None:
        """Devolve o último estado conhecido da dependência, se houver."""

        return self._estados.get(nome)

    def gravar(self, estado: EstadoDependencia) -> None:
        """Grava o estado mais recente conhecido da dependência."""

        self._estados[estado.nome] = estado

    def lock_de(self, nome: NomeDependencia) -> asyncio.Lock:
        """Devolve o lock de coordenação da dependência externa informada."""

        return self._locks[nome]

    def chave_em_voo(self, nome: NomeDependencia) -> str | None:
        """Devolve a chave de idempotência da verificação em andamento, se houver."""

        return self._chaves_em_voo.get(nome)

    def marcar_em_voo(self, nome: NomeDependencia, chave: str) -> None:
        """Registra a chave de idempotência que iniciou a verificação em andamento."""

        self._chaves_em_voo[nome] = chave

    def limpar_em_voo(self, nome: NomeDependencia) -> None:
        """Remove o registro de verificação em andamento ao concluir."""

        self._chaves_em_voo.pop(nome, None)


def _montar_terminal(
    nome: NomeDependencia, resultado: ResultadoSonda, verificado_em: datetime
) -> EstadoDependencia:
    """Monta o estado de exibição de um resultado terminal produzido por uma sonda."""

    impacto, acao = _textos(nome, resultado.estado)
    return EstadoDependencia(
        nome=nome,
        estado=resultado.estado,
        verificado_em=verificado_em,
        causa=resultado.causa,
        impacto=impacto,
        acao_disponivel=acao,
    )


def _montar_verificando(nome: NomeDependencia) -> EstadoDependencia:
    """Monta o estado de exibição de uma dependência com verificação recém-iniciada."""

    impacto, acao = _textos(nome, EstadoProntidao.VERIFICANDO)
    return EstadoDependencia(
        nome=nome,
        estado=EstadoProntidao.VERIFICANDO,
        verificado_em=None,
        causa=None,
        impacto=impacto,
        acao_disponivel=acao,
    )


async def _computar_local(sonda: PortaSonda, nome: NomeDependencia) -> EstadoDependencia:
    """Recomputa uma dependência local (backend/banco_dados) de forma síncrona e inline."""

    resultado = await sonda.verificar()
    return _montar_terminal(nome, resultado, datetime.now(UTC))


async def _executar_sonda(
    sonda: PortaSonda, registro: RegistroProntidao, nome: NomeDependencia
) -> None:
    """Executa a sonda em segundo plano e grava o estado terminal resultante.

    Uma exceção não mapeada nunca deixa a dependência presa em `VERIFICANDO` (NFR11):
    é capturada aqui e traduzida em `INDISPONIVEL` com uma causa genérica.
    """

    try:
        resultado = await sonda.verificar()
    except Exception:
        resultado = ResultadoSonda(
            estado=EstadoProntidao.INDISPONIVEL, causa=CAUSA_FALHA_INESPERADA, latencia_ms=None
        )
    registro.gravar(_montar_terminal(nome, resultado, datetime.now(UTC)))
    registro.limpar_em_voo(nome)


async def _obter_ou_iniciar_externa(
    portas: PortasProntidao, registro: RegistroProntidao, nome: NomeDependencia
) -> EstadoDependencia:
    """Devolve o estado já conhecido de uma dependência externa ou inicia sua verificação."""

    async with registro.lock_de(nome):
        existente = registro.obter(nome)
        if existente is not None:
            return existente

        sonda = portas.inmet if nome == "inmet" else portas.openai
        if sonda is None:
            estado = _montar_terminal(
                nome,
                ResultadoSonda(
                    estado=EstadoProntidao.INDISPONIVEL,
                    causa=CAUSA_CREDENCIAL_AUSENTE,
                    latencia_ms=None,
                ),
                datetime.now(UTC),
            )
            registro.gravar(estado)
            return estado

        estado = _montar_verificando(nome)
        registro.gravar(estado)
        asyncio.create_task(_executar_sonda(sonda, registro, nome))
        return estado


async def consultar_prontidao(
    portas: PortasProntidao, registro: RegistroProntidao
) -> tuple[EstadoDependencia, EstadoDependencia, EstadoDependencia, EstadoDependencia]:
    """Devolve o snapshot atual das 4 dependências, iniciando sondas externas pendentes.

    Backend e banco de dados são recomputados de forma síncrona a cada chamada; nunca
    passam por `VERIFICANDO`. INMET e OpenAI, na primeira consulta sem estado registrado,
    disparam a sonda em segundo plano e retornam `VERIFICANDO`; chamadas seguintes só
    leem o último estado conhecido em memória.
    """

    backend = await _computar_local(portas.backend, "backend")
    banco_dados = await _computar_local(portas.banco_dados, "banco_dados")
    inmet = await _obter_ou_iniciar_externa(portas, registro, "inmet")
    openai = await _obter_ou_iniciar_externa(portas, registro, "openai")
    return (backend, banco_dados, inmet, openai)
