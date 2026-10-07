import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'

function ProtectedRoute() {
  const { user, loading } = useAuth()

  if (loading) {
    return <p className="route-message" role="status">Checking your session…</p>
  }

  return user ? <Outlet /> : <Navigate to="/login" replace />
}

export default ProtectedRoute
