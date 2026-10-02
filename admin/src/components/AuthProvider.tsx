import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { ApiError, setUnauthorizedHandler } from '../api/client'
import { api } from '../api/endpoints'
import { clearToken, loadToken, saveToken } from '../api/token'
import { AuthContext, type AuthContextValue } from '../hooks/useAuth'
import type { Me } from '../types/api'

const NOT_ADMIN = 'Contul nu are rol de administrator.'

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [token, setToken] = useState<string | null>(loadToken)
  const [user, setUser] = useState<Me | null>(null)
  const [checking, setChecking] = useState(token !== null)
  const [notice, setNotice] = useState<string | null>(null)

  const logout = useCallback(
    (message?: string) => {
      clearToken()
      setToken(null)
      setUser(null)
      setChecking(false)
      setNotice(message ?? null)
      queryClient.clear()
    },
    [queryClient],
  )

  useEffect(() => {
    setUnauthorizedHandler(() => logout('Sesiunea a expirat, autentifică-te din nou.'))
  }, [logout])

  // a token left in sessionStorage from before a reload is checked once against /me
  useEffect(() => {
    if (!token || user) return
    let cancelled = false
    api
      .me()
      .then((me) => {
        if (cancelled) return
        if (me.is_admin) {
          setUser(me)
          setChecking(false)
        } else {
          logout(NOT_ADMIN)
        }
      })
      .catch((e: unknown) => {
        if (!cancelled && !(e instanceof ApiError && e.status === 401)) logout((e as Error).message)
      })
    return () => {
      cancelled = true
    }
  }, [token, user, logout])

  const login = useCallback(async (username: string, password: string) => {
    const res = await api.login(username, password)
    if (!res.is_admin) throw new Error(NOT_ADMIN)
    saveToken(res.access_token)
    const me = await api.me()
    setNotice(null)
    setUser(me)
    setToken(res.access_token)
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({ user, token, checking, notice, login, logout }),
    [user, token, checking, notice, login, logout],
  )
  return <AuthContext value={value}>{children}</AuthContext>
}
