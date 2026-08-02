import { Navigate, Route, Routes, useLocation } from 'react-router-dom'

import Navbar from './components/Navbar'
import Sidebar from './components/Sidebar'
import PassengerDashboard from './pages/PassengerDashboard'
import StationMasterPanel from './pages/StationMasterPanel'
import './App.css'

/**
 * App shell.
 *
 * The two screens serve different people in different situations, so each gets
 * its own visual world: warm paper for a traveller checking a journey, a dark
 * control room for staff watching a station. The theme class here is what the
 * stylesheets key off.
 */
function App() {
  const { pathname } = useLocation()
  const theme = pathname.startsWith('/station-master')
    ? 'theme-station'
    : 'theme-passenger'

  return (
    <div className={`app ${theme}`}>
      <Sidebar />

      <div className="app-body">
        <Navbar />

        <main className="app-main">
          <Routes>
            {/* Opening the site root lands the user on the passenger view. */}
            <Route path="/" element={<Navigate to="/passenger" replace />} />
            <Route path="/passenger" element={<PassengerDashboard />} />
            <Route path="/station-master" element={<StationMasterPanel />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default App
