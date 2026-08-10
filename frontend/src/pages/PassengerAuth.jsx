import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import {
  login,
  signupPassenger,
  verifyPassengerSignup,
} from '../api/client'

/**
 * Passenger sign-up (NID + phone + password, then an OTP to confirm the
 * phone) and sign-in (phone + password only - the OTP never runs again
 * after signup).
 */
function PassengerAuth() {
  const navigate = useNavigate()
  const [mode, setMode] = useState('login') // 'login' | 'signup' | 'verify'

  const [phoneNumber, setPhoneNumber] = useState('')
  const [nidNumber, setNidNumber] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')

  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)
  const [busy, setBusy] = useState(false)

  async function handleLogin(event) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login({ phoneNumber, password })
      navigate('/passenger', { replace: true })
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
      await signupPassenger({ phoneNumber, nidNumber, password })
      setMode('verify')
      setNotice('OTP sent to your phone. Enter it below to activate your account.')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function handleVerify(event) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await verifyPassengerSignup({ phoneNumber, code })
      setMode('login')
      setCode('')
      setNotice('Phone verified. Sign in with your phone number and password.')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-screen">
      <div className="page-header">
        <p className="page-eyebrow">Passenger</p>
        <h1 className="page-title">
          {mode === 'signup' ? 'Create Account' : mode === 'verify' ? 'Verify Phone' : 'Sign In'}
        </h1>
      </div>

      <section className="panel auth-panel">
        {mode !== 'verify' && (
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
        )}

        {notice && !error && <p className="form-hint">{notice}</p>}
        {error && <p className="form-hint form-hint-error">{error}</p>}

        {mode === 'login' && (
          <form className="delay-form auth-form" onSubmit={handleLogin}>
            <div className="field">
              <label htmlFor="p-login-phone">Phone Number</label>
              <input
                id="p-login-phone"
                type="tel"
                placeholder="+8801XXXXXXXXX"
                value={phoneNumber}
                onChange={(event) => setPhoneNumber(event.target.value)}
                disabled={busy}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="p-login-password">Password</label>
              <input
                id="p-login-password"
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
              <label htmlFor="p-signup-nid">NID Number</label>
              <input
                id="p-signup-nid"
                type="text"
                placeholder="10 or 17 digits"
                value={nidNumber}
                onChange={(event) => setNidNumber(event.target.value)}
                disabled={busy}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="p-signup-phone">Phone Number</label>
              <input
                id="p-signup-phone"
                type="tel"
                placeholder="+8801XXXXXXXXX"
                value={phoneNumber}
                onChange={(event) => setPhoneNumber(event.target.value)}
                disabled={busy}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="p-signup-password">Password</label>
              <input
                id="p-signup-password"
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

        {mode === 'verify' && (
          <form className="delay-form auth-form" onSubmit={handleVerify}>
            <div className="field">
              <label htmlFor="p-verify-code">OTP Code</label>
              <input
                id="p-verify-code"
                type="text"
                inputMode="numeric"
                placeholder="123456"
                value={code}
                onChange={(event) => setCode(event.target.value)}
                disabled={busy}
                required
              />
            </div>
            <button type="submit" className="run-button" disabled={busy}>
              {busy ? 'Verifying…' : 'Verify'}
            </button>
          </form>
        )}
      </section>
    </div>
  )
}

export default PassengerAuth
