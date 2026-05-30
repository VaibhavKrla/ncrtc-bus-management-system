import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, Polyline, Marker, useMap } from 'react-leaflet'
import L from 'leaflet'
import { useNavigate } from 'react-router-dom'
import Layout from '../components/common/Layout'
import { avlsApi } from '../services/avlsApi'
import toast from 'react-hot-toast'

// Fix Leaflet icons
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

function makeStartEndIcon(type) {
  const color = type === 'start' ? '#16a34a' : '#dc2626'
  const label = type === 'start' ? 'S' : 'E'
  return L.divIcon({
    html: `<div style="width:22px;height:22px;border-radius:50%;background:${color};
      color:#fff;display:flex;align-items:center;justify-content:center;
      font-size:11px;font-weight:700;border:2px solid white;
      box-shadow:0 2px 4px rgba(0,0,0,0.3)">${label}</div>`,
    className: '',
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  })
}

function FitBounds({ pings }) {
  const map = useMap()
  useEffect(() => {
    if (pings.length < 2) return
    const lats = pings.map(p => p[0])
    const lngs = pings.map(p => p[1])
    map.fitBounds([
      [Math.min(...lats) - 0.005, Math.min(...lngs) - 0.005],
      [Math.max(...lats) + 0.005, Math.max(...lngs) + 0.005],
    ], { padding: [40, 40] })
  }, [pings])
  return null
}

export default function HistoryPage() {
  const navigate = useNavigate()
  const [vehicles, setVehicles] = useState([])
  const [selectedVehicle, setSelectedVehicle] = useState('')
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().slice(0, 10))
  const [history, setHistory] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    avlsApi.getVehicles().then(setVehicles)
  }, [])

  const loadHistory = async () => {
    if (!selectedVehicle || !selectedDate) {
      toast.error('Select a vehicle and date')
      return
    }
    setLoading(true)
    try {
      const data = await avlsApi.getHistory(selectedVehicle, selectedDate)
      setHistory(data)
      if (data.pings.length === 0) toast('No GPS data for this vehicle on this date', { icon: 'ℹ️' })
    } catch {
      toast.error('Failed to load history')
    } finally {
      setLoading(false)
    }
  }

  const positions = history?.pings?.map(p => [p.lat, p.lng]) || []
  const totalDistance = history?.pings?.length > 1
    ? (history.pings.length * 0.05).toFixed(1)
    : null
  const avgSpeed = history?.pings?.length
    ? (history.pings.reduce((s, p) => s + p.speed_kmh, 0) / history.pings.length).toFixed(1)
    : null

  return (
    <Layout>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 2 }}>📅 Trip History</h1>
          <p style={{ fontSize: 13, color: '#6b7280' }}>View full-day GPS path for any vehicle</p>
        </div>
        <button
          onClick={() => navigate('/map')}
          style={{
            padding: '8px 16px', borderRadius: 8, border: '1px solid #d1d5db',
            background: '#fff', fontSize: 13, cursor: 'pointer',
          }}
        >← Live Map</button>
      </div>

      {/* Controls */}
      <div style={{
        background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10,
        padding: '1rem', marginBottom: '1rem',
        display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap',
      }}>
        <div style={{ flex: 1, minWidth: 200 }}>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 5 }}>Vehicle</label>
          <select
            value={selectedVehicle}
            onChange={e => setSelectedVehicle(e.target.value)}
            style={{
              width: '100%', padding: '8px 10px', borderRadius: 7,
              border: '1px solid #d1d5db', fontSize: 14,
            }}
          >
            <option value="">Select vehicle...</option>
            {vehicles.map(v => (
              <option key={v.id} value={v.id}>{v.registration_no} — {v.model}</option>
            ))}
          </select>
        </div>

        <div style={{ flex: 1, minWidth: 160 }}>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 500, marginBottom: 5 }}>Date</label>
          <input
            type="date"
            value={selectedDate}
            onChange={e => setSelectedDate(e.target.value)}
            max={new Date().toISOString().slice(0, 10)}
            style={{
              width: '100%', padding: '8px 10px', borderRadius: 7,
              border: '1px solid #d1d5db', fontSize: 14,
            }}
          />
        </div>

        <button
          onClick={loadHistory}
          disabled={loading}
          style={{
            padding: '9px 20px', borderRadius: 8, border: 'none',
            background: loading ? '#93c5fd' : '#2563eb',
            color: '#fff', fontSize: 14, fontWeight: 500,
            cursor: loading ? 'not-allowed' : 'pointer', flexShrink: 0,
          }}
        >
          {loading ? 'Loading...' : 'Show history'}
        </button>
      </div>

      {/* Stats bar (shows after load) */}
      {history && positions.length > 0 && (
        <div style={{ display: 'flex', gap: 8, marginBottom: '0.875rem', flexWrap: 'wrap' }}>
          {[
            { label: 'Vehicle', value: history.registration_no },
            { label: 'Date', value: history.date },
            { label: 'GPS points', value: history.pings.length },
            { label: 'Avg speed', value: `${avgSpeed} km/h` },
          ].map(s => (
            <div key={s.label} style={{
              background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8,
              padding: '6px 14px',
            }}>
              <div style={{ fontSize: 11, color: '#9ca3af' }}>{s.label}</div>
              <div style={{ fontSize: 14, fontWeight: 600 }}>{s.value}</div>
            </div>
          ))}
        </div>
      )}

      {/* Map */}
      <div style={{ borderRadius: 12, overflow: 'hidden', border: '1px solid #e5e7eb' }}>
        <MapContainer
          center={[28.6274, 77.3717]}
          zoom={12}
          style={{ height: 'calc(100vh - 340px)', minHeight: 420 }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />

          {positions.length > 1 && (
            <>
              <FitBounds pings={positions} />
              <Polyline
                positions={positions}
                pathOptions={{ color: '#2563eb', weight: 4, opacity: 0.8 }}
              />
              {/* Start marker */}
              <Marker position={positions[0]} icon={makeStartEndIcon('start')} />
              {/* End marker */}
              <Marker position={positions[positions.length - 1]} icon={makeStartEndIcon('end')} />
            </>
          )}

          {history && positions.length === 0 && (
            <div style={{
              position: 'absolute', top: '50%', left: '50%',
              transform: 'translate(-50%,-50%)', zIndex: 999,
              background: '#fff', padding: '1rem 1.5rem', borderRadius: 8,
              fontSize: 14, color: '#6b7280', boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}>
              No GPS data for this vehicle on {history.date}
            </div>
          )}
        </MapContainer>
      </div>

      {/* Legend */}
      {positions.length > 0 && (
        <div style={{ marginTop: 8, display: 'flex', gap: 16, fontSize: 12, color: '#6b7280' }}>
          <span><span style={{ color: '#16a34a', fontWeight: 700 }}>S</span> = Start of day</span>
          <span><span style={{ color: '#dc2626', fontWeight: 700 }}>E</span> = Last recorded position</span>
          <span style={{ color: '#9ca3af', fontSize: 11 }}>
            ⚠️ Positions simulated by tick script for demo purposes
          </span>
        </div>
      )}
    </Layout>
  )
}
