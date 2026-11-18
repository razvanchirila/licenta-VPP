import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { clearToken, loadToken, saveToken } from './token'

const KEY = 'vpp_admin_token'

describe('token', () => {
  beforeEach(() => {
    clearToken()
    sessionStorage.clear()
  })
  afterEach(() => vi.restoreAllMocks())

  it('keeps the saved token and copies it to sessionStorage', () => {
    saveToken('abc')
    expect(loadToken()).toBe('abc')
    expect(sessionStorage.getItem(KEY)).toBe('abc')
  })

  it('forgets the token on clear', () => {
    saveToken('abc')
    clearToken()
    expect(loadToken()).toBeNull()
    expect(sessionStorage.getItem(KEY)).toBeNull()
  })

  it('still works when the storage is blocked', () => {
    const blocked = () => {
      throw new DOMException('blocked', 'SecurityError')
    }
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(blocked)
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(blocked)
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(blocked)

    saveToken('abc')
    expect(loadToken()).toBe('abc')
    clearToken()
    expect(loadToken()).toBeNull()
  })

  it('starts from the token left in sessionStorage before a reload', async () => {
    sessionStorage.setItem(KEY, 'din-sesiune')
    vi.resetModules()
    const fresh = await import('./token')
    expect(fresh.loadToken()).toBe('din-sesiune')
  })
})
