"""Prepara o banco exclusivo da suíte E2E antes de o servidor subir (História 5.8).

Roda uma única vez, no `globalSetup` do Playwright, com o backend ainda parado: o DuckDB
aceita um único processo escritor, e o `README.md` já documenta que a inicialização precisa
terminar antes de iniciar o servidor.

Faz duas coisas:

1. Aplica as migrações versionadas e semeia o conjunto sintético canônico, exatamente como
   `python -m central_preventiva.composicao.inicializador`.
2. Insere as áreas monitoradas do INMET (AD-007). Nenhuma migração nem o semeador populam
   `areas_monitoradas_inmet`; sem essas linhas não existe `area_id` para iniciar uma execução
   preventiva. A tabela está na lista de exceções da restauração (`TABELAS_EXCECAO_RESTAURACAO`,
   AD-014), então as linhas sobrevivem a toda restauração feita entre cenários.

Os códigos de estação e as áreas sintéticas são os mesmos que as fixtures e o semeador já
usam: `A701 → 9990001` (chuva intensa, apólices residenciais) e `A702 → 9990002` (granizo,
apólices de automóvel).
"""

from central_preventiva.adaptadores.persistencia.conexao import abrir_conexao
from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.semeador import SemeadorDadosSinteticos
from central_preventiva.aplicacao.inicializacao import (
    PortasInicializacao,
    inicializar_dados_sinteticos,
)
from central_preventiva.composicao.configuracao import obter_configuracao
from central_preventiva.dominio.identificadores_demonstracao import identificador_demonstracao

AREAS_MONITORADAS = (
    ("area-monitorada/chuva", "A701", "Estação Sintética DEMO-A701", "9990001"),
    ("area-monitorada/granizo", "A702", "Estação Sintética DEMO-A702", "9990002"),
)


def executar() -> None:
    """Inicializa o schema/semeadura e garante as áreas monitoradas da demonstração."""

    configuracao = obter_configuracao()
    portas = PortasInicializacao(
        migracoes=ExecutorMigracoes(configuracao.caminho_banco),
        dados=SemeadorDadosSinteticos(configuracao.caminho_banco),
    )
    inicializar_dados_sinteticos(portas)

    with abrir_conexao(configuracao.caminho_banco) as conexao:
        for nome, codigo_estacao, nome_estacao, codigo_ibge_area in AREAS_MONITORADAS:
            conexao.execute(
                "INSERT INTO areas_monitoradas_inmet "
                "(id, codigo_estacao_inmet, nome_estacao, codigo_ibge_area, ativa) "
                "VALUES (?, ?, ?, ?, true) ON CONFLICT DO NOTHING",
                [identificador_demonstracao(nome), codigo_estacao, nome_estacao, codigo_ibge_area],
            )

    print(f"Banco E2E preparado em {configuracao.caminho_banco}.")


if __name__ == "__main__":
    executar()
