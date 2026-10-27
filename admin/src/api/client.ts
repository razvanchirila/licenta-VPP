import { clearToken, loadToken } from './token'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type UnauthorizedHandler = () => void
let onUnauthorized: UnauthorizedHandler = () => {}

export function setUnauthorizedHandler(handler: UnauthorizedHandler): void {
  onUnauthorized = handler
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: unknown
  auth?: boolean
}

interface ValidationIssue {
  loc?: (string | number)[]
  msg: string
}

export function errorMessage(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return (detail as ValidationIssue[])
      .map((e) => (e.loc && e.loc.length > 1 ? `${e.loc.slice(1).join('.')}: ` : '') + e.msg)
      .join('; ')
  }
  if (status === 403) return 'Acces interzis'
  return `Eroare ${status}`
}

async function readJson(res: Response): Promise<unknown> {
  const text = await res.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return null
  }
}

export async function request<T>(path: string, { method = 'GET', body, auth = true }: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' }
  const token = auth ? loadToken() : null
  // after a logout, queries still mounted may refetch once more: without a token there is nothing to ask
  if (auth && !token) throw new ApiError(401, 'Neautentificat')
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined) headers['Content-Type'] = 'application/json'

  let res: Response
  try {
    res = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) })
  } catch {
    throw new ApiError(0, 'Serverul nu răspunde')
  }

  const data = await readJson(res)
  if (res.status === 401 && auth) {
    clearToken()
    onUnauthorized()
    throw new ApiError(401, 'Sesiunea a expirat, autentifică-te din nou.')
  }
  if (!res.ok) throw new ApiError(res.status, errorMessage(data, res.status))
  return data as T
}

/** A text download (e.g. CSV) with the session token; errors as in request(). */
export async function requestText(path: string): Promise<string> {
  const token = loadToken()
  if (!token) throw new ApiError(401, 'Neautentificat')
  let res: Response
  try {
    res = await fetch(path, { headers: { Authorization: `Bearer ${token}` } })
  } catch {
    throw new ApiError(0, 'Serverul nu răspunde')
  }
  const text = await res.text()
  if (!res.ok) {
    let body: unknown
    try {
      body = JSON.parse(text)
    } catch {
      body = null
    }
    throw new ApiError(res.status, errorMessage(body, res.status))
  }
  return text
}
