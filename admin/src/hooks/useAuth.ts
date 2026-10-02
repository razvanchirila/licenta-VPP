import { createContext, useContext } from 'react'
import type { Me } from '../types/api'

export interface AuthContextValue {
  user: Me | null
  token: string | null
  checking: boolean
  notice: string | null
  login: (username: string, password: string) => Promise<void>
  logout: (notice?: string) => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
