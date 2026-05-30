import api from './api'

export const avlsApi = {
  // Live positions of all vehicles (optional depot filter)
  getLive: (depotId = null) => {
    const params = depotId ? { depot_id: depotId } : {}
    return api.get('/avls/live', { params }).then(r => r.data)
  },

  // Last N minutes trail for one vehicle
  getTrail: (vehicleId, minutes = 30) =>
    api.get(`/avls/vehicles/${vehicleId}/trail`, { params: { minutes } }).then(r => r.data),

  // Full day history
  getHistory: (vehicleId, date) =>
    api.get(`/avls/vehicles/${vehicleId}/history`, { params: { date } }).then(r => r.data),

  // Vehicle list for dropdowns
  getVehicles: (depotId = null) => {
    const params = depotId ? { depot_id: depotId } : {}
    return api.get('/avls/vehicles', { params }).then(r => r.data)
  },

  // Depot list for filter
  getDepots: () => api.get('/avls/depots').then(r => r.data),
}
