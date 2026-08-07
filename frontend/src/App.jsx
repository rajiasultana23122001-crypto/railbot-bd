import { Navigate, Route, Routes } from 'react-router-dom'

import Navbar from './components/Navbar'
import NetworkStatus from './components/NetworkStatus'
import RouteGuard from './components/RouteGuard'
import Sidebar from './components/Sidebar'
import { getAuthToken, getRole, ROLE_AUTHORITY, ROLE_PASSENGER } from './api/client'
import AuthLanding from './pages/AuthLanding'
import AuthorityAuth from './pages/AuthorityAuth'
import PassengerAuth from './pages/PassengerAuth'
import PassengerDashboard from './pages/PassengerDashboard'
import StationMasterPanel from './pages/StationMasterPanel'
import TrainInfo from './pages/TrainInfo'
import './App.css'

/** Where "/" sends a visitor: their own dashboard if signed in, otherwise the role picker. */
function RootRedirect() {
  const role = getRole()
  if (!getAuthToken() || !role) return <Navigate to="/auth" replace />
  return (
    <Navigate to={role === ROLE_AUTHORITY ? '/station-master' : '/passenger'} replace />
  )
}

/**
 * App shell: the left rail and top bar stay put while <Routes> swaps the page
 * underneath them.
 */
function App() {
  return (
    <div className="app">
      <Sidebar />

      <div className="app-body">
        <Navbar />

        <main className="app-main">
          <Routes>
            <Route path="/" element={<RootRedirect />} />

            {/* Role picker + the two signup/login forms - open to anyone. */}
            <Route path="/auth" element={<AuthLanding />} />
            <Route path="/auth/passenger" element={<PassengerAuth />} />
            <Route path="/auth/authority" element={<AuthorityAuth />} />

            <Route
              path="/passenger"
              element={
                <RouteGuard allow={[ROLE_PASSENGER]}>
                  <PassengerDashboard />
                </RouteGuard>
              }
            />
            <Route
              path="/station-master"
              element={
                <RouteGuard allow={[ROLE_AUTHORITY]}>
                  <StationMasterPanel />
                </RouteGuard>
              }
            />
            {/* Timetable: either signed-in role may see it. */}
            <Route
              path="/trains"
              element={
                <RouteGuard allow={[ROLE_PASSENGER, ROLE_AUTHORITY]}>
                  <TrainInfo />
                </RouteGuard>
              }
            />
          </Routes>
        </main>
      </div>

      <NetworkStatus />
    </div>
  )
}

export default App
