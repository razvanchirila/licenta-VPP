import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, errorMessage, request, setUnauthorizedHandler } from './client'
import { loadToken, saveToken } from './token'

function mockFetch(status: number, body: unknown) {
  const fn = vi.fn(async () => new Response(body === null ? '' : JSON.stringify(body), { status }))
  vi.stubGlobal('fetch', fn)
  return fn
}

describe('request', () => {
  beforeEach(() => sessionStorage.clear())
  afterEach(() => {
    vi.unstubAllGlobals()
    setUnauthorizedHandler(() => {})
  })

  it('sends the saved token as a bearer header', async () => {
    saveToken('abc')
    const fetchMock = mockFetch(200, { ok: true })
    await expect(request('/api/sim/status')).resolves.toEqual({ ok: true })
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer abc')
  })

  it('on 401 clears the token, calls the handler and throws', async () => {
    saveToken('expired')
    const onUnauthorized = vi.fn()
    setUnauthorizedHandler(onUnauthorized)
    mockFetch(401, { detail: 'Token invalid' })

    const error = await request('/api/houses').catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect((error as ApiError).status).toBe(401)
    expect(onUnauthorized).toHaveBeenCalledOnce()
    expect(loadToken()).toBeNull()
  })

  it('does not log out when the login itself returns 401', async () => {
    const onUnauthorized = vi.fn()
    setUnauthorizedHandler(onUnauthorized)
    mockFetch(401, { detail: 'Utilizator sau parola gresita' })

    await expect(request('/api/auth/login', { method: 'POST', auth: false })).rejects.toThrow(
      'Utilizator sau parola gresita',
    )
    expect(onUnauthorized).not.toHaveBeenCalled()
  })

  it('reports a network failure as status 0', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => Promise.reject(new TypeError('Failed to fetch'))),
    )
    await expect(request('/api/config')).rejects.toMatchObject({ status: 0 })
  })
})

describe('errorMessage', () => {
  it('joins FastAPI validation errors without the "body" prefix', () => {
    const body = { detail: [{ loc: ['body', 'tick_seconds'], msg: 'too small' }] }
    expect(errorMessage(body, 422)).toBe('tick_seconds: too small')
  })

  it('falls back to the status code', () => {
    expect(errorMessage(null, 500)).toBe('Eroare 500')
  })
})
