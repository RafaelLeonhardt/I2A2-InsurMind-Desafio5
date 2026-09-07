/** `globalTeardown` da suíte E2E: derruba frontend, backend e dublês, nessa ordem. */

import { ambienteAtivo } from './global-setup.ts'

export default async function globalTeardown(): Promise<void> {
  const ambiente = ambienteAtivo()
  if (ambiente === undefined) return
  await ambiente.frontend.encerrar()
  await ambiente.backend.encerrar()
  await ambiente.dubles.encerrar()
}
