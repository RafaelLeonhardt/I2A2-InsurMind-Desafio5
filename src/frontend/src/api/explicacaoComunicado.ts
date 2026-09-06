import { clienteApi } from './clienteHttp'
import type { components } from './tipos-gerados'

/** Evento meteorológico de origem, sempre rotulado como determinístico. */
export type EventoDeterministico = {
  id: string
  tipo: string
  area: string
  proveniencia: string
}

/** Evento e regra que originaram a mensagem — sempre `deterministica`. */
export type SecaoEvento = {
  origem: string
  evento: EventoDeterministico | null
  regraId: string
  regraVersao: number
}

/** Categorias de dado usadas e não usadas pelo agente redator. */
export type SecaoContexto = {
  categoriasUsadas: string[]
  categoriasNaoUsadas: string[]
}

/** Avaliação crítica de uma tentativa de geração. */
export type AvaliacaoCriticaTentativa = {
  aprovada: boolean
  motivos: string[]
  agente: string
  modelo: string
  duracaoMs: number
}

/** Decisão humana registrada sobre uma tentativa. */
export type DecisaoHumanaTentativa = {
  resultado: string
  justificativa: string | null
}

/** Uma tentativa de geração: redator, crítico e decisões humanas — sempre `agente`. */
export type Tentativa = {
  numeroTentativa: number
  origemRegeneracao: string
  corpo: string
  assunto: string | null
  modeloRedator: string
  avaliacaoCritica: AvaliacaoCriticaTentativa | null
  decisoesHumanas: DecisaoHumanaTentativa[]
}

/** Os papéis do agente redator e do agente crítico — sempre `agente`. */
export type SecaoAgente = {
  origem: string
  status: string
  causaExcecao: string | null
  tentativas: Tentativa[]
}

/** Prévia da mensagem final — cópia exata da versão aprovada e simulada. */
export type ApresentacaoSimuladaExplicacao = {
  canal: string
  assunto: string | null
  corpo: string
  rotulo: string
}

/** Explicação completa de "Como esta mensagem foi criada". */
export type ExplicacaoComunicado = {
  entregaSimuladaId: string
  mensagemId: string
  execucaoId: string
  execucaoOrigemId: string | null
  eventoERegra: SecaoEvento
  contexto: SecaoContexto | null
  agente: SecaoAgente
  apresentacaoSimulada: ApresentacaoSimuladaExplicacao | null
}

type CorpoProblema = Partial<components['schemas']['ProblemaExplicacaoComunicado']>

type DadosErroExplicacaoComunicado = {
  codigo: string
  correlacaoId: string | null
  ocorrencia: string
  impacto: string
  proximaAcao: string
  status: number | null
}

/** Falha tipada da consulta de explicação, com ocorrência, impacto e próxima ação segura. */
export class ErroExplicacaoComunicado extends Error {
  readonly codigo: string
  readonly correlacaoId: string | null
  readonly ocorrencia: string
  readonly impacto: string
  readonly proximaAcao: string
  readonly status: number | null

  constructor(dados: DadosErroExplicacaoComunicado) {
    super(dados.ocorrencia)
    this.name = 'ErroExplicacaoComunicado'
    this.codigo = dados.codigo
    this.correlacaoId = dados.correlacaoId
    this.ocorrencia = dados.ocorrencia
    this.impacto = dados.impacto
    this.proximaAcao = dados.proximaAcao
    this.status = dados.status
  }
}

const FALHA_INESPERADA = {
  ocorrencia: 'A explicação não pôde ser consultada.',
  impacto: 'A explicação pode estar indisponível ou desatualizada.',
  proximaAcao: 'Verifique se o backend local está disponível e tente novamente.',
}

const FALHA_DE_REDE: DadosErroExplicacaoComunicado = {
  codigo: 'falha_de_rede',
  correlacaoId: null,
  ocorrencia: 'Não foi possível falar com o backend local da Central Preventiva.',
  impacto: 'Nenhuma explicação pôde ser exibida.',
  proximaAcao: 'Confirme que o backend está em execução em 127.0.0.1:8000 e tente de novo.',
  status: null,
}

function erroDeResultado(erro: unknown, status: number): ErroExplicacaoComunicado {
  const corpo = (erro ?? {}) as CorpoProblema
  return new ErroExplicacaoComunicado({
    codigo: corpo.codigo ?? 'falha_inesperada',
    correlacaoId: corpo.correlacao_id ?? null,
    ocorrencia: corpo.ocorrencia ?? FALHA_INESPERADA.ocorrencia,
    impacto: corpo.impacto ?? FALHA_INESPERADA.impacto,
    proximaAcao: corpo.proxima_acao ?? FALHA_INESPERADA.proximaAcao,
    status,
  })
}

function paraTentativa(
  corpo: components['schemas']['RespostaTentativaExplicacao'],
): Tentativa {
  const avaliacao = corpo.avaliacao_critica
  return {
    numeroTentativa: corpo.numero_tentativa,
    origemRegeneracao: corpo.origem_regeneracao,
    corpo: corpo.corpo,
    assunto: corpo.assunto,
    modeloRedator: corpo.modelo_redator,
    avaliacaoCritica: avaliacao
      ? {
          aprovada: avaliacao.aprovada,
          motivos: avaliacao.motivos,
          agente: avaliacao.agente,
          modelo: avaliacao.modelo,
          duracaoMs: avaliacao.duracao_ms,
        }
      : null,
    decisoesHumanas: corpo.decisoes_humanas.map((decisao) => ({
      resultado: decisao.resultado,
      justificativa: decisao.justificativa,
    })),
  }
}

function paraExplicacao(
  corpo: components['schemas']['RespostaExplicacaoComunicado'],
): ExplicacaoComunicado {
  const evento = corpo.evento_e_regra.evento
  const contexto = corpo.contexto
  const apresentacao = corpo.apresentacao_simulada
  return {
    entregaSimuladaId: corpo.entrega_simulada_id,
    mensagemId: corpo.mensagem_id,
    execucaoId: corpo.execucao_id,
    execucaoOrigemId: corpo.execucao_origem_id,
    eventoERegra: {
      origem: corpo.evento_e_regra.origem,
      evento: evento
        ? { id: evento.id, tipo: evento.tipo, area: evento.area, proveniencia: evento.proveniencia }
        : null,
      regraId: corpo.evento_e_regra.regra_id,
      regraVersao: corpo.evento_e_regra.regra_versao,
    },
    contexto: contexto
      ? {
          categoriasUsadas: contexto.categorias_usadas,
          categoriasNaoUsadas: contexto.categorias_nao_usadas,
        }
      : null,
    agente: {
      origem: corpo.agente.origem,
      status: corpo.agente.status,
      causaExcecao: corpo.agente.causa_excecao,
      tentativas: corpo.agente.tentativas.map(paraTentativa),
    },
    apresentacaoSimulada: apresentacao
      ? {
          canal: apresentacao.canal,
          assunto: apresentacao.assunto,
          corpo: apresentacao.corpo,
          rotulo: apresentacao.rotulo,
        }
      : null,
  }
}

async function chamarExplicacao(seguradoId: string, entregaSimuladaId: string) {
  return clienteApi.GET(
    '/api/v1/segurados/{segurado_id}/comunicados/{entrega_simulada_id}/explicacao',
    {
      params: { path: { segurado_id: seguradoId, entrega_simulada_id: entregaSimuladaId } },
      fetch,
    },
  )
}

/** Consulta como um comunicado foi criado, ou lança `ErroExplicacaoComunicado` (`status`
 * 404 se o comunicado não existir ou não pertencer ao segurado). */
export async function getExplicacaoComunicado(
  seguradoId: string,
  entregaSimuladaId: string,
): Promise<ExplicacaoComunicado> {
  let resultado: Awaited<ReturnType<typeof chamarExplicacao>>
  try {
    resultado = await chamarExplicacao(seguradoId, entregaSimuladaId)
  } catch {
    throw new ErroExplicacaoComunicado(FALHA_DE_REDE)
  }

  if (!resultado.response.ok || !resultado.data) {
    throw erroDeResultado(resultado.error, resultado.response.status)
  }

  return paraExplicacao(resultado.data)
}
