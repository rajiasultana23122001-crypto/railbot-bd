import Clock from './Clock'
import ThemeToggle from './ThemeToggle'
import { getPhoneNumber, getRole } from '../api/client'
import { useLiveStats } from '../api/useLiveStats'

/**
 * Top HUD bar, shown on every page: project name on the left, live network
 * figures and the BD-time clock on the right.
 *
 * Page-to-page navigation lives in the left rail (see Sidebar) — this bar is
 * status, not navigation.
 */
function Navbar() {
  const { stationCount, trainCount, onTimePercent } = useLiveStats()
  const role = getRole()
  const phoneNumber = getPhoneNumber()

  return (
    <header className="navbar">
      <div className="navbar-brand">
        <span className="navbar-mark" aria-hidden="true">
          <span></span>
          <span></span>
          <span></span>
        </span>
        <span>
          Bangladesh Railway <span className="navbar-sep">—</span>{' '}
          <em>Management Information System</em>
        </span>
      </div>

      <div className="navbar-stats" aria-label="Network summary">
        <div className="navbar-stat">
          <span className="navbar-stat-label">Trains</span>
          <span className="navbar-stat-value">{trainCount ?? '—'}</span>
        </div>
        <div className="navbar-stat">
          <span className="navbar-stat-label">Stations</span>
          <span className="navbar-stat-value">{stationCount}</span>
        </div>
        <div className="navbar-stat">
          <span className="navbar-stat-label">On Time</span>
          <span className="navbar-stat-value">
            {onTimePercent === null ? '—' : `${onTimePercent}%`}
          </span>
        </div>

        {role && (
          <div className="navbar-stat">
            <span className="navbar-stat-label">Signed In As</span>
            <span className="navbar-stat-value navbar-role">
              {phoneNumber} · {role}
            </span>
          </div>
        )}

        <Clock />
        <ThemeToggle />
      </div>
    </header>
  )
}

export default Navbar
