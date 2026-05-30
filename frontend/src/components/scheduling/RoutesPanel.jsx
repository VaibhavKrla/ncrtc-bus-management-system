import { useState, useEffect } from 'react'
import { schedulingApi } from '../../services/schedulingApi'
import toast from 'react-hot-toast'

const inputStyle = {
  width: '100%', padding: '8px 10px', borderRadius: 7,
  border: '1px solid #d1d5db', fontSize: 14, outline: 'none',
  boxSizing: 'border-box',
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

function RouteFormModal({ depots, stops, existing, onClose, onSave }) {
  const [form, setForm] = useState({
    name: existing?.name || '',
    code: existing?.code || '',
    depot_id: existing?.depot_id || '',
    selectedStops: existing?.stops?.map(s => ({ stop_id: s.id, sequence: s.sequence, scheduled_time: s.scheduled_time || '' })) || [],
  })
  const [loading, setLoading] = useState(false)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const addStop = (stopId) => {
    if (!stopId) return
    const id = parseInt(stopId)
    if (form.selectedStops.find(s => s.stop_id === id)) return
    setForm(f => ({
      ...f,
      selectedStops: [...f.selectedStops, { stop_id: id, sequence: f.selectedStops.length + 1, scheduled_time: '' }]
    }))
  }

  const removeStop = (idx) => {
    setForm(f => ({
      ...f,
      selectedStops: f.selectedStops
        .filter((_, i) => i !== idx)
        .map((s, i) => ({ ...s, sequence: i + 1 }))
    }))
  }

  const updateStopTime = (idx, time) => {
    setForm(f => ({
      ...f,
      selectedStops: f.selectedStops.map((s, i) => i === idx ? { ...s, scheduled_time: time } : s)
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.name || !form.code || !form.depot_id) {
      toast.error('Name, code and depot are required')
      return
    }
    setLoading(true)
    try {
      const payload = {
        name: form.name,
        code: form.code,
        depot_id: parseInt(form.depot_id),
        stops: form.selectedStops,
      }
      if (existing) {
        await schedulingApi.updateRoute(existing.id, payload)
        toast.success('Route updated')
      } else {
        await schedulingApi.createRoute(payload)
        toast.success('Route created')
      }
      onSave()
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save route')
    } finally {
      setLoading(false)
    }
  }

  const stopMap = Object.fromEntries(stops.map(s => [s.id, s]))

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 300,
    }}>
      <div style={{
        background: '#fff', borderRadius: 12, padding: '1.75rem',
        width: 560, maxHeight: '90vh', overflowY: 'auto',
        boxShadow: '0 8px 32px rgba(0,0,0,0.18)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
          <h2 style={{ fontSize: 17, fontWeight: 600 }}>{existing ? 'Edit Route' : 'Create Route'}</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: '#6b7280' }}>×</button>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Field label="Route name">
              <input value={form.name} onChange={e => set('name', e.target.value)}
                placeholder="e.g. Anand Vihar Express" style={inputStyle} required />
            </Field>
            <Field label="Code">
              <input value={form.code} onChange={e => set('code', e.target.value)}
                placeholder="e.g. R001" style={inputStyle} required />
            </Field>
          </div>

          <Field label="Depot">
            <select value={form.depot_id} onChange={e => set('depot_id', e.target.value)} style={inputStyle} required>
              <option value="">Select depot...</option>
              {depots.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
            </select>
          </Field>

          {/* Stop builder */}
          <Field label="Stops (in order)">
            <select onChange={e => { addStop(e.target.value); e.target.value = '' }}
              style={{ ...inputStyle, marginBottom: 8 }}>
              <option value="">+ Add stop...</option>
              {stops.map(s => <option key={s.id} value={s.id}>{s.name} ({s.code})</option>)}
            </select>
            {form.selectedStops.length === 0 ? (
              <div style={{ fontSize: 13, color: '#9ca3af', padding: '8px 0' }}>No stops added yet.</div>
            ) : (
              form.selectedStops.map((rs, idx) => {
                const stop = stopMap[rs.stop_id]
                return (
                  <div key={idx} style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    padding: '6px 10px', borderRadius: 7, background: '#f8fafc',
                    border: '1px solid #e5e7eb', marginBottom: 4,
                  }}>
                    <span style={{ fontSize: 12, color: '#9ca3af', fontWeight: 600, width: 20 }}>{idx + 1}</span>
                    <span style={{ flex: 1, fontSize: 13 }}>{stop?.name || `Stop ${rs.stop_id}`}</span>
                    <input
                      type="time" value={rs.scheduled_time}
                      onChange={e => updateStopTime(idx, e.target.value)}
                      style={{ padding: '3px 6px', borderRadius: 5, border: '1px solid #d1d5db', fontSize: 12, width: 90 }}
                    />
                    <button type="button" onClick={() => removeStop(idx)}
                      style={{ background: 'none', border: 'none', color: '#dc2626', cursor: 'pointer', fontSize: 16 }}>×</button>
                  </div>
                )
              })
            )}
          </Field>

          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button type="button" onClick={onClose} style={{
              padding: '8px 16px', borderRadius: 8, border: '1px solid #d1d5db',
              background: '#fff', fontSize: 14, cursor: 'pointer',
            }}>Cancel</button>
            <button type="submit" disabled={loading} style={{
              padding: '8px 20px', borderRadius: 8, border: 'none',
              background: loading ? '#93c5fd' : '#2563eb',
              color: '#fff', fontSize: 14, fontWeight: 500, cursor: loading ? 'not-allowed' : 'pointer',
            }}>
              {loading ? 'Saving...' : existing ? 'Update' : 'Create route'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function RoutesPanel({ depotId, depots }) {
  const [routes, setRoutes] = useState([])
  const [stops, setStops] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editRoute, setEditRoute] = useState(null)
  const [expanded, setExpanded] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const [r, s] = await Promise.all([
        schedulingApi.getRoutes(depotId),
        schedulingApi.getStops(),
      ])
      setRoutes(r)
      setStops(s)
    } catch { toast.error('Failed to load routes') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [depotId])

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this route?')) return
    try {
      await schedulingApi.deleteRoute(id)
      toast.success('Route deleted')
      load()
    } catch { toast.error('Cannot delete — may have active duties') }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div style={{ fontSize: 14, color: '#6b7280' }}>{routes.length} route{routes.length !== 1 ? 's' : ''}</div>
        <button onClick={() => { setEditRoute(null); setShowForm(true) }} style={{
          padding: '7px 16px', borderRadius: 7, border: 'none',
          background: '#2563eb', color: '#fff', fontSize: 13, fontWeight: 500, cursor: 'pointer',
        }}>+ New route</button>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem', color: '#9ca3af' }}>Loading...</div>
      ) : routes.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '2rem', color: '#9ca3af', background: '#fff', borderRadius: 10, border: '1px solid #e5e7eb' }}>
          No routes yet. Create one above.
        </div>
      ) : routes.map(r => (
        <div key={r.id} style={{
          background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10,
          marginBottom: 8, overflow: 'hidden',
        }}>
          <div
            style={{ padding: '0.875rem 1rem', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
            onClick={() => setExpanded(expanded === r.id ? null : r.id)}
          >
            <div>
              <span style={{ fontWeight: 600, fontSize: 14, marginRight: 8 }}>{r.name}</span>
              <span style={{ fontSize: 12, color: '#6b7280', marginRight: 8 }}>#{r.code}</span>
              <span style={{
                fontSize: 11, padding: '2px 7px', borderRadius: 99,
                background: r.is_active ? '#dcfce7' : '#f3f4f6',
                color: r.is_active ? '#166534' : '#6b7280',
              }}>{r.is_active ? 'Active' : 'Inactive'}</span>
            </div>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <span style={{ fontSize: 12, color: '#9ca3af' }}>{r.stops?.length || 0} stops</span>
              <button onClick={e => { e.stopPropagation(); setEditRoute(r); setShowForm(true) }}
                style={{ padding: '4px 10px', borderRadius: 6, border: '1px solid #d1d5db', background: '#fff', fontSize: 12, cursor: 'pointer' }}>
                Edit
              </button>
              <button onClick={e => { e.stopPropagation(); handleDelete(r.id) }}
                style={{ padding: '4px 8px', borderRadius: 6, border: '1px solid #fca5a5', background: '#fff', color: '#dc2626', fontSize: 12, cursor: 'pointer' }}>
                ✕
              </button>
              <span style={{ color: '#9ca3af', fontSize: 14 }}>{expanded === r.id ? '▲' : '▼'}</span>
            </div>
          </div>

          {expanded === r.id && (
            <div style={{ borderTop: '1px solid #f3f4f6', padding: '0.75rem 1rem', background: '#fafafa' }}>
              {r.stops?.length === 0 ? (
                <div style={{ fontSize: 13, color: '#9ca3af' }}>No stops defined.</div>
              ) : (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {r.stops.map((s, i) => (
                    <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
                      <span style={{ color: '#9ca3af' }}>{s.sequence}.</span>
                      <span style={{ background: '#eff6ff', color: '#1d4ed8', padding: '2px 8px', borderRadius: 6 }}>
                        {s.name}
                        {s.scheduled_time && <span style={{ color: '#60a5fa', marginLeft: 4 }}>@{s.scheduled_time}</span>}
                      </span>
                      {i < r.stops.length - 1 && <span style={{ color: '#d1d5db' }}>→</span>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      ))}

      {showForm && (
        <RouteFormModal
          depots={depots}
          stops={stops}
          existing={editRoute}
          onClose={() => { setShowForm(false); setEditRoute(null) }}
          onSave={load}
        />
      )}
    </div>
  )
}
