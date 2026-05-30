import { useState } from 'react'
import useAuthStore from '../store/authStore'
import DriverNotices from '../components/notices/DriverNotices'
import DriverDutyView from '../components/scheduling/DriverDutyView'
import DriverIncidentTab from '../components/incidents/DriverIncidentTab'

const TABS = [
  { id: 'duty',     label: 'My Duty',  icon: '📅' },
  { id: 'notices',  label: 'Notices',  icon: '📢' },
  { id: 'incident', label: 'Incident', icon: '⚠️' },
]

export default function DriverPortal() {
  const { user, logout } = useAuthStore()
  const [activeTab, setActiveTab] = useState('duty')

  return (
    <div style={{
      maxWidth: 480, margin: '0 auto', minHeight: '100vh',
      background: '#f3f4f6', display: 'flex', flexDirection: 'column',
    }}>
      <div style={{
        background: '#1e293b', color: '#fff', padding: '0.875rem 1rem',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        position: 'sticky', top: 0, zIndex: 50,
      }}>
        <div>
          <div style={{ fontSize: 15, fontWeight: 600 }}>🚌 NCRTC BMS</div>
          <div style={{ fontSize: 11, color: '#94a3b8' }}>{user?.full_name || user?.username}</div>
        </div>
        <button onClick={logout} style={{
          background: '#334155', border: 'none', color: '#94a3b8',
          padding: '5px 12px', borderRadius: 6, fontSize: 12, cursor: 'pointer',
        }}>Sign out</button>
      </div>

      <div style={{ flex: 1 }}>
        {activeTab === 'duty'     && <DriverDutyView />}
        {activeTab === 'notices'  && <DriverNotices />}
        {activeTab === 'incident' && <DriverIncidentTab />}
      </div>

      <div style={{
        display: 'flex', background: '#fff',
        borderTop: '1px solid #e5e7eb', position: 'sticky', bottom: 0,
      }}>
        {TABS.map(t => (
          <button key={t.id} onClick={() => setActiveTab(t.id)} style={{
            flex: 1, padding: '10px 4px', border: 'none', background: 'none',
            cursor: 'pointer', fontSize: 11,
            color: activeTab === t.id ? '#2563eb' : '#9ca3af',
            borderTop: activeTab === t.id ? '2px solid #2563eb' : '2px solid transparent',
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3,
          }}>
            <span style={{ fontSize: 20 }}>{t.icon}</span>
            {t.label}
          </button>
        ))}
      </div>
    </div>
  )
}
