import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router'
import { ApiError } from '../api/client'
import { useAuth } from '../hooks/useAuth'
import styles from './LoginPage.module.css'

export function LoginPage() {
  const { user, notice, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const from = (location.state as { from?: string } | null)?.from ?? '/'
  if (user) return <Navigate to={from} replace />

  async function onSubmit(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(username.trim(), password)
      navigate(from, { replace: true })
    } catch (e) {
      setError(e instanceof ApiError && e.status === 401 ? 'Utilizator sau parolă greșită.' : (e as Error).message)
      setPassword('')
    } finally {
      setBusy(false)
    }
  }

  const message = error ?? notice
  return (
    <div className={styles.page}>
      <form className={styles.card} onSubmit={onSubmit}>
        <div className={styles.logo} aria-hidden>
          <svg viewBox="0 0 24 24" width="26" height="26">
            <path d="M13.5 2 5 13.5h6L9.5 22 19 9.5h-6z" fill="currentColor" />
          </svg>
        </div>
        <h1>Panou operator VPP</h1>
        <p className="muted">Comunitatea de 10 case: simulare, prețuri și schimb de energie. Acces doar pentru administratori.</p>

        <label className={styles.field}>
          <span>Utilizator</span>
          <input
            className="input"
            name="username"
            autoComplete="username"
            required
            maxLength={50}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
          />
        </label>
        <label className={styles.field}>
          <span>Parolă</span>
          <input
            className="input"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            maxLength={72}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>

        {message && (
          <p className={styles.error} role="alert">
            {message}
          </p>
        )}
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? 'Se verifică…' : 'Autentificare'}
        </button>
      </form>
    </div>
  )
}
