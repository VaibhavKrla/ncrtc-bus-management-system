import { useState, useEffect, useRef, useCallback } from 'react'
import { avlsApi } from '../services/avlsApi'

const WS_URL = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_WS_URL) || 'ws://localhost:8000'

/**
 * useLivePositions — stretch goal upgrade.
 * Tries WebSocket first; falls back to 5s polling if WS fails/unavailable.
 */
export function useLivePositions(depotId = null, pollIntervalMs = 5000) {
  const [vehicles, setVehicles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdated, setLastUpdated] = useState(null)
  const [mode, setMode] = useState('connecting') // 'ws' | 'polling' | 'connecting'

  const wsRef = useRef(null)
  const pollRef = useRef(null)
  const mountedRef = useRef(true)

  const startPolling = useCallback(() => {
    if (pollRef.current) return
    setMode('polling')
    const fetchOnce = async () => {
      if (!mountedRef.current) return
      try {
        const data = await avlsApi.getLive(depotId)
        if (mountedRef.current) {
          setVehicles(data)
          setLastUpdated(new Date())
          setError(null)
          setLoading(false)
        }
      } catch {
        if (mountedRef.current) {
          setError('Failed to fetch live positions')
          setLoading(false)
        }
      }
    }
    fetchOnce()
    pollRef.current = setInterval(fetchOnce, pollIntervalMs)
  }, [depotId, pollIntervalMs])

  const stopPolling = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }, [])

  const connectWS = useCallback(() => {
    const token = localStorage.getItem('access_token')
    if (!token) { startPolling(); return }
    const depotParam = depotId ? `&depot_id=${depotId}` : ''
    const url = `${WS_URL}/api/v1/ws/live?token=${token}${depotParam}`
    try {
      const ws = new WebSocket(url)
      wsRef.current = ws
      const wsTimeout = setTimeout(() => {
        if (ws.readyState !== WebSocket.OPEN) { ws.close(); startPolling() }
      }, 3000)
      ws.onopen = () => { clearTimeout(wsTimeout); setMode('ws'); setError(null); stopPolling() }
      ws.onmessage = (event) => {
        if (!mountedRef.current) return
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'positions') {
            setVehicles(msg.data); setLastUpdated(new Date()); setLoading(false)
          }
        } catch {}
      }
      ws.onerror = () => { clearTimeout(wsTimeout); startPolling() }
      ws.onclose = (e) => { clearTimeout(wsTimeout); if (mountedRef.current && e.code !== 1000) startPolling() }
    } catch { startPolling() }
  }, [depotId, startPolling, stopPolling])

  useEffect(() => {
    mountedRef.current = true
    connectWS()
    return () => {
      mountedRef.current = false
      stopPolling()
      if (wsRef.current) { wsRef.current.close(1000); wsRef.current = null }
    }
  }, [connectWS])

  const refresh = useCallback(async () => {
    try { const data = await avlsApi.getLive(depotId); setVehicles(data); setLastUpdated(new Date()) } catch {}
  }, [depotId])

  return { vehicles, loading, error, lastUpdated, mode, refresh }
}
