import JourneyCard from '../components/JourneyCard'
import { ErrorMessage, Loading } from '../components/Feedback'
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
    <div className="page-header">
      <p className="page-eyebrow">Passenger View</p>
      <h1 className="page-title">Your Journeys</h1>
      <p className="page-subtitle">
        Track your booked trains and see delay updates the moment RailBot's
        agents detect them.
      </p>
    </div>
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
    { label: 'Upcoming journeys', value: journeys.length },
    { label: 'Currently delayed', value: delayedCount, tone: 'late' },
    { label: 'Flagged at risk', value: atRiskCount, tone: 'warn' },
    { label: 'Alerts received', value: data.alertsReceived },
  ]

  return (
    <>
      {header}

      <section className="stat-row" aria-label="Journey summary">
        {stats.map((stat) => (
          <div className="stat-tile" key={stat.label}>
            <p className={`stat-value ${stat.tone ? `stat-${stat.tone}` : ''}`}>
              {stat.value}
            </p>
            <p className="stat-label">{stat.label}</p>
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
