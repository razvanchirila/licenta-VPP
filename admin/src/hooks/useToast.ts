import { createContext, useContext } from 'react'

export type ToastKind = 'info' | 'ok' | 'error'

export const ToastContext = createContext<(message: string, kind?: ToastKind) => void>(() => {})

export function useToast() {
  return useContext(ToastContext)
}
