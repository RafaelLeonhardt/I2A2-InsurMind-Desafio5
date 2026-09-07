import { SeguradoProvider, useSeguradoContexto } from '../../contexto/SeguradoContexto'
import { SeletorSegurado } from './SeletorSegurado'
import { SuperficieAlertas } from './SuperficieAlertas'
import { SuperficieApolice } from './SuperficieApolice'
import { SuperficieComunicados } from './SuperficieComunicados'
import { SuperficieMeusDados } from './SuperficieMeusDados'
import { VisaoGeralSegurado } from './VisaoGeralSegurado'

/**
 * SPEC_DEVIATION (5.7 T5): `design.md`/`tasks.md` descrevem cada uma das cinco superfícies
 * de 5.1–5.6 passando a "consumir `seguradoAtivoId` de `useSeguradoContexto()`" — lido
 * literalmente, isso exigiria cada arquivo chamar o hook internamente, o que quebraria a
 * suíte de testes existente de cada superfície (hoje renderizada isoladamente, sem
 * `SeguradoProvider`), forçando reescrever ~5 suítes só para acomodar uma dependência de
 * contexto nova. As cinco superfícies já foram construídas nas Histórias 5.1–5.6 com o seam
 * exato que esta história precisa: uma prop opcional `seguradoId`. `PainelSegurado` é o
 * único ponto que lê `useSeguradoContexto()` e injeta `seguradoAtivoId` como essa prop em
 * cada uma — "mudança de fonte do segurado_id" (design.md) acontece na composição, não
 * reescrevendo cada superfície. Nenhum arquivo de 5.1–5.6 foi alterado; nenhum teste
 * existente foi tocado.
 *
 * Enquanto o contexto está `trocando`, `seguradoAtivoId` não muda até a troca ser validada
 * (SeguradoContexto, 5.7 T3) — a prop injetada aqui também não muda, então nenhuma das cinco
 * superfícies dispara uma nova requisição antes da troca estar confirmada, e uma falha
 * reverte silenciosamente sem nunca propagar um id inconsistente (SELETOR-02/03/04).
 *
 * fix (5.8, achado pela suíte E2E): a grade CSS de `.aplicacao` (`App.css`) espera UM único
 * item de conteúdo na célula central — cada superfície de 5.1–5.6 foi construída como página
 * independente, com seu próprio `<main id="conteudo-principal">`. Compostas como irmãs soltas
 * (Fragment), eram 6 itens (`SeletorSegurado` + 5 superfícies) auto-posicionados pela grade,
 * um deles caindo sob a coluna de navegação, mais 6 landmarks/ids "conteudo-principal"
 * duplicados. `conteudo-segurado-empilhado` (App.css) é o único item real da grade; dentro
 * dele as superfícies empilham em fluxo normal. Só `VisaoGeralSegurado` continua como o
 * `<main>` da página (âncora do skip-link); as outras quatro recebem `comoSecao` e renderizam
 * como `<section>` sem `id`/foco próprios.
 */
function ConteudoPainelSegurado() {
  const { seguradoAtivoId } = useSeguradoContexto()
  const seguradoId = seguradoAtivoId ?? undefined

  return (
    <div className="conteudo-segurado-empilhado">
      <SeletorSegurado />
      <VisaoGeralSegurado seguradoId={seguradoId} />
      <SuperficieAlertas comoSecao seguradoId={seguradoId} />
      <SuperficieApolice comoSecao seguradoId={seguradoId} />
      <SuperficieComunicados comoSecao seguradoId={seguradoId} />
      <SuperficieMeusDados comoSecao seguradoId={seguradoId} />
    </div>
  )
}

/** Painel completo do perfil Segurado: seletor "Visualizar como" + as cinco superfícies de
 * 5.1–5.6, todas seguindo o mesmo segurado sintético ativo (5.7). */
export function PainelSegurado() {
  return (
    <SeguradoProvider>
      <ConteudoPainelSegurado />
    </SeguradoProvider>
  )
}
