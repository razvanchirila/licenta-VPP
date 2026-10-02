import { useCallback, useState, type ReactNode } from 'react'
import clsx from 'clsx'
import { ToastContext, type ToastKind } from '../hooks/useToast'
import styles from './ToastProvider.module.css'

interface Toast {
  id: number
  message: string
  kind: ToastKind
}

const TOAST_MS = 4500
let nextId = 1

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const show = useCallback((message: string, kind: ToastKind = 'info') => {
    const id = nextId++
    setToasts((list) => [...list, { id, message, kind }])
    window.setTimeout(() => setToasts((list) => list.filter((t) => t.id !== id)), TOAST_MS)
  }, [])

  return (
    <ToastContext value={show}>
      {children}
      <div className={styles.stack} aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={clsx(styles.toast, styles[t.kind])}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext>
  )
}
