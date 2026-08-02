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
 * Only the first item navigates for now; the rest stand for sections the
 * project has not built yet, so they are marked disabled rather than pretending
 * to work.
 */
const items = [
  { key: 'home', label: 'Overview', Icon: IconHome, active: true },
  { key: 'board', label: 'Boards', Icon: IconGrid },
  { key: 'people', label: 'Passengers', Icon: IconUsers },
  { key: 'reports', label: 'Reports', Icon: IconChart },
  { key: 'timetable', label: 'Timetable', Icon: IconCalendar },
  { key: 'settings', label: 'Settings', Icon: IconSettings },
]

function Sidebar() {
  return (
    <aside className="rail" aria-label="Sections">
      <button type="button" className="rail-btn rail-menu" aria-label="Menu">
        <IconMenu />
      </button>

      <nav className="rail-nav">
        {items.map(({ key, label, Icon, active }) => (
          <button
            key={key}
            type="button"
            className={`rail-btn ${active ? 'is-active' : ''}`}
            aria-label={label}
            aria-current={active ? 'page' : undefined}
            disabled={!active}
            title={active ? label : `${label} — not built yet`}
          >
            <Icon />
          </button>
        ))}
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
