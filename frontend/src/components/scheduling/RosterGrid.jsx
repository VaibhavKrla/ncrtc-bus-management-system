import { useState, useEffect, useCallback } from 'react'
import { schedulingApi } from '../../services/schedulingApi'
import AssignDutyModal from './AssignDutyModal'
import toast from 'react-hot-toast'

const STATUS_STYLE = {
  draft:        { bg: '#fef9c3', text: '#854d0e', border: '#fde68a' },
  published:    { bg: '#dbeafe', text: '#1e40af', border: '#bfdbfe' },
  acknowledged: { bg: '#dcfce7', text: '#166534', border: '#bbf7d0' },
  completed:    { bg: '#f3f4f6', text: '#6b7280', border: '#e5e7eb' },
}

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function getMonday(dateStr) {
  const d = new Date(dateStr)
  const day = d.getDay()
  const diff = d.getDate() - day + (day === 0 ? -6 : 1)
  d.setDate(diff)
  return d.toISOString().slice(0, 10)
}

function formatDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })
}

function isToday(dateStr) {
  return dateStr === new Date().toISOString().slice(0, 10)
}

export default function RosterGrid({ depotId }) {
  const [weekStart, setWeekStart] = useState(() => getMonday(new Date().toISOString().slice(0, 10)))
  const [roster, setRoster] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedDuties, setSelectedDuties] = useState(new Set())
  const [assignModal, setAssignModal] = useState(null) // { driverId, date } or { existing: duty }
  const [publishing, setPublishing] = useState(false)

  const load = useCallback(async () => {
    if (!depotId) return
    setLoading(true)
    try {
      const data = await schedulingApi.getRoster(depotId, weekStart)
      setRoster(data)
      setSelectedDuties(new Set())
    } catch {
      toast.error('Failed to load roster')
    } finally {
      setLoading(false)
    }
  }, [depotId, weekStart])

  useEffect(() => { load() }, [load])

  const shiftWeek = (dir) => {
    const d = new Date(weekStart + 'T00:00:00')
    d.setDate(d.getDate() + dir * 7)
    setWeekStart(d.toISOString().slice(0, 10))
  }

  const toggleSelect = (dutyId) => {
    setSelectedDuties(prev => {
      const next = new Set(prev)
      next.has(dutyId) ? next.delete(dutyId) : next.add(dutyId)
      return next
    })
  }

  const handlePublish = async () => {
    if (selectedDuties.size === 0) {
      toast.error('Select at least one draft duty to publish')
      return
    }
    setPublishing(true)
    try {
      const res = await schedulingApi.publishDuties([...selectedDuties])
      toast.success(`Published ${res.published} duties`)
      load()
    } catch {
      toast.error('Publish failed')
    } finally {
      setPublishing(false)
    }
  }

  const handleDelete = async (dutyId) => {
    if (!window.confirm('Delete this duty?')) return
    await schedulingApi.deleteDuty(dutyId)
    toast.success('Duty deleted')
    load()
  }

  // Collect all draft duty IDs for select-all
  const allDraftIds = roster
    ? roster.drivers.flatMap(d =>
        roster.dates.map(date => roster.duties[d.id]?.[date])
          .filter(duty => duty?.status === 'draft')
          .map(duty => duty.id)
      )
    : []

  const allSelected = allDraftIds.length > 0 && allDraftIds.every(id => selectedDuties.has(id))

  return (
    <div>
      {/* Toolbar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: 8 }}>
        {/* Week nav */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button onClick={() => shiftWeek(-1)} style={navBtn}>← Prev</button>
          <div style={{ fontSize: 14, fontWeight: 600, minWidth: 160, textAlign: 'center' }}>
            Week of {formatDate(weekStart)}
          </div>
          <button onClick={() => shiftWeek(1)} style={navBtn}>Next →</button>
          <button onClick={() => setWeekStart(getMonday(new Date().toISOString().slice(0, 10)))}
            style={{ ...navBtn, color: '#2563eb', borderColor: '#bfdbfe' }}>
            Today
          </button>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', gap: 8 }}>
          {selectedDuties.size > 0 && (
            <button onClick={handlePublish} disabled={publishing} style={{
              padding: '7px 16px', borderRadius: 7, border: 'none',
              background: publishing ? '#93c5fd' : '#2563eb',
              color: '#fff', fontSize: 13, fontWeight: 500, cursor: 'pointer',
            }}>
              {publishing ? 'Publishing...' : `Publish ${selectedDuties.size} selected`}
            </button>
          )}
          <button
            onClick={() => setAssignModal({ driverId: null, date: new Date().toISOString().slice(0, 10) })}
            style={{
              padding: '7px 16px', borderRadius: 7, border: '1px solid #d1d5db',
              background: '#fff', fontSize: 13, cursor: 'pointer', fontWeight: 500,
            }}
          >+ Assign duty</button>
        </div>
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: 10, marginBottom: '0.75rem', flexWrap: 'wrap' }}>
        {Object.entries(STATUS_STYLE).map(([s, style]) => (
          <div key={s} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
            <div style={{ width: 10, height: 10, borderRadius: 2, background: style.bg, border: `1px solid ${style.border}` }} />
            <span style={{ color: '#6b7280', textTransform: 'capitalize' }}>{s}</span>
          </div>
        ))}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: '#6b7280' }}>
          ☑ = select to bulk publish
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#9ca3af' }}>Loading roster...</div>
      ) : !roster || roster.drivers.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: '#9ca3af', background: '#fff', borderRadius: 10, border: '1px solid #e5e7eb' }}>
          No drivers found for this depot.
        </div>
      ) : (
        <div style={{ overflowX: 'auto', borderRadius: 10, border: '1px solid #e5e7eb', background: '#fff' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 700 }}>
            <thead>
              <tr style={{ background: '#f8fafc' }}>
                {/* Select all checkbox */}
                <th style={{ ...thStyle, width: 32, padding: '10px 8px' }}>
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={() => {
                      if (allSelected) setSelectedDuties(new Set())
                      else setSelectedDuties(new Set(allDraftIds))
                    }}
                    title="Select all drafts"
                  />
                </th>
                <th style={{ ...thStyle, textAlign: 'left', minWidth: 130 }}>Driver</th>
                {roster.dates.map((date, i) => (
                  <th key={date} style={{
                    ...thStyle, minWidth: 110,
                    background: isToday(date) ? '#eff6ff' : '#f8fafc',
                    color: isToday(date) ? '#1d4ed8' : '#374151',
                  }}>
                    <div>{DAY_LABELS[i]}</div>
                    <div style={{ fontSize: 11, fontWeight: 400, color: '#6b7280' }}>{formatDate(date)}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {roster.drivers.map((driver, rowIdx) => (
                <tr key={driver.id} style={{ background: rowIdx % 2 === 0 ? '#fff' : '#fafafa' }}>
                  <td style={{ ...tdStyle, textAlign: 'center' }} />
                  <td style={{ ...tdStyle, fontWeight: 500, fontSize: 13, color: '#1e293b' }}>
                    {driver.full_name}
                    <div style={{ fontSize: 11, color: '#9ca3af', fontWeight: 400 }}>{driver.username}</div>
                  </td>
                  {roster.dates.map(date => {
                    const duty = roster.duties[driver.id]?.[date]
                    const style = duty ? STATUS_STYLE[duty.status] || STATUS_STYLE.draft : null
                    const isSelected = duty && selectedDuties.has(duty.id)

                    return (
                      <td key={date} style={{
                        ...tdStyle,
                        background: isToday(date) ? '#f0f7ff' : 'transparent',
                        verticalAlign: 'top',
                        padding: '6px',
                      }}>
                        {duty ? (
                          <div
                            style={{
                              background: isSelected ? '#dbeafe' : style.bg,
                              border: `1px solid ${isSelected ? '#3b82f6' : style.border}`,
                              borderRadius: 7, padding: '5px 7px', cursor: 'pointer',
                              outline: isSelected ? '2px solid #3b82f6' : 'none',
                            }}
                            onClick={() => duty.status === 'draft' && toggleSelect(duty.id)}
                          >
                            <div style={{ fontSize: 11, fontWeight: 600, color: style.text, textTransform: 'uppercase', marginBottom: 2 }}>
                              {duty.status}
                              {duty.status === 'draft' && (
                                <input
                                  type="checkbox"
                                  checked={isSelected}
                                  readOnly
                                  style={{ marginLeft: 4, cursor: 'pointer' }}
                                  onClick={e => { e.stopPropagation(); toggleSelect(duty.id) }}
                                />
                              )}
                            </div>
                            <div style={{ fontSize: 11, color: '#374151', marginBottom: 1 }}>🚌 {duty.registration_no}</div>
                            <div style={{ fontSize: 11, color: '#374151', marginBottom: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 95 }}>
                              🛣 {duty.route_name}
                            </div>
                            <div style={{ fontSize: 10, color: '#9ca3af' }}>{duty.shift_start}–{duty.shift_end}</div>
                            {/* Edit / delete buttons */}
                            <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
                              <button
                                onClick={e => { e.stopPropagation(); setAssignModal({ existing: duty }) }}
                                style={{ fontSize: 10, padding: '1px 5px', borderRadius: 4, border: '1px solid #d1d5db', background: '#fff', cursor: 'pointer' }}
                              >✏️</button>
                              <button
                                onClick={e => { e.stopPropagation(); handleDelete(duty.id) }}
                                style={{ fontSize: 10, padding: '1px 5px', borderRadius: 4, border: '1px solid #fca5a5', background: '#fff', color: '#dc2626', cursor: 'pointer' }}
                              >✕</button>
                            </div>
                          </div>
                        ) : (
                          <button
                            onClick={() => setAssignModal({ driverId: driver.id, date })}
                            style={{
                              width: '100%', minHeight: 36, border: '1px dashed #d1d5db',
                              borderRadius: 7, background: 'transparent', cursor: 'pointer',
                              color: '#9ca3af', fontSize: 18, display: 'flex',
                              alignItems: 'center', justifyContent: 'center',
                            }}
                            title="Assign duty"
                          >+</button>
                        )}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Assign / Edit modal */}
      {assignModal && (
        <AssignDutyModal
          depotId={depotId}
          prefillDriver={assignModal.driverId}
          prefillDate={assignModal.date}
          existing={assignModal.existing || null}
          onClose={() => setAssignModal(null)}
          onSave={load}
        />
      )}
    </div>
  )
}

const navBtn = {
  padding: '6px 12px', borderRadius: 7, border: '1px solid #d1d5db',
  background: '#fff', fontSize: 13, cursor: 'pointer',
}
const thStyle = {
  padding: '10px 8px', fontWeight: 600, fontSize: 12,
  color: '#374151', borderBottom: '1px solid #e5e7eb', textAlign: 'center',
}
const tdStyle = {
  padding: '8px', borderBottom: '1px solid #f3f4f6', fontSize: 13,
}
