"""Comando local de inicialização do schema versionado e dos dados sintéticos."""

from central_preventiva.adaptadores.persistencia.migracoes import ExecutorMigracoes
from central_preventiva.adaptadores.persistencia.semeador import SemeadorDadosSinteticos
from central_preventiva.aplicacao.inicializacao import (
    PortasInicializacao,
    inicializar_dados_sinteticos,
)
from central_preventiva.aplicacao.portas_persistencia import ResultadoInicializacao
from central_preventiva.composicao.configuracao import obter_configuracao


def descrever_resultado(resultado: ResultadoInicializacao) -> str:
    """Descreve em português o que a inicialização efetivamente preparou."""

    if resultado.estado == "ja_preparado":
        return (
            "Dados já preparados: nenhuma migração pendente e conjunto sintético já presente."
        )

    if resultado.versoes_aplicadas:
        versoes = ", ".join(str(versao) for versao in resultado.versoes_aplicadas)
        migracoes = f"migrações aplicadas: {versoes}"
    else:
        migracoes = "nenhuma migração pendente"
    semeadura = (
        "conjunto sintético semeado"
        if resultado.semeado_agora
        else "conjunto sintético já presente"
    )
    return f"Dados sintéticos inicializados ({migracoes}; {semeadura})."


def executar() -> None:
    """Valida a configuração, aplica as migrações pendentes e semeia a demonstração."""

    configuracao = obter_configuracao()
    portas = PortasInicializacao(
        migracoes=ExecutorMigracoes(configuracao.caminho_banco),
        dados=SemeadorDadosSinteticos(configuracao.caminho_banco),
    )
    print(descrever_resultado(inicializar_dados_sinteticos(portas)))


if __name__ == "__main__":
    executar()
