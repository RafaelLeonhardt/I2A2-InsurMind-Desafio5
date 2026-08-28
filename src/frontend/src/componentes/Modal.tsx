import { type KeyboardEvent, type ReactNode, useEffect, useId, useRef } from 'react'
import './Modal.css'

const SELETOR_FOCAVEIS = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')

export type PropriedadesModal = {
  /** Controla a presença do modal no documento. */
  aberto: boolean
  /** Título da confirmação, anunciado como nome acessível do diálogo. */
  titulo: string
  /** Objeto afetado pela ação, exigido pelo contrato UX-DR20. */
  objeto: string
  /** Impacto da ação, exigido pelo contrato UX-DR20. */
  impacto: string
  /** Rótulo do botão que confirma a ação. */
  rotuloConfirmar?: string
  /** Rótulo do botão que cancela a ação. */
  rotuloCancelar?: string
  /** Permite fechar por `Esc` e pelo botão de cancelamento. */
  podeFechar?: boolean
  /** Desabilita a confirmação enquanto a ação estiver em andamento. */
  confirmacaoDesabilitada?: boolean
  /** Conteúdo adicional, como o estado corrente da operação. */
  children?: ReactNode
  /** Executa a ação confirmada. */
  onConfirmar: () => void
  /** Fecha o modal sem executar a ação. */
  onFechar: () => void
}

/** Modal de confirmação acessível, conforme o contrato UX-DR20. */
export function Modal({
  aberto,
  titulo,
  objeto,
  impacto,
  rotuloConfirmar = 'Confirmar',
  rotuloCancelar = 'Cancelar',
  podeFechar = true,
  confirmacaoDesabilitada = false,
  children,
  onConfirmar,
  onFechar,
}: PropriedadesModal) {
  const identificador = useId()
  const idTitulo = `${identificador}-titulo`
  const idDescricao = `${identificador}-descricao`
  const referenciaDialogo = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!aberto) {
      return
    }

    const origemDoFoco = document.activeElement as HTMLElement | null
    const primeiroFocavel =
      referenciaDialogo.current?.querySelector<HTMLElement>(SELETOR_FOCAVEIS)
    primeiroFocavel?.focus()

    return () => {
      origemDoFoco?.focus()
    }
  }, [aberto])

  if (!aberto) {
    return null
  }

  function aoTeclar(evento: KeyboardEvent<HTMLDivElement>) {
    if (evento.key === 'Escape' && podeFechar) {
      evento.preventDefault()
      onFechar()
      return
    }

    if (evento.key !== 'Tab') {
      return
    }

    const focaveis = Array.from(
      referenciaDialogo.current?.querySelectorAll<HTMLElement>(SELETOR_FOCAVEIS) ?? [],
    )
    if (focaveis.length === 0) {
      return
    }

    const primeiro = focaveis[0]
    const ultimo = focaveis[focaveis.length - 1]

    if (evento.shiftKey && document.activeElement === primeiro) {
      evento.preventDefault()
      ultimo.focus()
      return
    }

    if (!evento.shiftKey && document.activeElement === ultimo) {
      evento.preventDefault()
      primeiro.focus()
    }
  }

  return (
    <div className="modal-fundo">
      <div
        aria-describedby={idDescricao}
        aria-labelledby={idTitulo}
        aria-modal="true"
        className="modal"
        onKeyDown={aoTeclar}
        ref={referenciaDialogo}
        role="dialog"
      >
        <h2 id={idTitulo}>{titulo}</h2>
        <dl className="modal-descricao" id={idDescricao}>
          <div>
            <dt>Objeto</dt>
            <dd>{objeto}</dd>
          </div>
          <div>
            <dt>Impacto</dt>
            <dd>{impacto}</dd>
          </div>
        </dl>
        {children}
        <div className="modal-acoes">
          <button disabled={!podeFechar} onClick={onFechar} type="button">
            {rotuloCancelar}
          </button>
          <button
            className="modal-confirmar"
            disabled={confirmacaoDesabilitada}
            onClick={onConfirmar}
            type="button"
          >
            {rotuloConfirmar}
          </button>
        </div>
      </div>
    </div>
  )
}
