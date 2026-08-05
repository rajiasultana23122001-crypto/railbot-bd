import { Navigate, Route, Routes } from 'react-router-dom'

import Navbar from './components/Navbar'
import NetworkStatus from './components/NetworkStatus'
import Sidebar from './components/Sidebar'
import PassengerDashboard from './pages/PassengerDashboard'
import StationMasterPanel from './pages/StationMasterPanel'
import TrainInfo from './pages/TrainInfo'
import './App.css'

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
            {/* Opening the site root lands the user on the passenger view. */}
            <Route path="/" element={<Navigate to="/passenger" replace />} />
            <Route path="/passenger" element={<PassengerDashboard />} />
            <Route path="/station-master" element={<StationMasterPanel />} />
            <Route path="/trains" element={<TrainInfo />} />
          </Routes>
        </main>
      </div>

      <NetworkStatus />
    </div>
  )
}

export default App
