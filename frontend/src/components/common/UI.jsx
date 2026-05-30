export function Spinner({ size = 32, color = '#2563eb' }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '2rem' }}>
      <div style={{
        width: size, height: size, borderRadius: '50%',
        border: `3px solid ${color}22`,
        borderTop: `3px solid ${color}`,
        animation: 'spin 0.7s linear infinite',
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}

export function EmptyState({ icon = '📭', title = 'Nothing here', desc = '', action = null }) {
  return (
    <div style={{
      textAlign: 'center', padding: '3rem 1.5rem',
      background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb',
    }}>
      <div style={{ fontSize: 40, marginBottom: 12 }}>{icon}</div>
      <div style={{ fontSize: 15, fontWeight: 500, marginBottom: 4 }}>{title}</div>
      {desc && <div style={{ fontSize: 13, color: '#9ca3af', marginBottom: '1rem' }}>{desc}</div>}
      {action}
    </div>
  )
}

export function ErrorAlert({ message, onRetry }) {
  return (
    <div style={{
      background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 10,
      padding: '0.875rem 1rem', display: 'flex', justifyContent: 'space-between',
      alignItems: 'center', fontSize: 14, color: '#dc2626',
    }}>
      <span>⚠️ {message}</span>
      {onRetry && (
        <button onClick={onRetry} style={{
          fontSize: 12, color: '#dc2626', background: 'none',
          border: '1px solid #fecaca', borderRadius: 6,
          padding: '3px 10px', cursor: 'pointer',
        }}>
          Retry
        </button>
      )}
    </div>
  )
}

export function PageHeader({ title, subtitle, action }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem' }}>
      <div>
        <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 2 }}>{title}</h1>
        {subtitle && <p style={{ fontSize: 13, color: '#6b7280' }}>{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}
