import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '../store/authStore'
import toast from 'react-hot-toast'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const { login, isLoading } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const user = await login(username, password)
      toast.success(`Welcome, ${user.full_name || user.username}!`)
      // Route based on role
      if (user.role === 'driver' || user.role === 'conductor') {
        navigate('/driver')
      } else {
        navigate('/dashboard')
      }
    } catch {
      toast.error('Invalid username or password')
    }
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center',
      justifyContent: 'center', background: '#f5f5f5'
    }}>
      <div style={{
        background: '#fff', borderRadius: 12, padding: '2.5rem',
        width: 380, boxShadow: '0 2px 12px rgba(0,0,0,0.08)'
      }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{
            width: 56, height: 56, borderRadius: 12, background: '#1a56db',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 1rem', fontSize: 24
          }}>🚌</div>
          <h1 style={{ fontSize: 20, fontWeight: 600, margin: 0 }}>NCRTC BMS</h1>
          <p style={{ color: '#6b7280', fontSize: 14, marginTop: 4 }}>
            Bus Management System
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: 14, fontWeight: 500, marginBottom: 6 }}>
              Username
            </label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              placeholder="e.g. admin, driver_avd_1"
              required
              style={{
                width: '100%', padding: '10px 12px', borderRadius: 8,
                border: '1px solid #d1d5db', fontSize: 14, outline: 'none',
                boxSizing: 'border-box'
              }}
            />
          </div>
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', fontSize: 14, fontWeight: 500, marginBottom: 6 }}>
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="Password"
              required
              style={{
                width: '100%', padding: '10px 12px', borderRadius: 8,
                border: '1px solid #d1d5db', fontSize: 14, outline: 'none',
                boxSizing: 'border-box'
              }}
            />
          </div>
          <button
            type="submit"
            disabled={isLoading}
            style={{
              width: '100%', padding: '11px', borderRadius: 8,
              background: isLoading ? '#93c5fd' : '#1a56db',
              color: '#fff', fontSize: 15, fontWeight: 600,
              border: 'none', cursor: isLoading ? 'not-allowed' : 'pointer'
            }}
          >
            {isLoading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        {/* Demo creds hint */}
        <div style={{
          marginTop: '1.5rem', padding: '0.75rem', borderRadius: 8,
          background: '#f0f9ff', border: '1px solid #bae6fd', fontSize: 12
        }}>
          <strong>Demo:</strong> admin / admin123 &nbsp;|&nbsp; driver_avd_1 / driver123<br/>
          mgr_avd / manager123 &nbsp;|&nbsp; control1 / control123
        </div>
      </div>
    </div>
  )
}
