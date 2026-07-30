/**
 * Talks to the Flask API.
 *
 * The base URL can be overridden with VITE_API_URL when the backend is not on
 * localhost — useful later for a deployed build.
 */
const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:5000'

/**
 * Fetch a path from the API and return the parsed JSON.
 * Throws with a readable message so the dashboards can show what went wrong.
 */
async function request(path) {
  let response
  try {
    response = await fetch(`${API_BASE}${path}`)
  } catch {
    // fetch only rejects when the server could not be reached at all.
    throw new Error(
      `Cannot reach the API at ${API_BASE}. Is the Flask server running?`,
    )
  }

  if (!response.ok) {
    throw new Error(`API responded with ${response.status} for ${path}`)
  }

  return response.json()
}

export function fetchJourneys() {
  return request('/api/journeys')
}

export function fetchStation(code) {
  return request(`/api/station/${code}`)
}
