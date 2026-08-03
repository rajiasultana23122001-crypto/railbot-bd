import { NavLink } from 'react-router-dom'

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
 * work.
 */
const items = [
  { key: 'home', label: 'Overview', Icon: IconHome },
  { key: 'board', label: 'Boards', Icon: IconGrid, to: '/station-master' },
  { key: 'people', label: 'Passengers', Icon: IconUsers, to: '/passenger' },
  { key: 'reports', label: 'Reports', Icon: IconChart },
  { key: 'timetable', label: 'Timetable', Icon: IconCalendar, to: '/trains' },
  { key: 'settings', label: 'Settings', Icon: IconSettings },
]

function Sidebar() {
  return (
    <aside className="rail" aria-label="Sections">
      <button type="button" className="rail-btn rail-menu" aria-label="Menu">
        <IconMenu />
      </button>

      <nav className="rail-nav">
        {items.map(({ key, label, Icon, to }) =>
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
        disabled
        title="Sign out — not built yet"
      >
        <IconLogout />
      </button>
    </aside>
  )
}

export default Sidebar
