import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { login, signupAuthority } from '../api/client'

/**
 * Authority sign-up (phone + a pre-issued Authority ID + password, active
 * immediately - no OTP, the ID itself is the proof) and sign-in (phone +
 * password only).
 */
function AuthorityAuth() {
  const navigate = useNavigate()
  const [mode, setMode] = useState('login') // 'login' | 'signup'

  const [phoneNumber, setPhoneNumber] = useState('')
  const [authorityId, setAuthorityId] = useState('')
  const [password, setPassword] = useState('')

  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)
  const [busy, setBusy] = useState(false)

  async function handleLogin(event) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login({ phoneNumber, password })
      navigate('/station-master', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleSignup(event) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await signupAuthority({ phoneNumber, authorityId, password })
      setMode('login')
      setNotice('Account created. Sign in with your phone number and password.')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="page-header">
        <p className="page-eyebrow">Authority</p>
        <h1 className="page-title">{mode === 'signup' ? 'Create Account' : 'Sign In'}</h1>
      </div>

      <section className="panel" style={{ maxWidth: 420 }}>
        <div className="auth-tabs">
          <button
            type="button"
            className={`auth-tab ${mode === 'login' ? 'is-active' : ''}`}
            onClick={() => {
              setMode('login')
              setError(null)
            }}
          >
            Sign In
          </button>
          <button
            type="button"
            className={`auth-tab ${mode === 'signup' ? 'is-active' : ''}`}
            onClick={() => {
              setMode('signup')
              setError(null)
            }}
          >
            Sign Up
          </button>
        </div>

        {notice && !error && <p className="form-hint">{notice}</p>}
        {error && <p className="form-hint form-hint-error">{error}</p>}

        {mode === 'login' && (
          <form className="delay-form auth-form" onSubmit={handleLogin}>
            <div className="field">
              <label htmlFor="a-login-phone">Phone Number</label>
              <input
                id="a-login-phone"
                type="tel"
                placeholder="+8801XXXXXXXXX"
                value={phoneNumber}
                onChange={(event) => setPhoneNumber(event.target.value)}
                disabled={busy}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="a-login-password">Password</label>
              <input
                id="a-login-password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                disabled={busy}
                autoComplete="current-password"
                required
              />
            </div>
            <button type="submit" className="run-button" disabled={busy}>
              {busy ? 'Signing in…' : 'Sign In'}
            </button>
          </form>
        )}

        {mode === 'signup' && (
          <form className="delay-form auth-form" onSubmit={handleSignup}>
            <div className="field">
              <label htmlFor="a-signup-phone">Phone Number</label>
              <input
                id="a-signup-phone"
                type="tel"
                placeholder="+8801XXXXXXXXX"
                value={phoneNumber}
                onChange={(event) => setPhoneNumber(event.target.value)}
                disabled={busy}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="a-signup-id">Authority ID</label>
              <input
                id="a-signup-id"
                type="text"
                placeholder="BR-AUTH-XXXX"
                value={authorityId}
                onChange={(event) => setAuthorityId(event.target.value)}
                disabled={busy}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="a-signup-password">Password</label>
              <input
                id="a-signup-password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                disabled={busy}
                autoComplete="new-password"
                required
              />
            </div>
            <button type="submit" className="run-button" disabled={busy}>
              {busy ? 'Creating…' : 'Sign Up'}
            </button>
          </form>
        )}
      </section>
    </>
  )
}

export default AuthorityAuth
