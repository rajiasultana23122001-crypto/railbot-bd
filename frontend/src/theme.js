/**
 * Which theme the interface is drawn in.
 *
 * The choice is written to <html data-theme="..."> — every colour in the app
 * reads a CSS custom property, so switching the attribute repaints everything
 * without a single component re-rendering.
 *
 * index.html applies the stored choice before React mounts, so the page never
 * flashes the wrong theme on load. This module keeps that in sync afterwards.
 */

const STORAGE_KEY = 'railbot-theme'

export const DARK = 'dark'
export const LIGHT = 'light'

/** The theme in effect right now. */
export function getTheme() {
  return document.documentElement.getAttribute('data-theme') === LIGHT ? LIGHT : DARK
}

/** Switch to a theme and remember it for next time. */
export function setTheme(theme) {
  const next = theme === LIGHT ? LIGHT : DARK
  document.documentElement.setAttribute('data-theme', next)
  try {
    localStorage.setItem(STORAGE_KEY, next)
  } catch {
    // Private browsing can refuse storage. The theme still applies for this
    // visit; only remembering it fails, which is not worth surfacing.
  }
  return next
}

/** Flip between the two. */
export function toggleTheme() {
  return setTheme(getTheme() === DARK ? LIGHT : DARK)
}
