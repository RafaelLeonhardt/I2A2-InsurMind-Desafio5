"""Repositório DuckDB de `mensagens` e `versoes_mensagem` (GERAR-06, GERAR-09, GERAR-10).

`criar` respeita a `UNIQUE (elegibilidade_id, canal)` da migração `0010`: a segunda criação
para o mesmo par é recusada pelo próprio banco e traduzida em `MensagemJaExiste`, um erro
específico que o caso de uso trata como no-op idempotente (AD-010). Nenhuma checagem
"consulta e depois insere" em Python, que correria.

`transicionar` repete o padrão de concorrência otimista de `RepositorioExecucaoPreventiva`
(AD-008): versão esperada, incremento na mesma instrução e recusa de sair de um terminal.
`incrementar_tentativa` (3.4) repete o mesmo padrão para o contador de tentativas, com o
limite de três cobrado na própria instrução de `UPDATE` (REGEN-02).

SPEC_DEVIATION (História 3.5): o `design.md` da 3.5 lista este repositório como reusado "sem
alteração" (`transicionar`, `incrementar_tentativa`). `obter`, `listar_por_execucao`,
`transicionar` e `incrementar_tentativa` ganharam um parâmetro `conexao` opcional — leitura e
transição passam a aceitar uma conexão já aberta pelo chamador. É o que permite à decisão em
lote aplicar todas as decisões válidas numa única transação (REVISAO-12): uma segunda conexão
ao mesmo arquivo não enxerga a transação aberta da primeira e sobrevive ao `ROLLBACK` dela —
sem o parâmetro, cada método reabriria sua própria conexão e a atomicidade seria impossível.
Mesmo parâmetro opcional já usado por `RepositorioElegibilidades.copiar_para_execucao`
(AD-012); nenhum comportamento muda para os chamadores existentes de 2.2/3.2/3.4, que
continuam sem passar `conexao` (default `None`, mesma conexão própria de sempre).
"""

import json
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import duckdb

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.dominio.estados_mensagem import (
    EstadoMensagem,
    eh_terminal_mensagem,
)
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal


class MensagemJaExiste(RuntimeError):
    """Indica uma segunda mensagem para a mesma elegibilidade e canal (GERAR-06)."""

    def __init__(self, elegibilidade_id: UUID, canal: Canal) -> None:
        """Identifica o par que já tem mensagem, sem expor conteúdo."""

        super().__init__(
            f"A elegibilidade {elegibilidade_id} já tem mensagem no canal '{canal}'."
        )
        self.elegibilidade_id = elegibilidade_id
        self.canal = canal


class ConflitoVersaoMensagem(RuntimeError):
    """Indica que `versao_esperada` não corresponde à versão persistida da mensagem."""

    def __init__(self, mensagem_id: UUID, versao_esperada: int) -> None:
        """Registra a mensagem e a versão esperada que não bateu."""

        super().__init__(
            f"A mensagem {mensagem_id} não está na versão esperada {versao_esperada}."
        )
        self.mensagem_id = mensagem_id
        self.versao_esperada = versao_esperada


LIMITE_TENTATIVAS_MENSAGEM = 3
"""Máximo de tentativas totais por mensagem (REGEN-02; AD-6, automáticas e humanas juntas)."""


class LimiteTentativasExcedido(RuntimeError):
    """Indica que a mensagem já consumiu as três tentativas permitidas (REGEN-02)."""

    def __init__(self, mensagem_id: UUID, tentativa_atual: int) -> None:
        """Registra a mensagem e a tentativa em que ela já está."""

        super().__init__(
            f"A mensagem {mensagem_id} já está na tentativa {tentativa_atual}, o máximo de "
            f"{LIMITE_TENTATIVAS_MENSAGEM} permitido."
        )
        self.mensagem_id = mensagem_id
        self.tentativa_atual = tentativa_atual


class TransicaoMensagemInvalida(RuntimeError):
    """Indica uma tentativa de transicionar uma mensagem já em estado terminal."""

    def __init__(self, mensagem_id: UUID, estado_atual: EstadoMensagem) -> None:
        """Registra a mensagem e seu estado terminal atual."""

        super().__init__(
            f"A mensagem {mensagem_id} está no estado terminal '{estado_atual}' e não "
            "pode ser transicionada."
        )
        self.mensagem_id = mensagem_id
        self.estado_atual = estado_atual


@dataclass(frozen=True, slots=True)
class RegistroMensagem:
    """Uma mensagem persistida, com o vínculo de origem e o estado de conteúdo."""

    id: UUID
    execucao_id: UUID
    elegibilidade_id: UUID
    canal: Canal
    estado: EstadoMensagem
    tentativa_atual: int
    versao: int
    criado_em: datetime
    atualizado_em: datetime


@dataclass(frozen=True, slots=True)
class VersaoMensagem:
    """Uma tentativa de geração persistida, com o veredito e as métricas da chamada."""

    id: UUID
    mensagem_id: UUID
    numero_tentativa: int
    conteudo: SaidaCanal
    valida: bool
    motivo_invalidez: str | None
    duracao_ms: float
    modelo: str
    versao_prompt: str
    tokens_entrada: int | None
    tokens_saida: int | None
    criado_em: datetime


def serializar_saida(saida: SaidaCanal) -> str:
    """Serializa a saída do canal: `{corpo}` ou `{assunto, corpo}` (schema da migração)."""

    conteudo: dict[str, str] = {"corpo": saida.corpo}
    if saida.assunto is not None:
        conteudo["assunto"] = saida.assunto
    return json.dumps(conteudo, ensure_ascii=False)


def desserializar_saida(bruto: str) -> SaidaCanal:
    """Reconstrói a saída do canal a partir do JSON persistido."""

    dados = cast(dict[str, object], json.loads(bruto))
    assunto = dados.get("assunto")
    return SaidaCanal(
        corpo=str(dados.get("corpo", "")),
        assunto=None if assunto is None else str(assunto),
    )


class RepositorioMensagens:
    """Cria mensagens, persiste versões de geração e transiciona o estado de conteúdo."""

    def __init__(self, caminho: Path) -> None:
        """Vincula o repositório ao arquivo operacional do DuckDB."""

        self._caminho = caminho

    @contextmanager
    def _conexao(
        self, conexao: duckdb.DuckDBPyConnection | None
    ) -> Generator[duckdb.DuckDBPyConnection]:
        """Usa a conexão do chamador quando há uma; senão abre e fecha a própria."""

        if conexao is not None:
            yield conexao
            return
        with abrir_conexao(self._caminho) as propria:
            yield propria

    def criar(self, execucao_id: UUID, elegibilidade_id: UUID, canal: Canal) -> UUID:
        """Cria a mensagem em `gerando`, tentativa 1, versão 1.

        A tentativa entra sempre em 1: incrementá-la é responsabilidade da regeneração
        (História 3.4). Uma segunda criação para o mesmo par elegibilidade+canal levanta
        `MensagemJaExiste`, traduzindo a `UNIQUE` do banco em um erro que o chamador
        reconhece (GERAR-06).
        """

        mensagem_id = uuid4()
        try:
            with abrir_conexao(self._caminho) as conexao:
                conexao.execute(
                    "INSERT INTO mensagens "
                    "(id, execucao_id, elegibilidade_id, canal, estado, tentativa_atual, versao) "
                    "VALUES (?, ?, ?, ?, ?, 1, 1)",
                    [
                        mensagem_id,
                        execucao_id,
                        elegibilidade_id,
                        canal.value,
                        EstadoMensagem.GERANDO.value,
                    ],
                )
        except duckdb.ConstraintException as conflito:
            raise MensagemJaExiste(elegibilidade_id, canal) from conflito
        return mensagem_id

    def salvar_versao(
        self,
        mensagem_id: UUID,
        numero_tentativa: int,
        conteudo: SaidaCanal,
        duracao_ms: float,
        modelo: str,
        versao_prompt: str,
        tokens_entrada: int | None,
        tokens_saida: int | None,
        valida: bool,
        motivo_invalidez: str | None,
    ) -> UUID:
        """Persiste a versão da tentativa, válida ou não, com métricas e motivo (GERAR-10).

        Uma versão inválida fica registrada com o motivo para a próxima tentativa
        controlada (3.4); registrar não avança estado nenhum.
        """

        id_versao = uuid4()
        with abrir_conexao(self._caminho) as conexao:
            conexao.execute(
                "INSERT INTO versoes_mensagem "
                "(id, mensagem_id, numero_tentativa, conteudo, valida, motivo_invalidez, "
                "duracao_ms, modelo, versao_prompt, tokens_entrada, tokens_saida) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    id_versao,
                    mensagem_id,
                    numero_tentativa,
                    serializar_saida(conteudo),
                    valida,
                    motivo_invalidez,
                    duracao_ms,
                    modelo,
                    versao_prompt,
                    tokens_entrada,
                    tokens_saida,
                ],
            )
        return id_versao

    def transicionar(
        self,
        mensagem_id: UUID,
        versao_esperada: int,
        novo_estado: EstadoMensagem,
        conexao: duckdb.DuckDBPyConnection | None = None,
    ) -> None:
        """Transiciona a mensagem incrementando a versão sob checagem otimista (AD-008).

        Levanta `TransicaoMensagemInvalida` se o estado atual já for terminal (AD-7:
        terminal nunca reabre) ou `ConflitoVersaoMensagem` se `versao_esperada` não bater;
        em nenhum dos dois casos a linha é mutada.
        """

        with self._conexao(conexao) as ativa:
            atual = ativa.execute(
                "SELECT estado FROM mensagens WHERE id = ?", [mensagem_id]
            ).fetchone()
            assert atual is not None, f"mensagem {mensagem_id} não encontrada"
            estado_atual = EstadoMensagem(str(atual[0]))
            if eh_terminal_mensagem(estado_atual):
                raise TransicaoMensagemInvalida(mensagem_id, estado_atual)

            resultado = ativa.execute(
                "UPDATE mensagens SET estado = ?, versao = versao + 1, "
                "atualizado_em = now() WHERE id = ? AND versao = ? RETURNING versao",
                [novo_estado.value, mensagem_id, versao_esperada],
            ).fetchone()
        if resultado is None:
            raise ConflitoVersaoMensagem(mensagem_id, versao_esperada)

    def incrementar_tentativa(
        self,
        mensagem_id: UUID,
        versao_esperada: int,
        conexao: duckdb.DuckDBPyConnection | None = None,
    ) -> int:
        """Reserva a próxima tentativa da mensagem e devolve o número reservado (REGEN-02).

        Pré-condição de toda reentrada em `gerando` (AD-4): o contador sobe uma vez só, na
        mesma instrução que incrementa a versão de concorrência otimista (AD-008) e que
        cobra o limite de três (`tentativa_atual < 3` no `WHERE`). Cobrar o limite no
        `UPDATE`, e não apenas na leitura anterior, é o que impede duas regenerações
        concorrentes de reservarem a quarta tentativa juntas.

        Levanta `TransicaoMensagemInvalida` se a mensagem já estiver em terminal (AD-7),
        `LimiteTentativasExcedido` se já estiver na terceira tentativa, ou
        `ConflitoVersaoMensagem` se `versao_esperada` não bater. Em nenhum dos três casos a
        linha é mutada.
        """

        with self._conexao(conexao) as ativa:
            atual = ativa.execute(
                "SELECT estado, tentativa_atual FROM mensagens WHERE id = ?", [mensagem_id]
            ).fetchone()
            assert atual is not None, f"mensagem {mensagem_id} não encontrada"
            estado_atual = EstadoMensagem(str(atual[0]))
            if eh_terminal_mensagem(estado_atual):
                raise TransicaoMensagemInvalida(mensagem_id, estado_atual)
            tentativa_atual = int(atual[1])
            if tentativa_atual >= LIMITE_TENTATIVAS_MENSAGEM:
                raise LimiteTentativasExcedido(mensagem_id, tentativa_atual)

            resultado = ativa.execute(
                "UPDATE mensagens SET tentativa_atual = tentativa_atual + 1, "
                "versao = versao + 1, atualizado_em = now() "
                "WHERE id = ? AND versao = ? AND tentativa_atual < ? RETURNING tentativa_atual",
                [mensagem_id, versao_esperada, LIMITE_TENTATIVAS_MENSAGEM],
            ).fetchone()
        if resultado is None:
            raise ConflitoVersaoMensagem(mensagem_id, versao_esperada)
        return int(resultado[0])

    def obter(
        self, mensagem_id: UUID, conexao: duckdb.DuckDBPyConnection | None = None
    ) -> RegistroMensagem | None:
        """Lê uma mensagem pelo identificador, ou `None` se ela não existir."""

        with self._conexao(conexao) as ativa:
            linha = ativa.execute(f"{_SELECT_MENSAGEM} WHERE id = ?", [mensagem_id]).fetchone()
        if linha is None:
            return None
        return _mensagem_de_linha(linha)

    def listar_por_execucao(
        self, execucao_id: UUID, conexao: duckdb.DuckDBPyConnection | None = None
    ) -> list[RegistroMensagem]:
        """Lista as mensagens da execução, em ordem de criação (reidratação, GERAR-11)."""

        with self._conexao(conexao) as ativa:
            linhas = ativa.execute(
                f"{_SELECT_MENSAGEM} WHERE execucao_id = ? ORDER BY criado_em",
                [execucao_id],
            ).fetchall()
        return [_mensagem_de_linha(linha) for linha in linhas]

    def obter_versao(self, mensagem_id: UUID, versao_id: UUID) -> VersaoMensagem | None:
        """Lê uma versão da mensagem, ou `None` se ela não existir ou for de outra mensagem.

        A consulta é escopada pelas duas chaves: uma versão que existe mas pertence a outra
        mensagem é indistinguível de uma versão inexistente (AD-011).
        """

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                f"{_SELECT_VERSAO} WHERE id = ? AND mensagem_id = ?", [versao_id, mensagem_id]
            ).fetchone()
        if linha is None:
            return None
        return _versao_de_linha(linha)

    def listar_versoes(self, mensagem_id: UUID) -> list[VersaoMensagem]:
        """Lista todas as versões da mensagem, da primeira tentativa à última (REGEN-07).

        É o histórico imutável do ciclo: uma linha por tentativa, nenhuma sobrescrita, com a
        proveniência completa de cada chamada.
        """

        with abrir_conexao(self._caminho) as conexao:
            linhas = conexao.execute(
                f"{_SELECT_VERSAO} WHERE mensagem_id = ? "
                "ORDER BY numero_tentativa, criado_em",
                [mensagem_id],
            ).fetchall()
        return [_versao_de_linha(linha) for linha in linhas]

    def obter_versao_atual(self, mensagem_id: UUID) -> VersaoMensagem | None:
        """Lê a versão mais recente da mensagem, ou `None` se nenhuma foi persistida."""

        with abrir_conexao(self._caminho) as conexao:
            linha = conexao.execute(
                f"{_SELECT_VERSAO} WHERE mensagem_id = ? "
                "ORDER BY numero_tentativa DESC, criado_em DESC LIMIT 1",
                [mensagem_id],
            ).fetchone()
        if linha is None:
            return None
        return _versao_de_linha(linha)


_SELECT_MENSAGEM = (
    "SELECT id, execucao_id, elegibilidade_id, canal, estado, tentativa_atual, versao, "
    "criado_em, atualizado_em FROM mensagens"
)

_SELECT_VERSAO = (
    "SELECT id, mensagem_id, numero_tentativa, conteudo, valida, motivo_invalidez, "
    "duracao_ms, modelo, versao_prompt, tokens_entrada, tokens_saida, criado_em "
    "FROM versoes_mensagem"
)


def _mensagem_de_linha(linha: tuple[object, ...]) -> RegistroMensagem:
    """Traduz uma linha de `_SELECT_MENSAGEM` para `RegistroMensagem`."""

    return RegistroMensagem(
        id=UUID(str(linha[0])),
        execucao_id=UUID(str(linha[1])),
        elegibilidade_id=UUID(str(linha[2])),
        canal=Canal(str(linha[3])),
        estado=EstadoMensagem(str(linha[4])),
        tentativa_atual=int(linha[5]),  # type: ignore[arg-type]
        versao=int(linha[6]),  # type: ignore[arg-type]
        criado_em=cast(datetime, linha[7]),
        atualizado_em=cast(datetime, linha[8]),
    )


def _versao_de_linha(linha: tuple[object, ...]) -> VersaoMensagem:
    """Traduz uma linha de `_SELECT_VERSAO` para `VersaoMensagem`."""

    return VersaoMensagem(
        id=UUID(str(linha[0])),
        mensagem_id=UUID(str(linha[1])),
        numero_tentativa=int(linha[2]),  # type: ignore[arg-type]
        conteudo=desserializar_saida(str(linha[3])),
        valida=bool(linha[4]),
        motivo_invalidez=None if linha[5] is None else str(linha[5]),
        duracao_ms=float(linha[6]),  # type: ignore[arg-type]
        modelo=str(linha[7]),
        versao_prompt=str(linha[8]),
        tokens_entrada=None if linha[9] is None else int(linha[9]),  # type: ignore[arg-type]
        tokens_saida=None if linha[10] is None else int(linha[10]),  # type: ignore[arg-type]
        criado_em=cast(datetime, linha[11]),
    )
