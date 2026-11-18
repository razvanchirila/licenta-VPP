import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, errorMessage, request, requestText, setUnauthorizedHandler } from './client'
import { clearToken, loadToken, saveToken } from './token'

function mockFetch(status: number, body: unknown) {
  const fn = vi.fn(async () => new Response(body === null ? '' : JSON.stringify(body), { status }))
  vi.stubGlobal('fetch', fn)
  return fn
}

describe('request', () => {
  beforeEach(clearToken)
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

  it('without a token does not call the server or the 401 handler', async () => {
    const onUnauthorized = vi.fn()
    setUnauthorizedHandler(onUnauthorized)
    const fetchMock = mockFetch(200, { ok: true })

    await expect(request('/api/vpp/stats')).rejects.toMatchObject({ status: 401 })
    expect(fetchMock).not.toHaveBeenCalled()
    expect(onUnauthorized).not.toHaveBeenCalled()
  })

  it('reports a network failure as status 0', async () => {
    saveToken('abc')
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => Promise.reject(new TypeError('Failed to fetch'))),
    )
    await expect(request('/api/config')).rejects.toMatchObject({ status: 0 })
  })
})

describe('requestText', () => {
  beforeEach(clearToken)
  afterEach(() => {
    vi.unstubAllGlobals()
    setUnauthorizedHandler(() => {})
  })

  it('returns the body as text and sends the token', async () => {
    saveToken('abc')
    const fetchMock = vi.fn(async () => new Response('id;persoane\n1;3\n', { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(requestText('/api/admin/neighbourhood/export')).resolves.toBe('id;persoane\n1;3\n')
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit]
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer abc')
  })

  it('on 401 logs out exactly like a JSON request', async () => {
    saveToken('expired')
    const onUnauthorized = vi.fn()
    setUnauthorizedHandler(onUnauthorized)
    mockFetch(401, { detail: 'Token invalid' })

    await expect(requestText('/api/admin/neighbourhood/export')).rejects.toMatchObject({ status: 401 })
    expect(onUnauthorized).toHaveBeenCalledOnce()
    expect(loadToken()).toBeNull()
  })

  it('reads the error message from a JSON answer', async () => {
    saveToken('abc')
    mockFetch(403, { detail: 'Doar pentru administratori' })
    await expect(requestText('/api/admin/neighbourhood/export')).rejects.toThrow('Doar pentru administratori')
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
