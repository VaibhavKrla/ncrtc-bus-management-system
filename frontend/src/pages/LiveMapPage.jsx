import { useState, useEffect, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import Layout from '../components/common/Layout'
import VehicleSidePanel from '../components/map/VehicleSidePanel'
import { useLivePositions } from '../hooks/useLivePositions'
import { avlsApi } from '../services/avlsApi'
import { useNavigate } from 'react-router-dom'

// Fix Leaflet default icon broken in Vite/webpack
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

const STATUS_COLORS = {
  active: '#16a34a',
  idle: '#ca8a04',
  maintenance: '#9333ea',
  breakdown: '#dc2626',
}

function makeBusIcon(status, isSelected) {
  const color = STATUS_COLORS[status] || '#6b7280'
  const size = isSelected ? 36 : 28
  const svg = `
    <svg width="${size}" height="${size}" viewBox="0 0 36 36" xmlns="http://www.w3.org/2000/svg">
      <circle cx="18" cy="18" r="17" fill="${color}" stroke="white" stroke-width="${isSelected ? 3 : 2}" opacity="${isSelected ? 1 : 0.9}"/>
      <text x="18" y="24" text-anchor="middle" font-size="18" fill="white">🚌</text>
    </svg>`
  return L.divIcon({
    html: svg,
    className: '',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  })
}

// Component to keep map centered when vehicles load
function MapUpdater({ vehicles }) {
  const map = useMap()
  const initializedRef = useRef(false)
  useEffect(() => {
    if (!initializedRef.current && vehicles.length > 0) {
      const lats = vehicles.map(v => v.lat)
      const lngs = vehicles.map(v => v.lng)
      const bounds = [
        [Math.min(...lats) - 0.01, Math.min(...lngs) - 0.01],
        [Math.max(...lats) + 0.01, Math.max(...lngs) + 0.01],
      ]
      map.fitBounds(bounds, { padding: [40, 40] })
      initializedRef.current = true
    }
  }, [vehicles])
  return null
}

export default function LiveMapPage() {
  const navigate = useNavigate()
  const [depots, setDepots] = useState([])
  const [selectedDepot, setSelectedDepot] = useState(null)
  const [selectedVehicle, setSelectedVehicle] = useState(null)

  const { vehicles, loading, error, lastUpdated, mode } = useLivePositions(selectedDepot, 5000)

  useEffect(() => {
    avlsApi.getDepots().then(setDepots)
  }, [])

  const stats = {
    active: vehicles.filter(v => v.status === 'active').length,
    idle: vehicles.filter(v => v.status === 'idle').length,
    breakdown: vehicles.filter(v => v.status === 'breakdown').length,
  }

  return (
    <Layout>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 2 }}>🗺️ Live Map</h1>
          <p style={{ fontSize: 13, color: '#6b7280', display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
            Real-time vehicle positions
            {lastUpdated && (
              <span style={{ color: '#9ca3af' }}>
                · Updated {lastUpdated.toLocaleTimeString()}
              </span>
            )}
            <span style={{
              fontSize: 11, padding: '1px 7px', borderRadius: 99,
              background: mode === 'ws' ? '#dcfce7' : '#fef9c3',
              color: mode === 'ws' ? '#166534' : '#854d0e',
              border: `1px solid ${mode === 'ws' ? '#bbf7d0' : '#fde68a'}`,
            }}>
              {mode === 'ws' ? '⚡ WebSocket' : mode === 'polling' ? '🔄 Polling 5s' : '⏳ Connecting'}
            </span>
          </p>
        </div>
        <button
          onClick={() => navigate('/map/history')}
          style={{
            padding: '8px 16px', borderRadius: 8, border: '1px solid #d1d5db',
            background: '#fff', fontSize: 13, cursor: 'pointer', fontWeight: 500,
          }}
        >📅 Trip History</button>
      </div>

      {/* Stats bar */}
      <div style={{ display: 'flex', gap: 8, marginBottom: '0.875rem', flexWrap: 'wrap' }}>
        {[
          { label: 'Total', value: vehicles.length, color: '#1e293b' },
          { label: 'Active', value: stats.active, color: '#16a34a' },
          { label: 'Idle', value: stats.idle, color: '#ca8a04' },
          { label: 'Breakdown', value: stats.breakdown, color: '#dc2626' },
        ].map(s => (
          <div key={s.label} style={{
            background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8,
            padding: '6px 14px', display: 'flex', gap: 8, alignItems: 'center',
          }}>
            <span style={{ fontSize: 18, fontWeight: 700, color: s.color }}>{s.value}</span>
            <span style={{ fontSize: 12, color: '#6b7280' }}>{s.label}</span>
          </div>
        ))}

        {/* Depot filter */}
        <select
          value={selectedDepot || ''}
          onChange={e => {
            setSelectedDepot(e.target.value ? parseInt(e.target.value) : null)
            setSelectedVehicle(null)
          }}
          style={{
            marginLeft: 'auto', padding: '6px 12px', borderRadius: 8,
            border: '1px solid #d1d5db', fontSize: 13, background: '#fff',
          }}
        >
          <option value="">All depots</option>
          {depots.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
        </select>
      </div>

      {/* Map + side panel */}
      <div style={{ position: 'relative', borderRadius: 12, overflow: 'hidden', border: '1px solid #e5e7eb' }}>
        {loading && (
          <div style={{
            position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)',
            zIndex: 999, background: '#fff', padding: '6px 16px', borderRadius: 99,
            fontSize: 13, color: '#6b7280', boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          }}>
            Loading vehicles...
          </div>
        )}
        {error && (
          <div style={{
            position: 'absolute', top: 12, left: '50%', transform: 'translateX(-50%)',
            zIndex: 999, background: '#fef2f2', padding: '6px 16px', borderRadius: 99,
            fontSize: 13, color: '#dc2626', border: '1px solid #fecaca',
          }}>
            {error}
          </div>
        )}

        <MapContainer
          center={[28.6274, 77.3717]}
          zoom={12}
          style={{ height: 'calc(100vh - 260px)', minHeight: 480 }}
          zoomControl={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <MapUpdater vehicles={vehicles} />

          {vehicles.map(v => (
            <Marker
              key={v.vehicle_id}
              position={[v.lat, v.lng]}
              icon={makeBusIcon(v.status, selectedVehicle?.vehicle_id === v.vehicle_id)}
              eventHandlers={{
                click: () => setSelectedVehicle(v),
              }}
            >
              <Popup>
                <div style={{ fontSize: 13, minWidth: 160 }}>
                  <strong>{v.registration_no}</strong><br />
                  {v.depot_name}<br />
                  <span style={{ color: STATUS_COLORS[v.status] || '#6b7280' }}>
                    {v.status}
                  </span> · {v.speed_kmh} km/h
                  {v.driver_name && <><br />Driver: {v.driver_name}</>}
                  {v.route_name && <><br />Route: {v.route_name}</>}
                </div>
              </Popup>
            </Marker>
          ))}

          {/* Side panel with trail polyline */}
          {selectedVehicle && (
            <VehicleSidePanel
              vehicle={selectedVehicle}
              onClose={() => setSelectedVehicle(null)}
            />
          )}
        </MapContainer>

        {/* Legend */}
        <div style={{
          position: 'absolute', bottom: 24, left: 12, zIndex: 999,
          background: 'rgba(255,255,255,0.95)', borderRadius: 8,
          padding: '8px 12px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          fontSize: 12,
        }}>
          {Object.entries(STATUS_COLORS).map(([s, c]) => (
            <div key={s} style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
              <div style={{ width: 10, height: 10, borderRadius: '50%', background: c }} />
              <span style={{ textTransform: 'capitalize' }}>{s}</span>
            </div>
          ))}
        </div>
      </div>
    </Layout>
  )
}
