import { useState } from 'react'

import { DARK, getTheme, toggleTheme } from '../theme'
import { IconMoon, IconSun } from './icons'

/**
 * Switches the interface between the dark control-room theme and the light one.
 *
 * The icon shows what pressing it will do, not what is currently on: a sun
 * while dark, because pressing it brings the light theme.
 */
function ThemeToggle() {
  const [theme, setThemeState] = useState(getTheme)
  const isDark = theme === DARK

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={() => setThemeState(toggleTheme())}
      aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      title={isDark ? 'Light theme' : 'Dark theme'}
    >
      {isDark ? <IconSun /> : <IconMoon />}
    </button>
  )
}

export default ThemeToggle
