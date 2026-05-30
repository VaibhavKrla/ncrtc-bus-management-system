import { useState } from 'react'
import { incidentsApi } from '../../services/incidentsApi'
import toast from 'react-hot-toast'
import useAuthStore from '../../store/authStore'

const STATUS_COLORS = {
  open:         { bg: '#fef2f2', text: '#dc2626', border: '#fecaca' },
  acknowledged: { bg: '#eff6ff', text: '#2563eb', border: '#bfdbfe' },
  in_progress:  { bg: '#fff7ed', text: '#d97706', border: '#fed7aa' },
  resolved:     { bg: '#f0fdf4', text: '#16a34a', border: '#bbf7d0' },
  closed:       { bg: '#f9fafb', text: '#6b7280', border: '#e5e7eb' },
}

const SEV_COLORS = { P1: '#dc2626', P2: '#d97706', P3: '#2563eb' }

const NEXT_TRANSITIONS = {
  open:         [{ to: 'acknowledged', label: 'Acknowledge' }],
  acknowledged: [{ to: 'in_progress',  label: 'Start work'  }],
  in_progress:  [{ to: 'resolved',     label: 'Mark resolved' }],
  resolved:     [{ to: 'closed',       label: 'Close'        }],
  closed:       [],
}

function TimelineEvent({ event }) {
  const timeStr = new Date(event.created_at).toLocaleString('en-IN', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
  })
  return (
    <div style={{ display: 'flex', gap: 12, marginBottom: '1rem' }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <div style={{
          width: 10, height: 10, borderRadius: '50%', background: '#3b82f6',
          border: '2px solid #93c5fd', flexShrink: 0, marginTop: 3,
        }} />
        <div style={{ width: 1, flex: 1, background: '#e5e7eb', marginTop: 4 }} />
      </div>
      <div style={{ flex: 1, paddingBottom: '0.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
          <span style={{ fontSize: 13, fontWeight: 500, color: '#111827' }}>
            {event.actor_name || 'System'}
          </span>
          <span style={{ fontSize: 11, color: '#9ca3af' }}>{timeStr}</span>
        </div>
        {event.from_status && event.to_status && (
          <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 3 }}>
            <span style={{ textTransform: 'capitalize' }}>{event.from_status.replace('_',' ')}</span>
            {' → '}
            <span style={{ textTransform: 'capitalize', fontWeight: 500, color: '#374151' }}>
              {event.to_status.replace('_',' ')}
            </span>
          </div>
        )}
        {event.note && (
          <div style={{
            fontSize: 13, color: '#374151', background: '#f9fafb',
            border: '1px solid #e5e7eb', borderRadius: 6, padding: '5px 9px',
          }}>
            {event.note}
          </div>
        )}
      </div>
    </div>
  )
}

export default function IncidentDetail({ incident, onClose, onUpdate }) {
  const { user } = useAuthStore()
  const [note, setNote] = useState('')
  const [transitionLoading, setTransitionLoading] = useState(null)

  const sc = STATUS_COLORS[incident.status] || STATUS_COLORS.open
  const transitions = NEXT_TRANSITIONS[incident.status] || []

  const canTransition = ['admin', 'depot_manager', 'control_operator'].includes(user?.role)

  const handleTransition = async (toStatus) => {
    setTransitionLoading(toStatus)
    try {
      await incidentsApi.transition(incident.id, toStatus, note || null)
      toast.success(`Status → ${toStatus.replace('_', ' ')}`)
      setNote('')
      onUpdate()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Transition failed')
    } finally {
      setTransitionLoading(null)
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)',
      display: 'flex', alignItems: 'flex-start', justifyContent: 'flex-end', zIndex: 300,
    }}>
      <div style={{
        background: '#fff', width: 440, height: '100vh',
        overflowY: 'auto', boxShadow: '-4px 0 24px rgba(0,0,0,0.12)',
        display: 'flex', flexDirection: 'column',
      }}>
        {/* Header */}
        <div style={{ padding: '1.25rem', borderBottom: '1px solid #f3f4f6', position: 'sticky', top: 0, background: '#fff', zIndex: 10 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
            <div style={{ flex: 1, paddingRight: 8 }}>
              {incident.is_panic && (
                <div style={{
                  fontSize: 11, fontWeight: 700, color: '#fff', background: '#dc2626',
                  padding: '2px 8px', borderRadius: 4, display: 'inline-block', marginBottom: 4,
                }}>🚨 PANIC</div>
              )}
              <div style={{ fontWeight: 600, fontSize: 15, lineHeight: 1.4 }}>{incident.title}</div>
            </div>
            <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: '#6b7280', flexShrink: 0 }}>×</button>
          </div>

          {/* Badges */}
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <span style={{
              fontSize: 12, padding: '2px 10px', borderRadius: 99, fontWeight: 600,
              background: sc.bg, color: sc.text, border: `1px solid ${sc.border}`,
              textTransform: 'capitalize',
            }}>
              {incident.status.replace('_', ' ')}
            </span>
            <span style={{ fontSize: 12, padding: '2px 10px', borderRadius: 99, fontWeight: 700, color: '#fff', background: SEV_COLORS[incident.severity] }}>
              {incident.severity}
            </span>
            <span style={{ fontSize: 12, padding: '2px 10px', borderRadius: 99, background: '#f3f4f6', color: '#374151', textTransform: 'capitalize' }}>
              {incident.type}
            </span>
          </div>

          {/* SLA */}
          {incident.sla_remaining_mins !== null && (
            <div style={{
              marginTop: 8, fontSize: 12, padding: '4px 10px', borderRadius: 6,
              background: incident.sla_breached ? '#fef2f2' : '#f0fdf4',
              color: incident.sla_breached ? '#dc2626' : '#16a34a',
              border: `1px solid ${incident.sla_breached ? '#fecaca' : '#bbf7d0'}`,
            }}>
              {incident.sla_breached
                ? `⚠️ SLA breached by ${Math.abs(incident.sla_remaining_mins)} min`
                : `✓ SLA: ${incident.sla_remaining_mins} min remaining`}
            </div>
          )}
        </div>

        {/* Body */}
        <div style={{ flex: 1, padding: '1.25rem', overflowY: 'auto' }}>
          {/* Details grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1.25rem' }}>
            <Detail label="Raised by" value={incident.raised_by_name} />
            <Detail label="Assigned to" value={incident.assigned_to_name || '—'} />
            <Detail label="Vehicle" value={incident.registration_no || '—'} />
            <Detail label="Depot" value={incident.depot_name || '—'} />
            <Detail label="Created" value={new Date(incident.created_at).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })} />
            {incident.resolved_at && <Detail label="Resolved" value={new Date(incident.resolved_at).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })} />}
            {incident.lat && <Detail label="Location" value={`${incident.lat.toFixed(4)}, ${incident.lng.toFixed(4)}`} />}
          </div>

          {incident.description && (
            <div style={{ marginBottom: '1.25rem' }}>
              <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: 4 }}>Description</div>
              <div style={{ fontSize: 14, color: '#374151', lineHeight: 1.6 }}>{incident.description}</div>
            </div>
          )}

          {/* Status transition */}
          {canTransition && transitions.length > 0 && (
            <div style={{
              marginBottom: '1.25rem', padding: '1rem', background: '#f8fafc',
              borderRadius: 10, border: '1px solid #e5e7eb',
            }}>
              <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 8 }}>Update status</div>
              <textarea
                value={note}
                onChange={e => setNote(e.target.value)}
                placeholder="Add a note (optional)..."
                rows={2}
                style={{
                  width: '100%', padding: '7px 10px', borderRadius: 7,
                  border: '1px solid #d1d5db', fontSize: 13, resize: 'none',
                  marginBottom: 8, boxSizing: 'border-box',
                }}
              />
              <div style={{ display: 'flex', gap: 8 }}>
                {transitions.map(t => (
                  <button
                    key={t.to}
                    onClick={() => handleTransition(t.to)}
                    disabled={!!transitionLoading}
                    style={{
                      padding: '7px 16px', borderRadius: 7, border: 'none',
                      background: transitionLoading === t.to ? '#93c5fd' : '#2563eb',
                      color: '#fff', fontSize: 13, fontWeight: 500,
                      cursor: transitionLoading ? 'not-allowed' : 'pointer',
                    }}
                  >
                    {transitionLoading === t.to ? '...' : t.label}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Timeline */}
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: '0.875rem' }}>
              Timeline
            </div>
            {incident.events.length === 0 ? (
              <div style={{ fontSize: 13, color: '#9ca3af' }}>No events yet.</div>
            ) : (
              incident.events.map(e => <TimelineEvent key={e.id} event={e} />)
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function Detail({ label, value }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 13, fontWeight: 500, color: '#111827' }}>{value}</div>
    </div>
  )
}
