import createClient from 'openapi-fetch'

import type { paths } from './tipos-gerados'

export const ENDERECO_BASE_API = 'http://127.0.0.1:8000'

export const clienteApi = createClient<paths>({ baseUrl: ENDERECO_BASE_API })
