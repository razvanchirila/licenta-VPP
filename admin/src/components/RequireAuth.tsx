import { Navigate, Outlet, useLocation } from 'react-router'
import { useAuth } from '../hooks/useAuth'
import { LiveProvider } from './LiveProvider'
import { Spinner } from './Spinner'

export function RequireAuth() {
  const { user, token, checking } = useAuth()
  const location = useLocation()

  if (checking) return <Spinner label="Se verifică sesiunea…" fullscreen />
  if (!user || !token) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return (
    <LiveProvider token={token}>
      <Outlet />
    </LiveProvider>
  )
}
