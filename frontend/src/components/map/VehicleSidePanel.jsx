import { useState, useEffect } from 'react'
import { Polyline, useMap } from 'react-leaflet'
import { avlsApi } from '../../services/avlsApi'

const STATUS_COLORS = {
  active: '#16a34a',
  idle: '#ca8a04',
  maintenance: '#9333ea',
  breakdown: '#dc2626',
}

export default function VehicleSidePanel({ vehicle, onClose }) {
  const [trail, setTrail] = useState([])
  const [trailLoading, setTrailLoading] = useState(true)

  useEffect(() => {
    if (!vehicle) return
    setTrailLoading(true)
    avlsApi.getTrail(vehicle.vehicle_id, 30)
      .then(pings => setTrail(pings.map(p => [p.lat, p.lng])))
      .finally(() => setTrailLoading(false))
  }, [vehicle?.vehicle_id])

  if (!vehicle) return null

  const statusColor = STATUS_COLORS[vehicle.status] || '#6b7280'
  const timeSince = vehicle.last_ping
    ? Math.round((Date.now() - new Date(vehicle.last_ping)) / 1000)
    : null

  return (
    <>
      {/* Trail polyline rendered on map */}
      {trail.length > 1 && (
        <Polyline
          positions={trail}
          pathOptions={{ color: '#3b82f6', weight: 3, opacity: 0.7, dashArray: '6 4' }}
        />
      )}

      {/* Side panel UI */}
      <div style={{
        position: 'absolute', top: 12, right: 12, width: 280, zIndex: 1000,
        background: '#fff', borderRadius: 12, boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
        overflow: 'hidden',
      }}>
        {/* Header */}
        <div style={{ background: '#1e293b', color: '#fff', padding: '0.875rem 1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ fontSize: 15, fontWeight: 600 }}>{vehicle.registration_no}</div>
              <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>{vehicle.model}</div>
            </div>
            <button
              onClick={onClose}
              style={{ background: 'none', border: 'none', color: '#94a3b8', fontSize: 18, cursor: 'pointer', padding: 0, lineHeight: 1 }}
            >×</button>
          </div>
          <div style={{ marginTop: 8 }}>
            <span style={{
              fontSize: 11, padding: '2px 8px', borderRadius: 99,
              background: statusColor, color: '#fff', fontWeight: 500,
            }}>
              {vehicle.status.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Details */}
        <div style={{ padding: '0.875rem 1rem' }}>
          <Row icon="🏠" label="Depot" value={vehicle.depot_name} />
          <Row icon="👤" label="Driver" value={vehicle.driver_name || '—'} />
          <Row icon="🛣️" label="Route" value={vehicle.route_name || '—'} />
          <Row icon="💨" label="Speed" value={`${vehicle.speed_kmh} km/h`} />
          <Row icon="🧭" label="Heading" value={`${Math.round(vehicle.heading)}°`} />
          <Row
            icon="🕐"
            label="Last ping"
            value={timeSince !== null ? `${timeSince}s ago` : '—'}
          />

          <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid #f3f4f6' }}>
            <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 4 }}>
              📍 {vehicle.lat.toFixed(5)}, {vehicle.lng.toFixed(5)}
            </div>
            {trailLoading ? (
              <div style={{ fontSize: 12, color: '#9ca3af' }}>Loading trail...</div>
            ) : (
              <div style={{ fontSize: 12, color: '#3b82f6' }}>
                🗺 Showing last 30 min trail ({trail.length} points)
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}

function Row({ icon, label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 13 }}>
      <span style={{ color: '#6b7280' }}>{icon} {label}</span>
      <span style={{ fontWeight: 500, color: '#111827' }}>{value}</span>
    </div>
  )
}
