import { useState, useEffect } from 'react'
import { schedulingApi } from '../../services/schedulingApi'
import toast from 'react-hot-toast'

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

export default function AssignDutyModal({ depotId, prefillDriver = null, prefillDate = null, existing = null, onClose, onSave }) {
  const [drivers, setDrivers] = useState([])
  const [vehicles, setVehicles] = useState([])
  const [routes, setRoutes] = useState([])
  const [loading, setLoading] = useState(false)

  const [form, setForm] = useState({
    driver_id: prefillDriver || existing?.driver_id || '',
    vehicle_id: existing?.vehicle_id || '',
    route_id: existing?.route_id || '',
    date: prefillDate || existing?.date || new Date().toISOString().slice(0, 10),
    shift_start: existing?.shift_start || '06:00',
    shift_end: existing?.shift_end || '14:00',
  })

  useEffect(() => {
    Promise.all([
      schedulingApi.getDrivers(depotId),
      schedulingApi.getVehicles(depotId),
      schedulingApi.getRoutes(depotId),
    ]).then(([d, v, r]) => {
      setDrivers(d)
      setVehicles(v)
      setRoutes(r)
    })
  }, [depotId])

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.driver_id || !form.vehicle_id || !form.route_id) {
      toast.error('Driver, vehicle and route are required')
      return
    }
    setLoading(true)
    try {
      const payload = {
        driver_id: parseInt(form.driver_id),
        vehicle_id: parseInt(form.vehicle_id),
        route_id: parseInt(form.route_id),
        date: form.date,
        shift_start: form.shift_start,
        shift_end: form.shift_end,
      }
      if (existing) {
        await schedulingApi.updateDuty(existing.id, payload)
        toast.success('Duty updated')
      } else {
        await schedulingApi.createDuty(payload)
        toast.success('Duty created')
      }
      onSave()
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save duty')
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
        width: 480, maxHeight: '90vh', overflowY: 'auto',
        boxShadow: '0 8px 32px rgba(0,0,0,0.18)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <h2 style={{ fontSize: 17, fontWeight: 600 }}>
            {existing ? 'Edit Duty' : 'Assign Duty'}
          </h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: '#6b7280' }}>×</button>
        </div>

        <form onSubmit={handleSubmit}>
          <Field label="Driver">
            <select value={form.driver_id} onChange={e => set('driver_id', e.target.value)} style={inputStyle} required>
              <option value="">Select driver...</option>
              {drivers.map(d => <option key={d.id} value={d.id}>{d.full_name}</option>)}
            </select>
          </Field>

          <Field label="Vehicle">
            <select value={form.vehicle_id} onChange={e => set('vehicle_id', e.target.value)} style={inputStyle} required>
              <option value="">Select vehicle...</option>
              {vehicles.map(v => <option key={v.id} value={v.id}>{v.registration_no} — {v.model}</option>)}
            </select>
          </Field>

          <Field label="Route">
            <select value={form.route_id} onChange={e => set('route_id', e.target.value)} style={inputStyle} required>
              <option value="">Select route...</option>
              {routes.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </Field>

          <Field label="Date">
            <input type="date" value={form.date} onChange={e => set('date', e.target.value)} style={inputStyle} required />
          </Field>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Field label="Shift start">
              <input type="time" value={form.shift_start} onChange={e => set('shift_start', e.target.value)} style={inputStyle} required />
            </Field>
            <Field label="Shift end">
              <input type="time" value={form.shift_end} onChange={e => set('shift_end', e.target.value)} style={inputStyle} required />
            </Field>
          </div>

          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: '0.5rem' }}>
            <button type="button" onClick={onClose} style={{
              padding: '8px 16px', borderRadius: 8, border: '1px solid #d1d5db',
              background: '#fff', fontSize: 14, cursor: 'pointer',
            }}>Cancel</button>
            <button type="submit" disabled={loading} style={{
              padding: '8px 20px', borderRadius: 8, border: 'none',
              background: loading ? '#93c5fd' : '#2563eb',
              color: '#fff', fontSize: 14, fontWeight: 500,
              cursor: loading ? 'not-allowed' : 'pointer',
            }}>
              {loading ? 'Saving...' : existing ? 'Update' : 'Assign'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
