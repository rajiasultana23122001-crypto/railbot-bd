/**
 * Passenger Dashboard — what a traveller sees.
 *
 * Journey cards with live delay status arrive in the next step.
 */
function PassengerDashboard() {
  return (
    <>
      <div className="page-header">
        <p className="page-eyebrow">Passenger View</p>
        <h1 className="page-title">Your Journeys</h1>
        <p className="page-subtitle">
          Track your booked trains and see delay updates the moment RailBot's
          agents detect them.
        </p>
      </div>

      <div className="placeholder">Journey cards are coming in the next step.</div>
    </>
  )
}

export default PassengerDashboard
