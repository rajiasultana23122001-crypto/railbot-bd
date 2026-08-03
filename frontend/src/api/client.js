/**
 * Talks to the Django API.
 *
 * 8000 is Django's own default port. The base URL can be overridden with
 * VITE_API_URL when the backend is not on localhost — useful later for a
 * deployed build.
 */
const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/**
 * Fetch a path from the API and return the parsed JSON.
 * Throws with a readable message so the dashboards can show what went wrong.
 */
async function request(path, options) {
  let response
  try {
    response = await fetch(`${API_BASE}${path}`, options)
  } catch {
    // fetch only rejects when the server could not be reached at all.
    throw new Error(
      `Cannot reach the API at ${API_BASE}. Is the Django server running?`,
    )
  }

  if (!response.ok) {
    // The API explains refusals in an "error" field. Surface that rather than
    // a bare status code, so the person using the form knows what to change.
    const detail = await response
      .clone()
      .json()
      .then((body) => body.error)
      .catch(() => null)

    throw new Error(detail ?? `API responded with ${response.status} for ${path}`)
  }

  return response.json()
}

export function fetchJourneys() {
  return request('/api/journeys')
}

export function fetchStation(code) {
  return request(`/api/station/${code}`)
}

export function fetchTrains() {
  return request('/api/trains')
}

/**
 * Every train in the network with its route and seat class fares, for the
 * passenger-facing train browser.
 */
export function fetchTrainInfo() {
  return request('/api/train-info')
}

/**
 * Ask the backend to run one Observe - Reason - Act cycle across all five
 * agents. Resolves with a summary of what each agent did.
 */
export function runAgentCycle() {
  return request('/api/agents/run', { method: 'POST' })
}

/**
 * Report a train as running late. The backend applies the delay and then runs
 * a full agent cycle, so the response describes everything that followed.
 */
export function reportDelay({ trainNo, minutes }) {
  return request('/api/delays', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ trainNo, minutes }),
  })
}
