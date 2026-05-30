import { useState, useEffect } from 'react'
import toast from 'react-hot-toast'
import { noticesApi } from '../../services/noticesApi'

export default function DriverNotices() {
  const [notices, setNotices] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)

  const load = async () => {
    try {
      const data = await noticesApi.list()
      setNotices(data)
    } catch {
      toast.error('Could not load notices')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const openNotice = async (notice) => {
    setSelected(notice)
    if (!notice.is_read_by_me) {
      try {
        const updated = await noticesApi.markRead(notice.id)
        setNotices(ns => ns.map(n => n.id === notice.id ? updated : n))
        setSelected(updated)
      } catch {}
    }
  }

  const unreadCount = notices.filter(n => !n.is_read_by_me).length

  if (selected) {
    return (
      <div style={{ padding: '1rem' }}>
        <button
          onClick={() => setSelected(null)}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            background: 'none', border: 'none', cursor: 'pointer',
            color: '#2563eb', fontSize: 14, marginBottom: '1rem', padding: 0,
          }}
        >
          ← Back to notices
        </button>

        <div style={{
          background: '#fff', borderRadius: 12, padding: '1.25rem',
          boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
        }}>
          <h2 style={{ fontSize: 17, fontWeight: 600, marginBottom: '0.5rem' }}>
            {selected.title}
          </h2>
          <div style={{ fontSize: 12, color: '#9ca3af', marginBottom: '1rem' }}>
            {selected.published_at
              ? new Date(selected.published_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
              : ''}
          </div>
          <p style={{ fontSize: 15, color: '#374151', lineHeight: 1.65 }}>
            {selected.body}
          </p>
          {selected.is_read_by_me && (
            <div style={{
              marginTop: '1.25rem', padding: '8px 12px', borderRadius: 8,
              background: '#f0fdf4', color: '#16a34a', fontSize: 13, display: 'flex', gap: 6,
            }}>
              ✓ Marked as read
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div style={{ padding: '1rem' }}>
      <div style={{ marginBottom: '1rem' }}>
        <h2 style={{ fontSize: 18, fontWeight: 600, marginBottom: 2 }}>📢 Notices</h2>
        {unreadCount > 0 && (
          <div style={{ fontSize: 13, color: '#dc2626', fontWeight: 500 }}>
            {unreadCount} unread notice{unreadCount > 1 ? 's' : ''}
          </div>
        )}
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', color: '#9ca3af', padding: '2rem' }}>Loading...</div>
      ) : notices.length === 0 ? (
        <div style={{
          background: '#fff', borderRadius: 10, padding: '2rem',
          textAlign: 'center', color: '#9ca3af', fontSize: 14,
        }}>
          No notices for you right now.
        </div>
      ) : (
        notices.map(n => (
          <div
            key={n.id}
            onClick={() => openNotice(n)}
            style={{
              background: '#fff', borderRadius: 10, padding: '1rem',
              marginBottom: 8, cursor: 'pointer',
              border: n.is_read_by_me ? '1px solid #e5e7eb' : '1px solid #bfdbfe',
              boxShadow: n.is_read_by_me ? 'none' : '0 0 0 2px #eff6ff',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{
                fontSize: 14, fontWeight: n.is_read_by_me ? 400 : 600,
                color: n.is_read_by_me ? '#374151' : '#1e3a8a',
              }}>
                {!n.is_read_by_me && (
                  <span style={{
                    display: 'inline-block', width: 8, height: 8,
                    borderRadius: '50%', background: '#2563eb', marginRight: 6,
                  }} />
                )}
                {n.title}
              </span>
              <span style={{ fontSize: 11, color: '#9ca3af', flexShrink: 0, marginLeft: 8 }}>
                {n.published_at
                  ? new Date(n.published_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
                  : ''}
              </span>
            </div>
            <p style={{
              fontSize: 13, color: '#6b7280', margin: 0,
              overflow: 'hidden', display: '-webkit-box',
              WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
            }}>
              {n.body}
            </p>
          </div>
        ))
      )}
    </div>
  )
}
