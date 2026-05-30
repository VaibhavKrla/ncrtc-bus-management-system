import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../components/common/Layout'
import useAuthStore from '../store/authStore'
import api from '../services/api'

const SEV_COLOR = { P1: '#dc2626', P2: '#d97706', P3: '#2563eb' }
const STATUS_COLOR = {
  open: '#dc2626', acknowledged: '#2563eb',
  in_progress: '#d97706', resolved: '#16a34a', closed: '#6b7280'
}

function StatCard({ icon, label, value, sub, color = '#1e293b', onClick }) {
  return (
    <div
      onClick={onClick}
      style={{
        background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12,
        padding: '1.25rem', cursor: onClick ? 'pointer' : 'default',
        transition: 'box-shadow 0.15s',
      }}
      onMouseEnter={e => onClick && (e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.08)')}
      onMouseLeave={e => (e.currentTarget.style.boxShadow = 'none')}
    >
      <div style={{ fontSize: 24, marginBottom: 8 }}>{icon}</div>
      <div style={{ fontSize: 28, fontWeight: 700, color, marginBottom: 2 }}>{value}</div>
      <div style={{ fontSize: 13, fontWeight: 500, color: '#374151' }}>{label}</div>
      {sub && <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 2 }}>{sub}</div>}
    </div>
  )
}

function Skeleton({ h = 24, w = '100%', r = 6 }) {
  return (
    <div style={{
      height: h, width: w, borderRadius: r,
      background: 'linear-gradient(90deg, #f3f4f6 25%, #e5e7eb 50%, #f3f4f6 75%)',
      backgroundSize: '200% 100%',
      animation: 'shimmer 1.5s infinite',
    }} />
  )
}

export default function DashboardPage() {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.get('/dashboard/stats')
      .then(r => setStats(r.data))
      .catch(() => setError('Failed to load dashboard stats'))
      .finally(() => setLoading(false))
  }, [])

  const greeting = () => {
    const h = new Date().getHours()
    if (h < 12) return 'Good morning'
    if (h < 17) return 'Good afternoon'
    return 'Good evening'
  }

  return (
    <Layout>
      <style>{`@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }`}</style>

      {/* Header */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 2 }}>
          {greeting()}, {user?.full_name?.split(' ')[0] || user?.username} 👋
        </h1>
        <p style={{ fontSize: 13, color: '#6b7280' }}>
          {new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
          {stats?.as_of && <span style={{ marginLeft: 8 }}>· Updated {new Date(stats.as_of).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}</span>}
        </p>
      </div>

      {error && (
        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 10, padding: '0.875rem 1rem', marginBottom: '1rem', fontSize: 14, color: '#dc2626' }}>
          ⚠️ {error}
        </div>
      )}

      {/* Stats grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12, marginBottom: '1.5rem' }}>
        {loading ? (
          Array(6).fill(0).map((_, i) => (
            <div key={i} style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: '1.25rem' }}>
              <Skeleton h={24} w={40} r={4} />
              <div style={{ marginTop: 10 }}><Skeleton h={32} w={60} r={4} /></div>
              <div style={{ marginTop: 8 }}><Skeleton h={14} w="80%" r={4} /></div>
            </div>
          ))
        ) : stats ? (
          <>
            <StatCard icon="🚌" label="Total vehicles" value={stats.vehicles.total}
              sub={`${stats.vehicles.active} active`}
              onClick={() => navigate('/map')} />
            <StatCard icon="🗺️" label="Active on map" value={stats.vehicles.active}
              color="#16a34a" onClick={() => navigate('/map')} />
            <StatCard icon="⚠️" label="Open incidents" value={stats.incidents.open}
              color={stats.incidents.open > 0 ? '#dc2626' : '#16a34a'}
              sub={`${stats.incidents.p1_active} P1 active`}
              onClick={() => navigate('/incidents')} />
            <StatCard icon="📅" label="Duties today" value={stats.duties.today}
              sub={`${stats.duties.acknowledged} acknowledged`}
              onClick={() => navigate('/scheduling')} />
            <StatCard icon="📢" label="Notices" value={stats.notices.published}
              onClick={() => navigate('/notices')} />
            <StatCard icon="🚨" label="P1 active" value={stats.incidents.p1_active}
              color={stats.incidents.p1_active > 0 ? '#dc2626' : '#16a34a'}
              onClick={() => navigate('/incidents?severity=P1')} />
          </>
        ) : null}
      </div>

      {/* Two column layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* Recent incidents */}
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: '1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div style={{ fontSize: 15, fontWeight: 600 }}>Recent incidents</div>
            <button onClick={() => navigate('/incidents')} style={{
              fontSize: 12, color: '#2563eb', background: 'none', border: 'none', cursor: 'pointer',
            }}>View all →</button>
          </div>

          {loading ? (
            Array(4).fill(0).map((_, i) => (
              <div key={i} style={{ marginBottom: 10 }}>
                <Skeleton h={14} w="60%" r={4} />
                <div style={{ marginTop: 5 }}><Skeleton h={11} w="40%" r={4} /></div>
              </div>
            ))
          ) : stats?.recent_incidents?.length === 0 ? (
            <div style={{ fontSize: 13, color: '#9ca3af', textAlign: 'center', padding: '1.5rem 0' }}>
              No incidents yet 🎉
            </div>
          ) : (
            stats?.recent_incidents?.map(inc => (
              <div
                key={inc.id}
                onClick={() => navigate('/incidents')}
                style={{
                  display: 'flex', gap: 10, alignItems: 'flex-start',
                  padding: '8px 0', borderBottom: '1px solid #f9fafb', cursor: 'pointer',
                }}
              >
                <div style={{
                  width: 32, height: 32, borderRadius: 8, flexShrink: 0,
                  background: SEV_COLOR[inc.severity] + '18',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 10, fontWeight: 700, color: SEV_COLOR[inc.severity],
                }}>
                  {inc.is_panic ? '🚨' : inc.severity}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 500, color: '#111827',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {inc.title}
                  </div>
                  <div style={{ display: 'flex', gap: 6, marginTop: 2 }}>
                    <span style={{
                      fontSize: 11, padding: '1px 6px', borderRadius: 99,
                      background: STATUS_COLOR[inc.status] + '18',
                      color: STATUS_COLOR[inc.status], textTransform: 'capitalize',
                    }}>
                      {inc.status.replace('_', ' ')}
                    </span>
                    <span style={{ fontSize: 11, color: '#9ca3af' }}>
                      {inc.raised_by_name}
                    </span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Quick nav */}
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: '1.25rem' }}>
          <div style={{ fontSize: 15, fontWeight: 600, marginBottom: '1rem' }}>Quick access</div>
          {[
            { icon: '🗺️', label: 'Live Map', desc: 'Real-time vehicle positions', path: '/map', color: '#eff6ff' },
            { icon: '📅', label: 'Scheduling', desc: 'Roster and duty assignments', path: '/scheduling', color: '#f0fdf4', roles: ['admin','depot_manager'] },
            { icon: '⚠️', label: 'Incidents', desc: 'Open and active incidents', path: '/incidents', color: '#fef2f2' },
            { icon: '📢', label: 'Notices', desc: 'Publish notices to staff', path: '/notices', color: '#fefce8' },
          ].filter(m => !m.roles || m.roles.includes(user?.role)).map(m => (
            <div
              key={m.path}
              onClick={() => navigate(m.path)}
              style={{
                display: 'flex', alignItems: 'center', gap: 12,
                padding: '10px 12px', borderRadius: 10, marginBottom: 6,
                background: m.color, cursor: 'pointer', transition: 'opacity 0.15s',
              }}
              onMouseEnter={e => e.currentTarget.style.opacity = '0.8'}
              onMouseLeave={e => e.currentTarget.style.opacity = '1'}
            >
              <span style={{ fontSize: 22 }}>{m.icon}</span>
              <div>
                <div style={{ fontSize: 14, fontWeight: 500 }}>{m.label}</div>
                <div style={{ fontSize: 12, color: '#6b7280' }}>{m.desc}</div>
              </div>
              <span style={{ marginLeft: 'auto', color: '#9ca3af', fontSize: 16 }}>→</span>
            </div>
          ))}
        </div>
      </div>

      {/* Duties acknowledge progress */}
      {stats && stats.duties.today > 0 && (
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 12, padding: '1.25rem', marginTop: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <div style={{ fontSize: 14, fontWeight: 500 }}>Today's duty acknowledgements</div>
            <div style={{ fontSize: 13, color: '#6b7280' }}>
              {stats.duties.acknowledged} / {stats.duties.today}
            </div>
          </div>
          <div style={{ background: '#f3f4f6', borderRadius: 99, height: 8, overflow: 'hidden' }}>
            <div style={{
              height: '100%', borderRadius: 99,
              background: stats.duties.acknowledged === stats.duties.today ? '#16a34a' : '#2563eb',
              width: `${Math.round((stats.duties.acknowledged / stats.duties.today) * 100)}%`,
              transition: 'width 0.5s ease',
            }} />
          </div>
          <div style={{ fontSize: 12, color: '#9ca3af', marginTop: 5 }}>
            {stats.duties.today - stats.duties.acknowledged} drivers yet to acknowledge
          </div>
        </div>
      )}
    </Layout>
  )
}
