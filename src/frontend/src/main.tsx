import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

const raiz = document.getElementById('root')

if (!raiz) {
  throw new Error('Não foi possível iniciar a Central Preventiva: elemento raiz ausente.')
}

createRoot(raiz).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
