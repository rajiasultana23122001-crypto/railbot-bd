import JourneyCard from '../components/JourneyCard'
import RouteMap from '../components/RouteMap'
import TrainArt from '../components/TrainArt'
import { ErrorMessage, Loading } from '../components/Feedback'
import { IconAlert, IconBell, IconClock, IconTrain } from '../components/icons'
import { fetchJourneys, getPhoneNumber } from '../api/client'
import { useApi, useAuthRedirectOnFailure } from '../api/useApi'
import './Dashboard.css'

/**
 * Passenger Dashboard — what a traveller sees.
 *
 * Journeys come from the Django API. The summary figures are derived from that
 * response rather than stored separately, so they cannot drift out of step.
 */
function PassengerDashboard() {
  const { data, loading, error, errorStatus } = useApi(fetchJourneys)
  useAuthRedirectOnFailure(errorStatus)

  const header = (
    <>
      {/* The route lines used to float loose behind the heading; they are
          the backdrop to the train now, which keeps the two from
          overlapping and gives the page one thing to look at, not two. */}
      <section className="hero-band bracketed" aria-hidden="true">
        <RouteMap />
        <TrainArt />
      </section>

      <div className="page-header">
        <p className="page-eyebrow">Passenger View</p>
        <h1 className="page-title">Your Journeys</h1>
        <p className="page-subtitle">
          Track your booked trains and see delay updates the moment RailBot's
          agents detect them.
        </p>
      </div>
    </>
  )

  if (loading) {
    return (
      <>
        {header}
        <Loading what="your journeys" />
      </>
    )
  }

  // On a 401/403 useAuthRedirectOnFailure logs out and redirects to /auth;
  // render nothing for this one frame rather than flash the raw error.
  if (errorStatus === 401 || errorStatus === 403) {
    return null
  }

  if (error) {
    return (
      <>
        {header}
        <ErrorMessage message={error} />
      </>
    )
  }

  const journeys = data.journeys
  const delayedCount = journeys.filter((j) => j.status === 'delayed').length
  const atRiskCount = journeys.filter((j) => j.status === 'at-risk').length

  const stats = [
    { label: 'Upcoming journeys', value: journeys.length, Art: IconClock },
    {
      label: 'Currently delayed',
      value: delayedCount,
      tone: 'late',
      Art: IconTrain,
    },
    { label: 'Flagged at risk', value: atRiskCount, tone: 'warn', Art: IconAlert },
    { label: 'Alerts received', value: data.alertsReceived, Art: IconBell },
  ]

  return (
    <>
      {header}

      <section className="stat-row" aria-label="Journey summary">
        {stats.map(({ label, value, tone, Art }) => (
          <div className="stat-tile" key={label}>
            <div className="stat-body">
              <p className={`stat-value ${tone ? `stat-${tone}` : ''}`}>{value}</p>
              <p className="stat-label">{label}</p>
            </div>
            <span className="stat-art" aria-hidden="true">
              <Art />
            </span>
          </div>
        ))}
      </section>

      <section className="journey-list">
        {journeys.length === 0 ? (
          // The API returns only this account's bookings, so an empty list
          // means nothing is booked against this number - worth saying, or it
          // reads as a page that failed to load.
          <p className="placeholder">
            Nothing is booked against {getPhoneNumber() || 'this number'} yet.
            A booking made against it will appear here on its own.
          </p>
        ) : (
          journeys.map((journey) => (
            <JourneyCard journey={journey} key={journey.id} />
          ))
        )}
      </section>
    </>
  )
}

export default PassengerDashboard
