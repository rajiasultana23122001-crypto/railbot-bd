import { Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import PassengerDashboard from './pages/PassengerDashboard'
import StationMasterPanel from './pages/StationMasterPanel'
import './App.css'

/**
 * App shell: the navigation bar stays fixed while <Routes> swaps the page
 * underneath it according to the URL.
 */
function App() {
  return (
    <div className="app">
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
  )
}

export default App
