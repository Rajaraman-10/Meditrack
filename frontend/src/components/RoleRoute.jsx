import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'

function RoleRoute({ allowedRoles }) {
  const { user } = useAuth()
  return allowedRoles.includes(user.role)
    ? <Outlet />
    : <Navigate to="/" replace />
}

export default RoleRoute
