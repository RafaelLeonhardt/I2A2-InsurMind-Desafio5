import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { RestaurarDemonstracao } from './funcionalidades/dados-sinteticos/RestaurarDemonstracao.tsx'

const CAMINHO_RESTAURAR_DEMONSTRACAO = '/administracao/restaurar-demonstracao'

const raiz = document.getElementById('root')

if (!raiz) {
  throw new Error('Não foi possível iniciar a Central Preventiva: elemento raiz ausente.')
}

const pagina =
  window.location.pathname === CAMINHO_RESTAURAR_DEMONSTRACAO ? (
    <RestaurarDemonstracao />
  ) : (
    <App />
  )

createRoot(raiz).render(<StrictMode>{pagina}</StrictMode>)
