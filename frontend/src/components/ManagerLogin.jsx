import { useState } from 'react'

import { loginManager } from '../api/client'

/**
 * Station Manager sign-in gate, shown in place of the panel until a manager
 * token exists. There is no self-service signup for this role — accounts
 * only come from the backend's `create_manager` command.
 */
function ManagerLogin({ onSuccess }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await loginManager({ username, password })
      onSuccess()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel" style={{ maxWidth: 360 }}>
      <h2 className="panel-title">Station Manager Sign-In</h2>
      <form className="delay-form" onSubmit={handleSubmit} style={{ flexDirection: 'column', alignItems: 'stretch' }}>
        <div className="field">
          <label htmlFor="manager-username">Username</label>
          <input
            id="manager-username"
            type="text"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            disabled={busy}
            autoComplete="username"
            required
          />
        </div>
        <div className="field">
          <label htmlFor="manager-password">Password</label>
          <input
            id="manager-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={busy}
            autoComplete="current-password"
            required
          />
        </div>
        {error && <p className="form-hint form-hint-error">{error}</p>}
        <button type="submit" className="run-button" disabled={busy}>
          {busy ? 'Signing in…' : 'Sign in'}
        </button>
      </form>
    </section>
  )
}

export default ManagerLogin
