import api from './api'

export const incidentsApi = {
  list: (params = {}) => api.get('/incidents/', { params }).then(r => r.data),
  get: (id) => api.get(`/incidents/${id}`).then(r => r.data),
  create: (data) => api.post('/incidents/', data).then(r => r.data),
  update: (id, data) => api.patch(`/incidents/${id}`, data).then(r => r.data),
  transition: (id, to_status, note = null) =>
    api.post(`/incidents/${id}/transition`, { to_status, note }).then(r => r.data),
  panic: (params = {}) => api.post('/incidents/panic', null, { params }).then(r => r.data),
}
