import { NavLink } from 'react-router-dom'

/**
 * Top navigation bar, shown on every page.
 *
 * NavLink works like a normal link, but react-router automatically gives it
 * the class "active" when its `to` matches the current URL — that is how the
 * current page gets highlighted in amber.
 */
function Navbar() {
  return (
    <header className="navbar">
      <div className="navbar-brand">
        <span className="navbar-mark" aria-hidden="true">
          <span></span>
          <span></span>
          <span></span>
        </span>
        <span>
          RailBot <em>BD</em>
        </span>
      </div>

      <nav className="navbar-links">
        <NavLink to="/passenger">Passenger Dashboard</NavLink>
        <NavLink to="/station-master">Station Master</NavLink>
      </nav>
    </header>
  )
}

export default Navbar
