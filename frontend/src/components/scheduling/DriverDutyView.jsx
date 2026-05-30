import { useState, useEffect } from 'react'
import { schedulingApi } from '../../services/schedulingApi'
import toast from 'react-hot-toast'

const STATUS_CONFIG = {
  draft:        { label: 'Pending',      color: '#854d0e', bg: '#fef9c3' },
  published:    { label: 'Needs Ack',    color: '#1e40af', bg: '#dbeafe' },
  acknowledged: { label: 'Acknowledged', color: '#166534', bg: '#dcfce7' },
  completed:    { label: 'Completed',    color: '#6b7280', bg: '#f3f4f6' },
}

export default function DriverDutyView() {
  const [duties, setDuties] = useState([])
  const [loading, setLoading] = useState(true)
  const [ackLoading, setAckLoading] = useState(null)

  const today = new Date().toISOString().slice(0, 10)

  const load = async () => {
    try {
      const data = await schedulingApi.getDuties({ date: today })
      setDuties(data)
    } catch {
      toast.error('Could not load duties')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleAcknowledge = async (dutyId) => {
    setAckLoading(dutyId)
    try {
      await schedulingApi.acknowledgeDuty(dutyId)
      toast.success('Duty acknowledged ✓')
      load()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to acknowledge')
    } finally {
      setAckLoading(null)
    }
  }

  const todayFormatted = new Date().toLocaleDateString('en-IN', {
    weekday: 'long', day: 'numeric', month: 'long'
  })

  if (loading) return (
    <div style={{ padding: '1.5rem', textAlign: 'center', color: '#9ca3af' }}>
      Loading duties...
    </div>
  )

  return (
    <div style={{ padding: '1rem' }}>
      <div style={{ marginBottom: '1rem' }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 2 }}>📅 My Duty</h2>
        <div style={{ fontSize: 13, color: '#6b7280' }}>{todayFormatted}</div>
      </div>

      {duties.length === 0 ? (
        <div style={{
          background: '#fff', borderRadius: 12, padding: '2rem',
          textAlign: 'center', color: '#9ca3af', border: '1px solid #e5e7eb',
        }}>
          <div style={{ fontSize: 32, marginBottom: 8 }}>😌</div>
          No duty assigned for today.
        </div>
      ) : (
        duties.map(duty => {
          const cfg = STATUS_CONFIG[duty.status] || STATUS_CONFIG.draft
          return (
            <div key={duty.id} style={{
              background: '#fff', borderRadius: 12, overflow: 'hidden',
              border: '1px solid #e5e7eb', marginBottom: 12,
              boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
            }}>
              {/* Status bar */}
              <div style={{ background: cfg.bg, padding: '6px 14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: cfg.color }}>
                  {cfg.label}
                </span>
                {duty.acknowledged_at && (
                  <span style={{ fontSize: 11, color: '#9ca3af' }}>
                    Acked {new Date(duty.acknowledged_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                  </span>
                )}
              </div>

              {/* Duty details */}
              <div style={{ padding: '1rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '0.75rem' }}>
                  <DutyField icon="🚌" label="Vehicle" value={duty.registration_no} />
                  <DutyField icon="🛣" label="Route" value={duty.route_name} />
                  <DutyField icon="🕐" label="Shift start" value={duty.shift_start} />
                  <DutyField icon="🕕" label="Shift end" value={duty.shift_end} />
                </div>

                {/* Acknowledge button */}
                {duty.status === 'published' && (
                  <button
                    onClick={() => handleAcknowledge(duty.id)}
                    disabled={ackLoading === duty.id}
                    style={{
                      width: '100%', padding: '11px',
                      background: ackLoading === duty.id ? '#93c5fd' : '#2563eb',
                      color: '#fff', border: 'none', borderRadius: 9,
                      fontSize: 15, fontWeight: 600,
                      cursor: ackLoading === duty.id ? 'not-allowed' : 'pointer',
                      marginTop: 4,
                    }}
                  >
                    {ackLoading === duty.id ? 'Confirming...' : '✓ Acknowledge duty'}
                  </button>
                )}

                {duty.status === 'acknowledged' && (
                  <div style={{
                    width: '100%', padding: '11px', background: '#f0fdf4',
                    border: '1px solid #bbf7d0', borderRadius: 9,
                    textAlign: 'center', fontSize: 14, color: '#16a34a', fontWeight: 500,
                    marginTop: 4,
                  }}>
                    ✓ You have acknowledged this duty
                  </div>
                )}
              </div>
            </div>
          )
        })
      )}

      {/* Upcoming duties */}
      <UpcomingDuties today={today} />
    </div>
  )
}

function DutyField({ icon, label, value }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: '#9ca3af', marginBottom: 2 }}>{icon} {label}</div>
      <div style={{ fontSize: 14, fontWeight: 500, color: '#111827' }}>{value || '—'}</div>
    </div>
  )
}

function UpcomingDuties({ today }) {
  const [upcoming, setUpcoming] = useState([])

  useEffect(() => {
    schedulingApi.getDuties().then(data => {
      const future = data.filter(d => d.date > today).slice(0, 5)
      setUpcoming(future)
    }).catch(() => {})
  }, [today])

  if (upcoming.length === 0) return null

  return (
    <div style={{ marginTop: '1.5rem' }}>
      <h3 style={{ fontSize: 15, fontWeight: 600, marginBottom: '0.75rem', color: '#374151' }}>
        Upcoming duties
      </h3>
      {upcoming.map(d => (
        <div key={d.id} style={{
          background: '#fff', borderRadius: 9, padding: '0.75rem 1rem',
          border: '1px solid #e5e7eb', marginBottom: 6,
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 500 }}>{d.route_name}</div>
            <div style={{ fontSize: 12, color: '#6b7280' }}>{d.registration_no} · {d.shift_start}–{d.shift_end}</div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 12, fontWeight: 500, color: '#374151' }}>
              {new Date(d.date + 'T00:00:00').toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' })}
            </div>
            <span style={{
              fontSize: 11, padding: '1px 7px', borderRadius: 99,
              background: d.status === 'published' ? '#dbeafe' : '#f3f4f6',
              color: d.status === 'published' ? '#1e40af' : '#6b7280',
            }}>{d.status}</span>
          </div>
        </div>
      ))}
    </div>
  )
}
