"""Repositório DuckDB de `entregas_simuladas` (SIMUL-05, SIMUL-06).

A entrega simulada é uma cópia exata do `conteudo` da versão aprovada da mensagem (3.2),
serializada no mesmo formato de `versoes_mensagem` (`serializar_saida`): a simulação mostra
como o conteúdo *seria* apresentado no canal, sem gerar nem transformar texto nenhum. Nenhum
conector real de WhatsApp, e-mail ou SMS é tocado aqui — a única escrita é a desta tabela.

`criar_lote` insere o lote inteiro numa única chamada e aceita a conexão já aberta pelo
chamador. Sem esse parâmetro a atomicidade exigida pelo SIMUL-05 seria impossível: uma segunda
conexão ao mesmo arquivo não enxerga a transação aberta pela primeira e sobrevive ao `ROLLBACK`
dela (achado de 3.5). Mesmo parâmetro opcional já usado por
`RepositorioElegibilidades.copiar_para_execucao` (AD-012) e por `RepositorioMensagens` (3.5).

SPEC_DEVIATION (História 3.6): o `design.md` escreve
`criar_lote(self, execucao_id, mensagens_aprovadas) -> list[UUID]`, sem o parâmetro `conexao`,
embora o mesmo parágrafo exija que a inserção ocorra "dentro da transação já aberta pelo
chamador" — as duas coisas não podem valer ao mesmo tempo. `MensagemAprovada`,
`ApresentacaoSimulada` e `EntregaSimulada` também não são definidas no design; a forma delas
segue a linha "Forma da apresentação simulada por canal" da tabela de decisões da `spec.md`.
"""

from collections.abc import Generator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import duckdb

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.repositorio_mensagens import (
    desserializar_saida,
    serializar_saida,
)
from central_preventiva.dominio.validador_saida_canal import Canal, SaidaCanal

ROTULO_SIMULADA = "simulada"
"""Rótulo fixo de toda entrega desta tabela (SIMUL-06).

Não existe outro valor possível: nenhuma entrega real é criada em lugar nenhum do MVP, e a
tabela não tem coluna onde inventar confirmação ou falha de provedor externo.
"""


class EntregaSimuladaJaExiste(RuntimeError):
    """Indica uma segunda entrega simulada para a mesma mensagem (SIMUL-07)."""

    def __init__(self, execucao_id: UUID) -> None:
        """Identifica a execução cuja simulação já foi registrada, sem expor conteúdo."""

        super().__init__(
            f"A execução {execucao_id} já tem entrega simulada para uma das mensagens do lote."
        )
        self.execucao_id = execucao_id


@dataclass(frozen=True, slots=True)
class ApresentacaoSimulada:
    """Como o conteúdo aprovado apareceria no canal, sempre rotulado como simulado.

    WhatsApp e SMS têm apenas `corpo`; e-mail tem `assunto` e `corpo` — a mesma forma da
    `SaidaCanal` já validada e aprovada em 3.2/3.5, sem transformação.
    """

    canal: Canal
    corpo: str
    assunto: str | None = None
    rotulo: str = ROTULO_SIMULADA


@dataclass(frozen=True, slots=True)
class MensagemAprovada:
    """Uma mensagem aprovada a simular: identidade, canal e o conteúdo já aprovado."""

    mensagem_id: UUID
    canal: Canal
    conteudo: SaidaCanal


@dataclass(frozen=True, slots=True)
class EntregaSimulada:
    """Uma entrega simulada persistida, com a apresentação copiada do conteúdo aprovado."""

    id: UUID
    execucao_id: UUID
    mensagem_id: UUID
    canal: Canal
    apresentacao: ApresentacaoSimulada
    criado_em: datetime


class RepositorioEntregasSimuladas:
    """Cria e lê as entregas simuladas de uma execução."""

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

    def criar_lote(
        self,
        execucao_id: UUID,
        mensagens_aprovadas: Sequence[MensagemAprovada],
        conexao: duckdb.DuckDBPyConnection | None = None,
    ) -> list[UUID]:
        """Cria uma entrega simulada por mensagem, numa única chamada (SIMUL-05).

        A `apresentacao` é a serialização exata do conteúdo aprovado recebido; nada é gerado
        nem reescrito aqui. Uma segunda entrega para a mesma mensagem é recusada pela `UNIQUE`
        da migração `0014` e traduzida em `EntregaSimuladaJaExiste` (AD-010), nunca duplicada.
        """

        identificadores = [uuid4() for _ in mensagens_aprovadas]
        parametros = [
            [
                identificador,
                execucao_id,
                mensagem.mensagem_id,
                mensagem.canal.value,
                serializar_saida(mensagem.conteudo),
            ]
            for identificador, mensagem in zip(
                identificadores, mensagens_aprovadas, strict=True
            )
        ]
        try:
            with self._conexao(conexao) as ativa:
                ativa.executemany(
                    "INSERT INTO entregas_simuladas "
                    "(id, execucao_id, mensagem_id, canal, apresentacao) "
                    "VALUES (?, ?, ?, ?, ?)",
                    parametros,
                )
        except duckdb.ConstraintException as conflito:
            raise EntregaSimuladaJaExiste(execucao_id) from conflito
        return identificadores

    def listar_por_execucao(self, execucao_id: UUID) -> list[EntregaSimulada]:
        """Lista as entregas simuladas da execução, em ordem de criação (SIMUL-06)."""

        with abrir_conexao(self._caminho) as conexao:
            linhas = conexao.execute(
                "SELECT id, execucao_id, mensagem_id, canal, apresentacao, criado_em "
                "FROM entregas_simuladas WHERE execucao_id = ? ORDER BY criado_em, id",
                [execucao_id],
            ).fetchall()
        return [_entrega_de_linha(linha) for linha in linhas]


def _entrega_de_linha(linha: tuple[object, ...]) -> EntregaSimulada:
    """Traduz uma linha de `entregas_simuladas` para `EntregaSimulada`."""

    canal = Canal(str(linha[3]))
    conteudo = desserializar_saida(str(linha[4]))
    return EntregaSimulada(
        id=UUID(str(linha[0])),
        execucao_id=UUID(str(linha[1])),
        mensagem_id=UUID(str(linha[2])),
        canal=canal,
        apresentacao=ApresentacaoSimulada(
            canal=canal, corpo=conteudo.corpo, assunto=conteudo.assunto
        ),
        criado_em=cast(datetime, linha[5]),
    )
