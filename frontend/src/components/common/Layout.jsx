import { Link, useLocation, useNavigate } from 'react-router-dom'
import useAuthStore from '../../store/authStore'

const NAV = [
  { path: '/dashboard',   label: 'Dashboard',  icon: '🏠', roles: ['admin','depot_manager','control_operator'] },
  { path: '/map',         label: 'Live Map',   icon: '🗺️',  roles: ['admin','depot_manager','control_operator'] },
  { path: '/scheduling',  label: 'Scheduling', icon: '📅', roles: ['admin','depot_manager'] },
  { path: '/incidents',   label: 'Incidents',  icon: '⚠️',  roles: ['admin','depot_manager','control_operator'] },
  { path: '/notices',     label: 'Notices',    icon: '📢', roles: ['admin','depot_manager','control_operator'] },
]

const ROLE_COLORS = {
  admin: '#dc2626',
  depot_manager: '#d97706',
  control_operator: '#2563eb',
  driver: '#16a34a',
  conductor: '#7c3aed',
}

export default function Layout({ children }) {
  const { user, logout } = useAuthStore()
  const location = useLocation()
  const navigate = useNavigate()

  const visibleNav = NAV.filter(n => n.roles.includes(user?.role))

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#f3f4f6' }}>
      {/* Sidebar */}
      <aside style={{
        width: 220, background: '#1e293b', color: '#fff',
        display: 'flex', flexDirection: 'column', flexShrink: 0,
        position: 'fixed', top: 0, left: 0, bottom: 0, zIndex: 100,
      }}>
        {/* Logo */}
        <div style={{ padding: '1.25rem 1rem', borderBottom: '1px solid #334155' }}>
          <div style={{ fontSize: 18, fontWeight: 700 }}>🚌 NCRTC BMS</div>
          <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>Bus Management System</div>
        </div>

        {/* Nav links */}
        <nav style={{ flex: 1, padding: '0.75rem 0' }}>
          {visibleNav.map(n => {
            const active = location.pathname.startsWith(n.path)
            return (
              <Link
                key={n.path}
                to={n.path}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '0.625rem 1rem',
                  background: active ? '#334155' : 'transparent',
                  color: active ? '#fff' : '#94a3b8',
                  textDecoration: 'none', fontSize: 14,
                  borderLeft: active ? '3px solid #3b82f6' : '3px solid transparent',
                  transition: 'all 0.15s',
                }}
              >
                <span>{n.icon}</span>
                <span>{n.label}</span>
              </Link>
            )
          })}
        </nav>

        {/* User info + logout */}
        <div style={{ padding: '1rem', borderTop: '1px solid #334155' }}>
          <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 4 }}>
            {user?.full_name || user?.username}
          </div>
          <div style={{
            display: 'inline-block', fontSize: 11, padding: '2px 8px',
            borderRadius: 99, background: ROLE_COLORS[user?.role] || '#475569',
            color: '#fff', marginBottom: 10,
          }}>
            {user?.role?.replace('_', ' ')}
          </div>
          <button
            onClick={logout}
            style={{
              display: 'block', width: '100%', padding: '6px',
              background: '#334155', color: '#94a3b8', border: 'none',
              borderRadius: 6, fontSize: 13, cursor: 'pointer',
            }}
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main style={{ marginLeft: 220, flex: 1, padding: '1.5rem', minWidth: 0 }}>
        {children}
      </main>
    </div>
  )
}
