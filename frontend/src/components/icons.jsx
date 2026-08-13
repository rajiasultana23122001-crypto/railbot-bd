/**
 * Inline SVG icons.
 *
 * Drawn here rather than pulled from an icon package so the app carries no
 * extra dependency and every icon inherits the surrounding text colour.
 */

const base = {
  width: 20,
  height: 20,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.7,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
}

/** Sun — shown when the dark theme is on, i.e. "switch to light". */
export function IconSun(props) {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2.5v2.2M12 19.3v2.2M4.2 4.2l1.6 1.6M18.2 18.2l1.6 1.6M2.5 12h2.2M19.3 12h2.2M4.2 19.8l1.6-1.6M18.2 5.8l1.6-1.6" />
    </svg>
  )
}

/** Moon — shown when the light theme is on, i.e. "switch to dark". */
export function IconMoon(props) {
  return (
    <svg {...base} {...props}>
      <path d="M20 14.2A8.2 8.2 0 0 1 9.8 4a8.5 8.5 0 1 0 10.2 10.2z" />
    </svg>
  )
}

export function IconMenu(props) {
  return (
    <svg {...base} {...props}>
      <path d="M4 7h16M4 12h16M4 17h16" />
    </svg>
  )
}

export function IconHome(props) {
  return (
    <svg {...base} {...props}>
      <path d="M4 10.5 12 4l8 6.5V19a1 1 0 0 1-1 1h-4v-6H9v6H5a1 1 0 0 1-1-1z" />
    </svg>
  )
}

export function IconGrid(props) {
  return (
    <svg {...base} {...props}>
      <rect x="4" y="4" width="7" height="7" rx="1.5" />
      <rect x="13" y="4" width="7" height="7" rx="1.5" />
      <rect x="4" y="13" width="7" height="7" rx="1.5" />
      <rect x="13" y="13" width="7" height="7" rx="1.5" />
    </svg>
  )
}

export function IconUsers(props) {
  return (
    <svg {...base} {...props}>
      <circle cx="9" cy="8" r="3.2" />
      <path d="M3.5 19a5.5 5.5 0 0 1 11 0" />
      <path d="M16 5.5a3 3 0 0 1 0 5.6M17.5 19a5.4 5.4 0 0 0-2-4.2" />
    </svg>
  )
}

export function IconChart(props) {
  return (
    <svg {...base} {...props}>
      <path d="M5 19V11M10 19V5M15 19v-6M20 19v-9" />
    </svg>
  )
}

export function IconCalendar(props) {
  return (
    <svg {...base} {...props}>
      <rect x="4" y="5.5" width="16" height="14" rx="2" />
      <path d="M4 10h16M9 3.5v4M15 3.5v4" />
    </svg>
  )
}

export function IconSettings(props) {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="3" />
      <path d="M12 3v2.2M12 18.8V21M4.2 7.5l1.9 1.1M17.9 15.4l1.9 1.1M4.2 16.5l1.9-1.1M17.9 8.6l1.9-1.1" />
    </svg>
  )
}

export function IconLogout(props) {
  return (
    <svg {...base} {...props}>
      <path d="M14 5H7a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h7" />
      <path d="M17 15l3-3-3-3M20 12H10" />
    </svg>
  )
}

/** Locomotive seen head-on, used beside a journey's train name. */
export function IconTrain(props) {
  return (
    <svg {...base} {...props}>
      <rect x="6" y="3.5" width="12" height="13" rx="3" />
      <path d="M9 7.5h6M8.5 12h2M13.5 12h2" />
      <path d="M8 16.5 6 20M16 16.5 18 20M9.5 20h5" />
    </svg>
  )
}

/** Warning triangle, for the at-risk figure. */
export function IconAlert(props) {
  return (
    <svg {...base} {...props}>
      <path d="M12 4.5 21 19H3z" />
      <path d="M12 10v4M12 16.4v.2" />
    </svg>
  )
}

/** Bell, for alerts already delivered. */
export function IconBell(props) {
  return (
    <svg {...base} {...props}>
      <path d="M6.5 10a5.5 5.5 0 0 1 11 0c0 4 1.5 5.5 1.5 5.5H5S6.5 14 6.5 10z" />
      <path d="M10 18.5a2 2 0 0 0 4 0" />
    </svg>
  )
}

/** Clock, for the count of upcoming journeys. */
export function IconClock(props) {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 1.8" />
    </svg>
  )
}

/** People on a platform, for the passengers-on-site figure. */
export function IconCrowd(props) {
  return (
    <svg {...base} {...props}>
      <circle cx="7" cy="8" r="2.4" />
      <circle cx="17" cy="8" r="2.4" />
      <circle cx="12" cy="6.5" r="2.6" />
      <path d="M2.5 19a4.5 4.5 0 0 1 9 0M12.5 19a4.5 4.5 0 0 1 9 0M7.5 20a5 5 0 0 1 9 0" />
    </svg>
  )
}

/** Gauge, for station occupancy. */
export function IconGauge(props) {
  return (
    <svg {...base} {...props}>
      <path d="M4 17a8 8 0 1 1 16 0" />
      <path d="M12 17l4-4.5" />
    </svg>
  )
}

/** Platform marker, for platforms under pressure. */
export function IconPlatform(props) {
  return (
    <svg {...base} {...props}>
      <path d="M3 18h18M6 18V9l6-4 6 4v9" />
      <path d="M10 18v-4h4v4" />
    </svg>
  )
}

/** A ticket stub, for the booking flow. */
export function IconTicket(props) {
  return (
    <svg {...base} {...props}>
      <path d="M4 8a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v2a2 2 0 0 0 0 4v2a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-2a2 2 0 0 0 0-4z" />
      <path d="M14 6.5v11" strokeDasharray="2.2 2.2" />
    </svg>
  )
}
