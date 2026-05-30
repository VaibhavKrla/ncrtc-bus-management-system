import { create } from 'zustand'
import api from '../services/api'

const useAuthStore = create((set) => ({
  user: null,
  token: localStorage.getItem('access_token') || null,
  isLoading: false,
  error: null,

  login: async (username, password) => {
    set({ isLoading: true, error: null })
    try {
      const form = new URLSearchParams()
      form.append('username', username)
      form.append('password', password)

      const res = await api.post('/auth/login', form, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      })
      const data = res.data
      localStorage.setItem('access_token', data.access_token)
      set({ user: data, token: data.access_token, isLoading: false })
      return data
    } catch (err) {
      const msg = err.response?.data?.detail || 'Login failed'
      set({ error: msg, isLoading: false })
      throw err
    }
  },

  logout: () => {
    localStorage.removeItem('access_token')
    set({ user: null, token: null })
    window.location.href = '/login'
  },

  fetchMe: async () => {
    try {
      const res = await api.get('/auth/me')
      set({ user: res.data })
    } catch {
      localStorage.removeItem('access_token')
      set({ user: null, token: null })
    }
  },
}))

export default useAuthStore
