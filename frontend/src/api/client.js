/**
 * Talks to the Django API.
 *
 * 8000 is Django's own default port. The base URL can be overridden with
 * VITE_API_URL when the backend is not on localhost — useful later for a
 * deployed build.
 */
const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const MANAGER_TOKEN_KEY = 'railbot_manager_token'

/** The signed-in Station Manager's bearer token, or null if none. */
export function getManagerToken() {
  return localStorage.getItem(MANAGER_TOKEN_KEY)
}

export function setManagerToken(token) {
  localStorage.setItem(MANAGER_TOKEN_KEY, token)
}

export function clearManagerToken() {
  localStorage.removeItem(MANAGER_TOKEN_KEY)
}

/**
 * Fetch a path from the API and return the parsed JSON.
 * Throws with a readable message so the dashboards can show what went wrong.
 * The thrown error also carries `.status`, so a 401 can be told apart from
 * any other failure without parsing the message text.
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

    const err = new Error(
      detail ?? `API responded with ${response.status} for ${path}`,
    )
    err.status = response.status
    throw err
  }

  return response.json()
}

/** Adds the Station Manager's bearer token to a request's headers, if signed in. */
function withManagerAuth(options = {}) {
  const token = getManagerToken()
  if (!token) return options
  return {
    ...options,
    headers: { ...options.headers, Authorization: `Bearer ${token}` },
  }
}

export function fetchJourneys() {
  return request('/api/journeys')
}

/** Station-manager-only: needs a signed-in manager's bearer token. */
export function fetchStation(code) {
  return request(`/api/station/${code}`, withManagerAuth())
}

/** Station Manager sign-in. Stores the token on success. */
export async function loginManager({ username, password }) {
  const data = await request('/api/auth/manager/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  setManagerToken(data.token)
  return data
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
  return request('/api/agents/run', withManagerAuth({ method: 'POST' }))
}

/**
 * Report a train as running late. The backend applies the delay and then runs
 * a full agent cycle, so the response describes everything that followed.
 */
export function reportDelay({ trainNo, minutes }) {
  return request(
    '/api/delays',
    withManagerAuth({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ trainNo, minutes }),
    }),
  )
}
