import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import DriverPortal from './pages/DriverPortal'
import NoticesAdminPage from './pages/NoticesAdminPage'
import LiveMapPage from './pages/LiveMapPage'
import HistoryPage from './pages/HistoryPage'
import SchedulingPage from './pages/SchedulingPage'
import IncidentsPage from './pages/IncidentsPage'
import ProtectedRoute from './components/common/ProtectedRoute'

const ADMIN_ROLES = ['admin', 'depot_manager', 'control_operator']
const DRIVER_ROLES = ['driver', 'conductor']

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/dashboard" element={<ProtectedRoute allowedRoles={ADMIN_ROLES}><DashboardPage /></ProtectedRoute>} />
        <Route path="/notices"    element={<ProtectedRoute allowedRoles={ADMIN_ROLES}><NoticesAdminPage /></ProtectedRoute>} />
        <Route path="/map"        element={<ProtectedRoute allowedRoles={ADMIN_ROLES}><LiveMapPage /></ProtectedRoute>} />
        <Route path="/map/history" element={<ProtectedRoute allowedRoles={ADMIN_ROLES}><HistoryPage /></ProtectedRoute>} />
        <Route path="/scheduling" element={<ProtectedRoute allowedRoles={['admin','depot_manager']}><SchedulingPage /></ProtectedRoute>} />
        <Route path="/incidents"  element={<ProtectedRoute allowedRoles={ADMIN_ROLES}><IncidentsPage /></ProtectedRoute>} />
        <Route path="/driver"     element={<ProtectedRoute allowedRoles={DRIVER_ROLES}><DriverPortal /></ProtectedRoute>} />
        <Route path="/"           element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
