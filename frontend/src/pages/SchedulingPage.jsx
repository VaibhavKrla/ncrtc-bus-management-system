import { useState, useEffect } from 'react'
import Layout from '../components/common/Layout'
import RosterGrid from '../components/scheduling/RosterGrid'
import RoutesPanel from '../components/scheduling/RoutesPanel'
import { schedulingApi } from '../services/schedulingApi'
import useAuthStore from '../store/authStore'

export default function SchedulingPage() {
  const { user } = useAuthStore()
  const [tab, setTab] = useState('roster')
  const [depots, setDepots] = useState([])
  const [selectedDepot, setSelectedDepot] = useState(null)

  useEffect(() => {
    schedulingApi.getDepots().then(data => {
      setDepots(data)
      // Depot managers default to their own depot
      if (user?.depot_id) {
        setSelectedDepot(user.depot_id)
      } else if (data.length > 0) {
        setSelectedDepot(data[0].id)
      }
    })
  }, [user])

  const depotName = depots.find(d => d.id === selectedDepot)?.name || ''

  return (
    <Layout>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 2 }}>📅 Scheduling</h1>
          <p style={{ fontSize: 13, color: '#6b7280' }}>Manage routes and assign driver duties</p>
        </div>

        {/* Depot selector (admin only) */}
        {user?.role === 'admin' && (
          <select
            value={selectedDepot || ''}
            onChange={e => setSelectedDepot(parseInt(e.target.value))}
            style={{
              padding: '8px 12px', borderRadius: 8, border: '1px solid #d1d5db',
              fontSize: 13, background: '#fff', minWidth: 180,
            }}
          >
            {depots.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
          </select>
        )}
      </div>

      {/* Depot badge */}
      {depotName && (
        <div style={{ marginBottom: '1rem' }}>
          <span style={{
            fontSize: 12, padding: '3px 10px', borderRadius: 99,
            background: '#eff6ff', color: '#1d4ed8', border: '1px solid #bfdbfe',
          }}>
            🏠 {depotName}
          </span>
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: '1.25rem', borderBottom: '1px solid #e5e7eb', paddingBottom: 0 }}>
        {[
          { id: 'roster', label: '🗂 Roster' },
          { id: 'routes', label: '🛣 Routes' },
        ].map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              padding: '8px 20px', border: 'none', cursor: 'pointer',
              background: 'none', fontSize: 14, fontWeight: tab === t.id ? 600 : 400,
              color: tab === t.id ? '#2563eb' : '#6b7280',
              borderBottom: tab === t.id ? '2px solid #2563eb' : '2px solid transparent',
              marginBottom: -1,
            }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {!selectedDepot ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#9ca3af' }}>
          Select a depot to continue.
        </div>
      ) : tab === 'roster' ? (
        <RosterGrid depotId={selectedDepot} />
      ) : (
        <RoutesPanel depotId={selectedDepot} depots={depots} />
      )}
    </Layout>
  )
}
