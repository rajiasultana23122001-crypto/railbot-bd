import { Navigate } from 'react-router-dom'

import { getAuthToken, getRole, ROLE_AUTHORITY, ROLE_PASSENGER } from '../api/client'

const HOME_FOR_ROLE = {
  [ROLE_PASSENGER]: '/passenger',
  [ROLE_AUTHORITY]: '/station-master',
}

/**
 * Wraps a route element and enforces who may see it.
 *
 * Not signed in at all -> sent to the role picker. Signed in as the wrong
 * role -> sent to that role's own home instead of a bare error, since
 * "you're logged in, just not as that" is a different situation from "you're
 * not logged in". This runs on every render of the wrapped route, so typing
 * the URL directly is blocked exactly like clicking a hidden link would be -
 * the backend enforces the same rule independently (see core/auth.py).
 *
 * @param {{ allow: string[], children: React.ReactNode }} props
 */
function RouteGuard({ allow, children }) {
  const token = getAuthToken()
  const role = getRole()

  if (!token || !role) {
    return <Navigate to="/auth" replace />
  }

  if (!allow.includes(role)) {
    return <Navigate to={HOME_FOR_ROLE[role] ?? '/auth'} replace />
  }

  return children
}

export default RouteGuard
