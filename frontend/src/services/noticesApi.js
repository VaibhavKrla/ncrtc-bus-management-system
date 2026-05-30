import api from './api'

export const noticesApi = {
  // Get notices visible to current user
  list: () => api.get('/notices/').then(r => r.data),

  // Admin/manager: all notices including drafts
  listAll: () => api.get('/notices/all').then(r => r.data),

  // Get single notice
  get: (id) => api.get(`/notices/${id}`).then(r => r.data),

  // Create notice
  create: (data) => api.post('/notices/', data).then(r => r.data),

  // Update notice
  update: (id, data) => api.patch(`/notices/${id}`, data).then(r => r.data),

  // Delete notice
  delete: (id) => api.delete(`/notices/${id}`),

  // Mark as read
  markRead: (id) => api.post(`/notices/${id}/read`).then(r => r.data),

  // Get read receipts (admin/manager)
  getReads: (id) => api.get(`/notices/${id}/reads`).then(r => r.data),
}
