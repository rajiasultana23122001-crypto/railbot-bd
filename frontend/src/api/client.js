/**
 * Talks to the Django API.
 *
 * 8000 is Django's own default port. The base URL can be overridden with
 * VITE_API_URL when the backend is not on localhost — useful later for a
 * deployed build.
 */
const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const TOKEN_KEY = 'railbot_token'
const ROLE_KEY = 'railbot_role'
const PHONE_KEY = 'railbot_phone'

export const ROLE_PASSENGER = 'passenger'
export const ROLE_AUTHORITY = 'authority'

export function getAuthToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function getRole() {
  return localStorage.getItem(ROLE_KEY)
}

export function getPhoneNumber() {
  return localStorage.getItem(PHONE_KEY)
}

function setAuth({ token, role, phoneNumber }) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(ROLE_KEY, role)
  localStorage.setItem(PHONE_KEY, phoneNumber)
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(ROLE_KEY)
  localStorage.removeItem(PHONE_KEY)
}

/**
 * Fetch a path from the API and return the parsed JSON.
 * Throws with a readable message so the dashboards can show what went wrong.
 * The thrown error also carries `.status`, so a 401/403 can be told apart
 * from any other failure without parsing the message text.
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

/** Adds the signed-in user's bearer token to a request's headers, if any. */
function withAuth(options = {}) {
  const token = getAuthToken()
  if (!token) return options
  return {
    ...options,
    headers: { ...options.headers, Authorization: `Bearer ${token}` },
  }
}

function postJSON(path, body) {
  return request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

// ---------------- Auth ----------------

export function signupPassenger({ phoneNumber, nidNumber, password }) {
  return postJSON('/api/auth/passenger/signup', {
    phone_number: phoneNumber,
    nid_number: nidNumber,
    password,
  })
}

export function verifyPassengerSignup({ phoneNumber, code }) {
  return postJSON('/api/auth/passenger/verify-signup', {
    phone_number: phoneNumber,
    code,
  })
}

export function signupAuthority({ phoneNumber, authorityId, password }) {
  return postJSON('/api/auth/authority/signup', {
    phone_number: phoneNumber,
    authority_id: authorityId,
    password,
  })
}

/** Shared login for both roles. Stores the token and role on success. */
export async function login({ phoneNumber, password }) {
  const data = await postJSON('/api/auth/login', {
    phone_number: phoneNumber,
    password,
  })
  setAuth({ token: data.token, role: data.role, phoneNumber: data.phoneNumber })
  return data
}

export function logout() {
  clearAuth()
}

// ---------------- Data ----------------

/** Passenger-only. */
export function fetchJourneys() {
  return request('/api/journeys', withAuth())
}

/** Authority-only. */
export function fetchStation(code) {
  return request(`/api/station/${code}`, withAuth())
}

/** Authority-only. */
export function fetchTrains() {
  return request('/api/trains', withAuth())
}

/**
 * Every train in the network with its route and seat class fares - the
 * Timetable, open to either signed-in role.
 */
export function fetchTrainInfo() {
  return request('/api/train-info', withAuth())
}

/**
 * Ask the backend to run one Observe - Reason - Act cycle across all five
 * agents. Resolves with a summary of what each agent did. Authority-only.
 */
export function runAgentCycle() {
  return request('/api/agents/run', withAuth({ method: 'POST' }))
}

/**
 * Report a train as running late. The backend applies the delay and then runs
 * a full agent cycle, so the response describes everything that followed.
 * Authority-only.
 */
export function reportDelay({ trainNo, minutes }) {
  return request(
    '/api/delays',
    withAuth({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ trainNo, minutes }),
    }),
  )
}
