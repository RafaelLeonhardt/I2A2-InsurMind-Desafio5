import { useEffect, useState } from 'react'
import {
  type EstadoDocumentacaoApi,
  ErroDocumentacaoApi,
  ENDERECO_SWAGGER_UI,
  type ResultadoDocumentacaoApi,
  verificarDocumentacaoApi,
} from '../../api/documentacaoApi'

/** Superfície "Documentação da API": prova, via chamada real, se Swagger UI/openapi.json estão disponíveis. */
export function SuperficieDocumentacaoApi() {
  const [estado, definirEstado] = useState<EstadoDocumentacaoApi>('carregando')
  const [resultado, definirResultado] = useState<ResultadoDocumentacaoApi | null>(null)
  const [falha, definirFalha] = useState<ErroDocumentacaoApi | null>(null)

  useEffect(() => {
    let cancelado = false

    definirEstado('carregando')
    verificarDocumentacaoApi()
      .then((valor) => {
        if (cancelado) return
        definirResultado(valor)
        definirFalha(null)
        definirEstado('disponivel')
      })
      .catch((causa: unknown) => {
        if (cancelado) return
        definirResultado(null)
        definirFalha(causa instanceof ErroDocumentacaoApi ? causa : null)
        definirEstado('indisponivel')
      })

    return () => {
      cancelado = true
    }
  }, [])

  return (
    <main className="conteudo" id="conteudo-principal" tabIndex={-1}>
      <p className="rotulo-contexto">Documentação da API</p>
      <h1>Documentação da API</h1>
      <p className="introducao">
        Confirma, via chamada real ao backend, se a Swagger UI e o contrato OpenAPI estão
        disponíveis localmente.
      </p>

      {estado === 'carregando' && <p role="status">Verificando disponibilidade…</p>}

      {estado === 'disponivel' && resultado && (
        <div>
          <p>
            <strong>Disponível</strong>
          </p>
          <p>
            Swagger UI:{' '}
            <a href={resultado.enderecoSwaggerUi} rel="noopener noreferrer" target="_blank">
              {resultado.enderecoSwaggerUi}
            </a>
          </p>
          <p>Contrato OpenAPI: {resultado.enderecoOpenApi}</p>
        </div>
      )}

      {estado === 'indisponivel' && (
        <div role="alert">
          <p>
            <strong>Indisponível</strong>
          </p>
          <p>
            <strong>Causa:</strong> {falha?.causa ?? 'Falha desconhecida ao verificar a documentação da API.'}
          </p>
          <p>
            <strong>Impacto:</strong> {falha?.impacto ?? ''}
          </p>
          <p>
            <strong>Próxima ação:</strong> {falha?.proximaAcao ?? ''}
          </p>
          <p>
            <strong>Endereço esperado:</strong> {falha?.enderecoEsperado ?? ENDERECO_SWAGGER_UI}
          </p>
        </div>
      )}
    </main>
  )
}
