import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import Layout from '../components/common/Layout'
import { noticesApi } from '../services/noticesApi'
import useAuthStore from '../store/authStore'

const TARGET_LABELS = { all: 'Everyone', depot: 'Depot only', role: 'By role' }
const ROLE_OPTIONS = ['driver', 'conductor', 'depot_manager', 'control_operator']

function Badge({ children, color = '#e5e7eb', text = '#374151' }) {
  return (
    <span style={{
      fontSize: 11, padding: '2px 8px', borderRadius: 99,
      background: color, color: text, fontWeight: 500,
    }}>{children}</span>
  )
}

function NoticeRow({ notice, onSelect, onPublish, onDelete, isAdmin }) {
  return (
    <div
      onClick={() => onSelect(notice)}
      style={{
        background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10,
        padding: '1rem 1.25rem', cursor: 'pointer', marginBottom: 8,
        display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12,
        transition: 'box-shadow 0.15s',
      }}
      onMouseEnter={e => e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)'}
      onMouseLeave={e => e.currentTarget.style.boxShadow = 'none'}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <span style={{ fontWeight: 600, fontSize: 14 }}>{notice.title}</span>
          {notice.is_published
            ? <Badge color="#dcfce7" text="#166534">Published</Badge>
            : <Badge color="#fef9c3" text="#854d0e">Draft</Badge>}
          <Badge color="#eff6ff" text="#1d4ed8">{TARGET_LABELS[notice.target]}</Badge>
        </div>
        <div style={{ fontSize: 13, color: '#6b7280', marginBottom: 6,
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 500 }}>
          {notice.body}
        </div>
        <div style={{ fontSize: 12, color: '#9ca3af' }}>
          {notice.is_published
            ? `Published ${new Date(notice.published_at).toLocaleDateString()}`
            : `Created ${new Date(notice.created_at).toLocaleDateString()}`}
          {' · '}
          <span style={{ color: '#3b82f6' }}>
            {notice.read_count}/{notice.total_target_count} read
          </span>
        </div>
      </div>
      <div style={{ display: 'flex', gap: 6, flexShrink: 0 }} onClick={e => e.stopPropagation()}>
        {!notice.is_published && (
          <button
            onClick={() => onPublish(notice.id)}
            style={{
              padding: '5px 12px', borderRadius: 6, border: '1px solid #16a34a',
              background: '#f0fdf4', color: '#16a34a', fontSize: 12, cursor: 'pointer',
            }}
          >Publish</button>
        )}
        {isAdmin && (
          <button
            onClick={() => onDelete(notice.id)}
            style={{
              padding: '5px 10px', borderRadius: 6, border: '1px solid #fca5a5',
              background: '#fff', color: '#dc2626', fontSize: 12, cursor: 'pointer',
            }}
          >✕</button>
        )}
      </div>
    </div>
  )
}

function CreateModal({ depots = [], onClose, onCreate }) {
  const [form, setForm] = useState({
    title: '', body: '', target: 'all',
    target_depot_id: '', target_role: '', is_published: false,
  })
  const [loading, setLoading] = useState(false)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const submit = async (e) => {
    e.preventDefault()
    if (!form.title.trim() || !form.body.trim()) {
      toast.error('Title and body are required')
      return
    }
    setLoading(true)
    try {
      const payload = {
        title: form.title, body: form.body,
        target: form.target,
        is_published: form.is_published,
        target_depot_id: form.target === 'depot' && form.target_depot_id ? parseInt(form.target_depot_id) : null,
        target_role: form.target === 'role' ? form.target_role || null : null,
      }
      await onCreate(payload)
      onClose()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200,
    }}>
      <div style={{
        background: '#fff', borderRadius: 12, padding: '1.75rem',
        width: 520, maxHeight: '90vh', overflowY: 'auto',
        boxShadow: '0 8px 32px rgba(0,0,0,0.18)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
          <h2 style={{ fontSize: 17, fontWeight: 600 }}>Create Notice</h2>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', color: '#6b7280' }}>×</button>
        </div>

        <form onSubmit={submit}>
          <Field label="Title">
            <input value={form.title} onChange={e => set('title', e.target.value)}
              placeholder="Notice title" style={inputStyle} required />
          </Field>

          <Field label="Body">
            <textarea value={form.body} onChange={e => set('body', e.target.value)}
              placeholder="Notice content..." rows={5}
              style={{ ...inputStyle, resize: 'vertical' }} required />
          </Field>

          <Field label="Audience">
            <select value={form.target} onChange={e => set('target', e.target.value)} style={inputStyle}>
              <option value="all">Everyone</option>
              <option value="depot">Specific depot</option>
              <option value="role">Specific role</option>
            </select>
          </Field>

          {form.target === 'depot' && (
            <Field label="Depot">
              <select value={form.target_depot_id} onChange={e => set('target_depot_id', e.target.value)} style={inputStyle}>
                <option value="">Select depot...</option>
                {depots.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </Field>
          )}

          {form.target === 'role' && (
            <Field label="Role">
              <select value={form.target_role} onChange={e => set('target_role', e.target.value)} style={inputStyle}>
                <option value="">Select role...</option>
                {ROLE_OPTIONS.map(r => <option key={r} value={r}>{r.replace('_', ' ')}</option>)}
              </select>
            </Field>
          )}

          <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: '1.25rem', cursor: 'pointer' }}>
            <input type="checkbox" checked={form.is_published}
              onChange={e => set('is_published', e.target.checked)} />
            <span style={{ fontSize: 14 }}>Publish immediately</span>
          </label>

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
              {loading ? 'Saving...' : 'Create notice'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function ReadsModal({ notice, onClose }) {
  const [reads, setReads] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    noticesApi.getReads(notice.id)
      .then(setReads)
      .finally(() => setLoading(false))
  }, [notice.id])

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200,
    }}>
      <div style={{
        background: '#fff', borderRadius: 12, padding: '1.75rem',
        width: 460, maxHeight: '80vh', display: 'flex', flexDirection: 'column',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 2 }}>Read receipts</h2>
            <div style={{ fontSize: 13, color: '#6b7280' }}>{notice.title}</div>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', color: '#6b7280' }}>×</button>
        </div>

        <div style={{ fontSize: 13, color: '#2563eb', fontWeight: 500, marginBottom: '0.75rem' }}>
          {notice.read_count} / {notice.total_target_count} users read
        </div>

        <div style={{ overflowY: 'auto', flex: 1 }}>
          {loading ? (
            <div style={{ color: '#9ca3af', fontSize: 14 }}>Loading...</div>
          ) : reads.length === 0 ? (
            <div style={{ color: '#9ca3af', fontSize: 14 }}>No reads yet.</div>
          ) : reads.map(r => (
            <div key={r.id} style={{
              display: 'flex', justifyContent: 'space-between',
              padding: '8px 0', borderBottom: '1px solid #f3f4f6', fontSize: 13,
            }}>
              <span>{r.full_name || r.username}</span>
              <span style={{ color: '#9ca3af' }}>
                {new Date(r.read_at).toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── Reusable helpers ──────────────────────────────────────────────────────────
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

// ── Main page ─────────────────────────────────────────────────────────────────
export default function NoticesAdminPage() {
  const { user } = useAuthStore()
  const [notices, setNotices] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [selectedNotice, setSelectedNotice] = useState(null)
  const [filter, setFilter] = useState('all') // all | published | draft

  const isAdmin = user?.role === 'admin'
  const canManage = ['admin', 'depot_manager'].includes(user?.role)

  const load = async () => {
    setLoading(true)
    try {
      const data = canManage
        ? await noticesApi.listAll()
        : await noticesApi.list()
      setNotices(data)
    } catch {
      toast.error('Failed to load notices')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleCreate = async (payload) => {
    await noticesApi.create(payload)
    toast.success('Notice created!')
    load()
  }

  const handlePublish = async (id) => {
    await noticesApi.update(id, { is_published: true })
    toast.success('Notice published!')
    load()
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this notice?')) return
    await noticesApi.delete(id)
    toast.success('Notice deleted')
    setSelectedNotice(null)
    load()
  }

  const filtered = notices.filter(n => {
    if (filter === 'published') return n.is_published
    if (filter === 'draft') return !n.is_published
    return true
  })

  return (
    <Layout>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, marginBottom: 2 }}>📢 Notices</h1>
          <p style={{ fontSize: 13, color: '#6b7280' }}>
            {canManage ? 'Manage and publish notices to staff' : 'Notices from management'}
          </p>
        </div>
        {canManage && (
          <button
            onClick={() => setShowCreate(true)}
            style={{
              padding: '9px 18px', borderRadius: 8, border: 'none',
              background: '#2563eb', color: '#fff', fontSize: 14,
              fontWeight: 500, cursor: 'pointer',
            }}
          >+ New notice</button>
        )}
      </div>

      {/* Filter tabs */}
      {canManage && (
        <div style={{ display: 'flex', gap: 4, marginBottom: '1rem' }}>
          {['all', 'published', 'draft'].map(f => (
            <button key={f} onClick={() => setFilter(f)} style={{
              padding: '5px 14px', borderRadius: 99, fontSize: 13, cursor: 'pointer',
              border: '1px solid #d1d5db',
              background: filter === f ? '#1e293b' : '#fff',
              color: filter === f ? '#fff' : '#374151',
              fontWeight: filter === f ? 500 : 400,
            }}>
              {f.charAt(0).toUpperCase() + f.slice(1)}
              {' '}
              <span style={{ opacity: 0.6 }}>
                ({notices.filter(n =>
                  f === 'all' ? true : f === 'published' ? n.is_published : !n.is_published
                ).length})
              </span>
            </button>
          ))}
        </div>
      )}

      {/* List */}
      {loading ? (
        <div style={{ color: '#9ca3af', padding: '2rem', textAlign: 'center' }}>Loading...</div>
      ) : filtered.length === 0 ? (
        <div style={{
          background: '#fff', border: '1px solid #e5e7eb', borderRadius: 10,
          padding: '3rem', textAlign: 'center', color: '#9ca3af',
        }}>
          No notices found.
        </div>
      ) : (
        filtered.map(n => (
          <NoticeRow
            key={n.id}
            notice={n}
            onSelect={setSelectedNotice}
            onPublish={handlePublish}
            onDelete={handleDelete}
            isAdmin={isAdmin}
          />
        ))
      )}

      {/* Create modal */}
      {showCreate && (
        <CreateModal
          onClose={() => setShowCreate(false)}
          onCreate={handleCreate}
        />
      )}

      {/* Detail / reads modal */}
      {selectedNotice && (
        <ReadsModal notice={selectedNotice} onClose={() => setSelectedNotice(null)} />
      )}
    </Layout>
  )
}
