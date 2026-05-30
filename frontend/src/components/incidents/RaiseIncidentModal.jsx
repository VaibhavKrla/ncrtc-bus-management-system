import { useState, useEffect } from 'react'
import { incidentsApi } from '../../services/incidentsApi'
import { avlsApi } from '../../services/avlsApi'
import toast from 'react-hot-toast'
import useAuthStore from '../../store/authStore'

const inputStyle = {
  width: '100%', padding: '8px 10px', borderRadius: 7,
  border: '1px solid #d1d5db', fontSize: 14, outline: 'none',
  boxSizing: 'border-box', background: '#fff',
}

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: '1rem' }}>
      <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 5, color: '#374151' }}>
        {label}
      </label>
      {children}
    </div>
  )
}

const SEVERITY_COLORS = { P1: '#dc2626', P2: '#d97706', P3: '#2563eb' }

export default function RaiseIncidentModal({ onClose, onSave }) {
  const { user } = useAuthStore()
  const [vehicles, setVehicles] = useState([])
  const [loading, setLoading] = useState(false)
  const [form, setForm] = useState({
    title: '', description: '', type: 'breakdown',
    severity: 'P2', vehicle_id: '', lat: '', lng: '',
  })

  useEffect(() => {
    avlsApi.getVehicles().then(setVehicles).catch(() => {})
  }, [])

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.title.trim()) { toast.error('Title is required'); return }
    setLoading(true)
    try {
      await incidentsApi.create({
        title: form.title,
        description: form.description || null,
        type: form.type,
        severity: form.severity,
        vehicle_id: form.vehicle_id ? parseInt(form.vehicle_id) : null,
        lat: form.lat ? parseFloat(form.lat) : null,
        lng: form.lng ? parseFloat(form.lng) : null,
        is_panic: false,
      })
      toast.success('Incident raised')
      onSave()
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to raise incident')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 300,
    }}>
      <div style={{
        background: '#fff', borderRadius: 12, padding: '1.75rem',
        width: 500, maxHeight: '90vh', overflowY: 'auto',
        boxShadow: '0 8px 32px rgba(0,0,0,0.18)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
          <h2 style={{ fontSize: 17, fontWeight: 600 }}>⚠️ Raise Incident</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: '#6b7280' }}>×</button>
        </div>

        <form onSubmit={handleSubmit}>
          <Field label="Title">
            <input value={form.title} onChange={e => set('title', e.target.value)}
              placeholder="Brief description of the issue" style={inputStyle} required />
          </Field>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Field label="Type">
              <select value={form.type} onChange={e => set('type', e.target.value)} style={inputStyle}>
                <option value="breakdown">Breakdown</option>
                <option value="accident">Accident</option>
                <option value="complaint">Complaint</option>
                <option value="other">Other</option>
              </select>
            </Field>

            <Field label="Severity">
              <select value={form.severity} onChange={e => set('severity', e.target.value)} style={{
                ...inputStyle, color: SEVERITY_COLORS[form.severity], fontWeight: 600,
              }}>
                <option value="P1">P1 — Critical</option>
                <option value="P2">P2 — Major</option>
                <option value="P3">P3 — Minor</option>
              </select>
            </Field>
          </div>

          <Field label="Description (optional)">
            <textarea value={form.description} onChange={e => set('description', e.target.value)}
              placeholder="Additional details..." rows={3}
              style={{ ...inputStyle, resize: 'vertical' }} />
          </Field>

          <Field label="Vehicle (optional)">
            <select value={form.vehicle_id} onChange={e => set('vehicle_id', e.target.value)} style={inputStyle}>
              <option value="">No vehicle / unknown</option>
              {vehicles.map(v => <option key={v.id} value={v.id}>{v.registration_no} — {v.model}</option>)}
            </select>
          </Field>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Field label="Lat (optional)">
              <input type="number" step="any" value={form.lat}
                onChange={e => set('lat', e.target.value)}
                placeholder="28.6274" style={inputStyle} />
            </Field>
            <Field label="Lng (optional)">
              <input type="number" step="any" value={form.lng}
                onChange={e => set('lng', e.target.value)}
                placeholder="77.3717" style={inputStyle} />
            </Field>
          </div>

          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: '0.5rem' }}>
            <button type="button" onClick={onClose} style={{
              padding: '8px 16px', borderRadius: 8, border: '1px solid #d1d5db',
              background: '#fff', fontSize: 14, cursor: 'pointer',
            }}>Cancel</button>
            <button type="submit" disabled={loading} style={{
              padding: '8px 20px', borderRadius: 8, border: 'none',
              background: loading ? '#93c5fd' : '#dc2626',
              color: '#fff', fontSize: 14, fontWeight: 500,
              cursor: loading ? 'not-allowed' : 'pointer',
            }}>
              {loading ? 'Raising...' : 'Raise incident'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
