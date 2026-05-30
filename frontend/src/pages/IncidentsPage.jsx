import { useState, useEffect, useCallback } from 'react'
import Layout from '../components/common/Layout'
import RaiseIncidentModal from '../components/incidents/RaiseIncidentModal'
import IncidentDetail from '../components/incidents/IncidentDetail'
import { incidentsApi } from '../services/incidentsApi'
import useAuthStore from '../store/authStore'
import toast from 'react-hot-toast'

const STATUS_COLORS = {
  open:         { bg: '#fef2f2', text: '#dc2626', border: '#fecaca' },
  acknowledged: { bg: '#eff6ff', text: '#2563eb', border: '#bfdbfe' },
  in_progress:  { bg: '#fff7ed', text: '#d97706', border: '#fed7aa' },
  resolved:     { bg: '#f0fdf4', text: '#16a34a', border: '#bbf7d0' },
  closed:       { bg: '#f9fafb', text: '#6b7280', border: '#e5e7eb' },
}

const SEV_COLORS = { P1: '#dc2626', P2: '#d97706', P3: '#2563eb' }
const STATUSES = ['open', 'acknowledged', 'in_progress', 'resolved', 'closed']
const SEVERITIES = ['P1', 'P2', 'P3']

function IncidentRow({ incident, onClick }) {
  const sc = STATUS_COLORS[incident.status] || STATUS_COLORS.open
  const timeAgo = Math.round((Date.now() - new Date(incident.created_at)) / 60000)
  const timeStr = timeAgo < 60
    ? `${timeAgo}m ago`
    : timeAgo < 1440
      ? `${Math.round(timeAgo / 60)}h ago`
      : `${Math.round(timeAgo / 1440)}d ago`

  return (
    <div
      onClick={() => onClick(incident)}
      style={{
        background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10,
        padding: '0.875rem 1rem', marginBottom: 8, cursor: 'pointer',
        display: 'flex', gap: 12, alignItems: 'flex-start',
        transition: 'box-shadow 0.15s',
        borderLeft: incident.is_panic ? '4px solid #dc2626' : incident.sla_breached ? '4px solid #f59e0b' : '1px solid #e5e7eb',
      }}
      onMouseEnter={e => e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)'}
      onMouseLeave={e => e.currentTarget.style.boxShadow = 'none'}
    >
      {/* Severity badge */}
      <div style={{
        width: 36, height: 36, borderRadius: 8, flexShrink: 0,
        background: SEV_COLORS[incident.severity] + '18',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 11, fontWeight: 700, color: SEV_COLORS[incident.severity],
      }}>
        {incident.severity}
      </div>

      {/* Main content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            {incident.is_panic && <span style={{ fontSize: 12 }}>🚨</span>}
            <span style={{ fontWeight: 600, fontSize: 14, color: '#111827' }}>
              {incident.title}
            </span>
          </div>
          <span style={{ fontSize: 12, color: '#9ca3af', flexShrink: 0, marginLeft: 8 }}>{timeStr}</span>
        </div>

        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 4 }}>
          <span style={{
            fontSize: 11, padding: '1px 8px', borderRadius: 99, fontWeight: 500,
            background: sc.bg, color: sc.text, border: `1px solid ${sc.border}`,
            textTransform: 'capitalize',
          }}>
            {incident.status.replace('_', ' ')}
          </span>
          <span style={{ fontSize: 11, padding: '1px 8px', borderRadius: 99, background: '#f3f4f6', color: '#6b7280', textTransform: 'capitalize' }}>
            {incident.type}
          </span>
          {incident.depot_name && (
            <span style={{ fontSize: 11, padding: '1px 8px', borderRadius: 99, background: '#eff6ff', color: '#1d4ed8' }}>
              {incident.depot_name}
            </span>
          )}
          {incident.sla_breached && (
            <span style={{ fontSize: 11, padding: '1px 8px', borderRadius: 99, background: '#fef3c7', color: '#b45309', fontWeight: 600 }}>
              ⚠️ SLA breach
            </span>
          )}
        </div>

        <div style={{ fontSize: 12, color: '#6b7280' }}>
          {incident.raised_by_name}
          {incident.registration_no && ` · ${incident.registration_no}`}
          {incident.assigned_to_name && ` · Assigned: ${incident.assigned_to_name}`}
        </div>
      </div>
    </div>
  )
}

export default function IncidentsPage() {
  const { user } = useAuthStore()
  const [incidents, setIncidents] = useState([])
  const [loading, setLoading] = useState(true)
  const [showRaise, setShowRaise] = useState(false)
  const [selected, setSelected] = useState(null)

  // Filters
  const [filterStatus, setFilterStatus] = useState('')
  const [filterSeverity, setFilterSeverity] = useState('')
  const [mineOnly, setMineOnly] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params = {}
      if (filterStatus) params.status = filterStatus
      if (filterSeverity) params.severity = filterSeverity
      if (mineOnly) params.mine_only = true
      const data = await incidentsApi.list(params)
      setIncidents(data)
    } catch {
      toast.error('Failed to load incidents')
    } finally {
      setLoading(false)
    }
  }, [filterStatus, filterSeverity, mineOnly])

  useEffect(() => { load() }, [load])

  // Refresh selected if it's open
  const handleUpdate = async () => {
    await load()
    if (selected) {
      const fresh = await incidentsApi.get(selected.id)
      setSelected(fresh)
    }
  }

  const counts = {
    open: incidents.filter(i => i.status === 'open').length,
    p1: incidents.filter(i => i.severity === 'P1' && i.status !== 'closed').length,
    sla: incidents.filter(i => i.sla_breached).length,
  }

  return (
    <Layout>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 2 }}>⚠️ Incidents</h1>
          <p style={{ fontSize: 13, color: '#6b7280' }}>Track and resolve operational incidents</p>
        </div>
        <button
          onClick={() => setShowRaise(true)}
          style={{
            padding: '9px 18px', borderRadius: 8, border: 'none',
            background: '#dc2626', color: '#fff', fontSize: 14,
            fontWeight: 500, cursor: 'pointer',
          }}
        >+ Raise incident</button>
      </div>

      {/* Stats */}
      <div style={{ display: 'flex', gap: 8, marginBottom: '1rem', flexWrap: 'wrap' }}>
        {[
          { label: 'Total', value: incidents.length, color: '#1e293b' },
          { label: 'Open', value: counts.open, color: '#dc2626' },
          { label: 'P1 active', value: counts.p1, color: '#dc2626' },
          { label: 'SLA breached', value: counts.sla, color: '#d97706' },
        ].map(s => (
          <div key={s.label} style={{
            background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8,
            padding: '6px 14px', display: 'flex', gap: 8, alignItems: 'center',
          }}>
            <span style={{ fontSize: 20, fontWeight: 700, color: s.color }}>{s.value}</span>
            <span style={{ fontSize: 12, color: '#6b7280' }}>{s.label}</span>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{
        background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10,
        padding: '0.75rem 1rem', marginBottom: '1rem',
        display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center',
      }}>
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}
          style={{ padding: '6px 10px', borderRadius: 7, border: '1px solid #d1d5db', fontSize: 13 }}>
          <option value="">All statuses</option>
          {STATUSES.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
        </select>

        <select value={filterSeverity} onChange={e => setFilterSeverity(e.target.value)}
          style={{ padding: '6px 10px', borderRadius: 7, border: '1px solid #d1d5db', fontSize: 13 }}>
          <option value="">All severities</option>
          {SEVERITIES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>

        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer' }}>
          <input type="checkbox" checked={mineOnly} onChange={e => setMineOnly(e.target.checked)} />
          Mine only
        </label>

        {(filterStatus || filterSeverity || mineOnly) && (
          <button onClick={() => { setFilterStatus(''); setFilterSeverity(''); setMineOnly(false) }}
            style={{ fontSize: 12, color: '#6b7280', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}>
            Clear filters
          </button>
        )}
      </div>

      {/* List */}
      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#9ca3af' }}>Loading...</div>
      ) : incidents.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '3rem', background: '#fff', borderRadius: 10, border: '1px solid #e5e7eb', color: '#9ca3af' }}>
          No incidents found.
        </div>
      ) : (
        incidents.map(inc => (
          <IncidentRow key={inc.id} incident={inc} onClick={setSelected} />
        ))
      )}

      {/* Modals */}
      {showRaise && (
        <RaiseIncidentModal onClose={() => setShowRaise(false)} onSave={load} />
      )}
      {selected && (
        <IncidentDetail
          incident={selected}
          onClose={() => setSelected(null)}
          onUpdate={handleUpdate}
        />
      )}
    </Layout>
  )
}
