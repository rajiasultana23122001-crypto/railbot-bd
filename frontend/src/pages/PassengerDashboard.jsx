import JourneyCard from '../components/JourneyCard'
import RouteMap from '../components/RouteMap'
import { ErrorMessage, Loading } from '../components/Feedback'
import { IconAlert, IconBell, IconClock, IconTrain } from '../components/icons'
import { fetchJourneys } from '../api/client'
import { useApi } from '../api/useApi'
import './Dashboard.css'

/**
 * Passenger Dashboard — what a traveller sees.
 *
 * Journeys come from the Django API. The summary figures are derived from that
 * response rather than stored separately, so they cannot drift out of step.
 */
function PassengerDashboard() {
  const { data, loading, error } = useApi(fetchJourneys)

  const header = (
    <>
      <RouteMap />
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
        {journeys.map((journey) => (
          <JourneyCard journey={journey} key={journey.id} />
        ))}
      </section>
    </>
  )
}

export default PassengerDashboard
