import { useState } from 'react'
import { incidentsApi } from '../../services/incidentsApi'
import toast from 'react-hot-toast'
import useAuthStore from '../../store/authStore'

const inputStyle = {
  width: '100%', padding: '9px 10px', borderRadius: 8,
  border: '1px solid #d1d5db', fontSize: 14, outline: 'none',
  boxSizing: 'border-box', background: '#fff',
}

export default function DriverIncidentTab() {
  const { user } = useAuthStore()
  const [panicLoading, setPanicLoading] = useState(false)
  const [panicDone, setPanicDone] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ title: '', description: '', type: 'breakdown', severity: 'P2' })
  const [formLoading, setFormLoading] = useState(false)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handlePanic = async () => {
    if (!window.confirm('🚨 Confirm PANIC — this will immediately alert control room with P1 priority!')) return
    setPanicLoading(true)
    try {
      // Try to get current location
      let lat = null, lng = null
      try {
        const pos = await new Promise((res, rej) =>
          navigator.geolocation.getCurrentPosition(res, rej, { timeout: 3000 })
        )
        lat = pos.coords.latitude
        lng = pos.coords.longitude
      } catch {}

      await incidentsApi.panic({ lat, lng })
      setPanicDone(true)
      toast.success('🚨 Panic alert sent to control room!')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send panic alert')
    } finally {
      setPanicLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.title.trim()) { toast.error('Title required'); return }
    setFormLoading(true)
    try {
      await incidentsApi.create({
        title: form.title,
        description: form.description || null,
        type: form.type,
        severity: form.severity,
        is_panic: false,
      })
      toast.success('Incident reported')
      setForm({ title: '', description: '', type: 'breakdown', severity: 'P2' })
      setShowForm(false)
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to report incident')
    } finally {
      setFormLoading(false)
    }
  }

  return (
    <div style={{ padding: '1.25rem' }}>
      {/* PANIC BUTTON */}
      <div style={{
        background: '#fff', borderRadius: 14, padding: '1.5rem',
        border: '1px solid #fecaca', marginBottom: '1.25rem', textAlign: 'center',
      }}>
        <div style={{ fontSize: 13, color: '#6b7280', marginBottom: '1rem' }}>
          In case of emergency — tap below to immediately alert the control room
        </div>

        {panicDone ? (
          <div style={{
            padding: '1rem', background: '#fef2f2', borderRadius: 12,
            border: '1px solid #fecaca',
          }}>
            <div style={{ fontSize: 24, marginBottom: 6 }}>🚨</div>
            <div style={{ fontSize: 15, fontWeight: 700, color: '#dc2626' }}>Panic alert sent!</div>
            <div style={{ fontSize: 13, color: '#6b7280', marginTop: 4 }}>
              Control room has been notified. Stay calm, help is on the way.
            </div>
            <button
              onClick={() => setPanicDone(false)}
              style={{ marginTop: '0.875rem', fontSize: 13, color: '#6b7280', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline' }}
            >
              Reset
            </button>
          </div>
        ) : (
          <button
            onClick={handlePanic}
            disabled={panicLoading}
            style={{
              width: 140, height: 140, borderRadius: '50%',
              background: panicLoading ? '#fca5a5' : '#dc2626',
              border: '6px solid #fecaca',
              color: '#fff', fontSize: 15, fontWeight: 800,
              cursor: panicLoading ? 'not-allowed' : 'pointer',
              boxShadow: '0 0 0 4px #fee2e2, 0 8px 24px rgba(220,38,38,0.4)',
              display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center', gap: 4,
              margin: '0 auto',
              transition: 'transform 0.1s',
            }}
            onMouseDown={e => e.currentTarget.style.transform = 'scale(0.96)'}
            onMouseUp={e => e.currentTarget.style.transform = 'scale(1)'}
          >
            <span style={{ fontSize: 28 }}>🚨</span>
            {panicLoading ? 'Sending...' : 'PANIC'}
          </button>
        )}
      </div>

      {/* Report incident */}
      {!showForm ? (
        <button
          onClick={() => setShowForm(true)}
          style={{
            width: '100%', padding: '12px', borderRadius: 10,
            border: '1px solid #d1d5db', background: '#fff',
            fontSize: 14, fontWeight: 500, cursor: 'pointer', color: '#374151',
          }}
        >
          ⚠️ Report a non-emergency incident
        </button>
      ) : (
        <div style={{ background: '#fff', borderRadius: 12, padding: '1.25rem', border: '1px solid #e5e7eb' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
            <div style={{ fontSize: 15, fontWeight: 600 }}>Report Incident</div>
            <button onClick={() => setShowForm(false)} style={{ background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', color: '#9ca3af' }}>×</button>
          </div>

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: '0.875rem' }}>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 5 }}>Title</label>
              <input value={form.title} onChange={e => set('title', e.target.value)}
                placeholder="What happened?" style={inputStyle} required />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: '0.875rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 5 }}>Type</label>
                <select value={form.type} onChange={e => set('type', e.target.value)} style={inputStyle}>
                  <option value="breakdown">Breakdown</option>
                  <option value="accident">Accident</option>
                  <option value="complaint">Complaint</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 5 }}>Severity</label>
                <select value={form.severity} onChange={e => set('severity', e.target.value)} style={inputStyle}>
                  <option value="P1">P1 — Critical</option>
                  <option value="P2">P2 — Major</option>
                  <option value="P3">P3 — Minor</option>
                </select>
              </div>
            </div>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 5 }}>Details (optional)</label>
              <textarea value={form.description} onChange={e => set('description', e.target.value)}
                placeholder="Describe what happened..." rows={3}
                style={{ ...inputStyle, resize: 'none' }} />
            </div>

            <div style={{ display: 'flex', gap: 8 }}>
              <button type="button" onClick={() => setShowForm(false)} style={{
                flex: 1, padding: '10px', borderRadius: 8, border: '1px solid #d1d5db',
                background: '#fff', fontSize: 14, cursor: 'pointer',
              }}>Cancel</button>
              <button type="submit" disabled={formLoading} style={{
                flex: 2, padding: '10px', borderRadius: 8, border: 'none',
                background: formLoading ? '#fca5a5' : '#dc2626',
                color: '#fff', fontSize: 14, fontWeight: 600,
                cursor: formLoading ? 'not-allowed' : 'pointer',
              }}>
                {formLoading ? 'Submitting...' : 'Submit report'}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
