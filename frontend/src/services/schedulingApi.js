import api from './api'

export const schedulingApi = {
  // Stops
  getStops: () => api.get('/scheduling/stops').then(r => r.data),
  createStop: (data) => api.post('/scheduling/stops', data).then(r => r.data),

  // Routes
  getRoutes: (depotId = null) => {
    const params = depotId ? { depot_id: depotId } : {}
    return api.get('/scheduling/routes', { params }).then(r => r.data)
  },
  getRoute: (id) => api.get(`/scheduling/routes/${id}`).then(r => r.data),
  createRoute: (data) => api.post('/scheduling/routes', data).then(r => r.data),
  updateRoute: (id, data) => api.patch(`/scheduling/routes/${id}`, data).then(r => r.data),
  deleteRoute: (id) => api.delete(`/scheduling/routes/${id}`),

  // Roster
  getRoster: (depotId, weekStart) =>
    api.get('/scheduling/roster', { params: { depot_id: depotId, week_start: weekStart } }).then(r => r.data),

  // Duties
  getDuties: (params = {}) => api.get('/scheduling/duties', { params }).then(r => r.data),
  createDuty: (data) => api.post('/scheduling/duties', data).then(r => r.data),
  updateDuty: (id, data) => api.patch(`/scheduling/duties/${id}`, data).then(r => r.data),
  deleteDuty: (id) => api.delete(`/scheduling/duties/${id}`),
  publishDuties: (dutyIds) => api.post('/scheduling/duties/publish', { duty_ids: dutyIds }).then(r => r.data),
  acknowledgeDuty: (id) => api.post(`/scheduling/duties/${id}/acknowledge`).then(r => r.data),

  // Dropdowns
  getDrivers: (depotId = null) => {
    const params = depotId ? { depot_id: depotId } : {}
    return api.get('/scheduling/drivers', { params }).then(r => r.data)
  },
  getVehicles: (depotId = null) => {
    const params = depotId ? { depot_id: depotId } : {}
    return api.get('/scheduling/vehicles', { params }).then(r => r.data)
  },
  getDepots: () => api.get('/avls/depots').then(r => r.data),
}
