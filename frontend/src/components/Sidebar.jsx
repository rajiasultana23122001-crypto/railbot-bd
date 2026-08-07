import { NavLink, useNavigate } from 'react-router-dom'

import { getRole, logout, ROLE_AUTHORITY, ROLE_PASSENGER } from '../api/client'
import {
  IconCalendar,
  IconChart,
  IconGrid,
  IconHome,
  IconLogout,
  IconMenu,
  IconSettings,
  IconUsers,
} from './icons'

/**
 * The narrow rail down the left edge.
 *
 * Only items with a `to` navigate; the rest stand for sections the project
 * has not built yet, so they are marked disabled rather than pretending to
 * work. Board and Passengers are further filtered by role - a passenger
 * never even sees a link to the Station Control Board, and vice versa. This
 * is the frontend half of "hide inaccessible routes"; RouteGuard is the half
 * that still blocks a direct URL either way.
 */
const items = [
  { key: 'home', label: 'Overview', Icon: IconHome },
  {
    key: 'board',
    label: 'Boards',
    Icon: IconGrid,
    to: '/station-master',
    role: ROLE_AUTHORITY,
  },
  {
    key: 'people',
    label: 'Passengers',
    Icon: IconUsers,
    to: '/passenger',
    role: ROLE_PASSENGER,
  },
  { key: 'reports', label: 'Reports', Icon: IconChart },
  { key: 'timetable', label: 'Timetable', Icon: IconCalendar, to: '/trains' },
  { key: 'settings', label: 'Settings', Icon: IconSettings },
]

function Sidebar() {
  const navigate = useNavigate()
  const role = getRole()

  const visibleItems = items.filter((item) => !item.role || item.role === role)

  function handleSignOut() {
    logout()
    navigate('/auth', { replace: true })
  }

  return (
    <aside className="rail" aria-label="Sections">
      <button type="button" className="rail-btn rail-menu" aria-label="Menu">
        <IconMenu />
      </button>

      <nav className="rail-nav">
        {visibleItems.map(({ key, label, Icon, to }) =>
          to ? (
            <NavLink
              key={key}
              to={to}
              className={({ isActive }) =>
                `rail-btn ${isActive ? 'is-active' : ''}`
              }
              aria-label={label}
              title={label}
            >
              <Icon />
            </NavLink>
          ) : (
            <button
              key={key}
              type="button"
              className="rail-btn"
              aria-label={label}
              disabled
              title={`${label} — not built yet`}
            >
              <Icon />
            </button>
          ),
        )}
      </nav>

      <button
        type="button"
        className="rail-btn rail-out"
        aria-label="Sign out"
        title="Sign out"
        onClick={handleSignOut}
        disabled={!role}
      >
        <IconLogout />
      </button>
    </aside>
  )
}

export default Sidebar
