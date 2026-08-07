import { Link } from 'react-router-dom'

/** First screen for anyone not signed in: pick which kind of account this is. */
function AuthLanding() {
  return (
    <>
      <div className="page-header">
        <p className="page-eyebrow">Welcome</p>
        <h1 className="page-title">Sign In to RailBot BD</h1>
        <p className="page-subtitle">
          Choose which kind of account you're signing in with. Passengers and
          station authorities see different tools.
        </p>
      </div>

      <div className="role-pick-grid">
        <Link to="/auth/passenger" className="role-pick-card bracketed">
          <h2 className="panel-title">Passenger</h2>
          <p className="role-pick-desc">
            Track your booked journeys and browse the timetable. Sign up with
            your NID and phone number, OTP-verified.
          </p>
          <span className="role-pick-cta">Continue as Passenger →</span>
        </Link>

        <Link to="/auth/authority" className="role-pick-card bracketed">
          <h2 className="panel-title">Authority</h2>
          <p className="role-pick-desc">
            Run the Station Master Control Panel and the agent cycle. Requires
            a BD Railway-issued Authority ID.
          </p>
          <span className="role-pick-cta">Continue as Authority →</span>
        </Link>
      </div>
    </>
  )
}

export default AuthLanding
