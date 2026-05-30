import { useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import useAuthStore from '../../store/authStore'

export default function ProtectedRoute({ children, allowedRoles = [] }) {
  const { user, token, fetchMe } = useAuthStore()

  useEffect(() => {
    if (token && !user) fetchMe()
  }, [token])

  if (!token) return <Navigate to="/login" replace />

  if (user && allowedRoles.length > 0 && !allowedRoles.includes(user.role)) {
    // Redirect drivers to driver portal, others to dashboard
    const dest =
      user.role === 'driver' || user.role === 'conductor'
        ? '/driver'
        : '/dashboard'
    return <Navigate to={dest} replace />
  }

  return children
}
