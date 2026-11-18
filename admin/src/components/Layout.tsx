import clsx from 'clsx'
import { NavLink, Outlet, useLocation } from 'react-router'
import { useAuth } from '../hooks/useAuth'
import { useLive } from '../hooks/useLive'
import { formatDate } from '../lib/format'
import { simStateLabel } from '../lib/simState'
import { ErrorBoundary } from './ErrorBoundary'
import styles from './Layout.module.css'

const NAV = [
  { to: '/', label: 'Prezentare generală', end: true },
  { to: '/case', label: 'Case', end: false },
  { to: '/cartier', label: 'Cartier', end: false },
  { to: '/simulare', label: 'Simulare', end: false },
  { to: '/utilizatori', label: 'Utilizatori', end: false },
]

export function Layout() {
  const { user, logout } = useAuth()
  const { status, connection } = useLive()
  const { pathname } = useLocation()
  const sim = simStateLabel(status)
  const connected = connection.state === 'open'
  const connectionText = connected
    ? 'live'
    : connection.retryInSeconds !== null
      ? `reconectare în ${connection.retryInSeconds} s`
      : 'se conectează…'

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.brand}>
          <span className={styles.logo} aria-hidden>
            <svg viewBox="0 0 24 24" width="18" height="18">
              <path d="M13.5 2 5 13.5h6L9.5 22 19 9.5h-6z" fill="currentColor" />
            </svg>
          </span>
          <span>
            <strong>VPP</strong> <span className={styles.brandSub}>Panou operator</span>
          </span>
        </div>

        <nav className={styles.nav} aria-label="Secțiuni">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => clsx(styles.navLink, isActive && styles.active)}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className={styles.right}>
          <div className={styles.clock} title="Ora simulată">
            <span className="muted">{formatDate(status?.sim_date)}</span>
            <strong className="num">{status?.sim_time ?? '--:--'}</strong>
            <span className={clsx(styles.badge, styles[sim.tone])}>{sim.label}</span>
          </div>
          <span className={styles.conn} title="Conexiunea WebSocket cu serverul">
            <span className={clsx(styles.dot, connected && styles.dotOn)} />
            {connectionText}
          </span>
          <span className={styles.user}>{user?.username}</span>
          <button type="button" className="btn btn-ghost" onClick={() => logout()}>
            Ieșire
          </button>
        </div>
      </header>

      <main className={styles.main}>
        {status?.last_error && <div className={styles.error}>Ultima eroare a simulării: {status.last_error}</div>}
        <ErrorBoundary resetKey={pathname}>
          <Outlet />
        </ErrorBoundary>
      </main>
    </div>
  )
}
