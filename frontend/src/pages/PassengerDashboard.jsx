import JourneyCard from '../components/JourneyCard'
import { journeys, alertsReceived } from '../data/mockJourneys'
import './Dashboard.css'

/**
 * Passenger Dashboard — what a traveller sees.
 *
 * The summary figures are derived from the journey list rather than hard-coded,
 * so they stay correct once real data arrives from the backend.
 */
function PassengerDashboard() {
  const delayedCount = journeys.filter((j) => j.status === 'delayed').length
  const atRiskCount = journeys.filter((j) => j.status === 'at-risk').length

  const stats = [
    { label: 'Upcoming journeys', value: journeys.length },
    { label: 'Currently delayed', value: delayedCount, tone: 'late' },
    { label: 'Flagged at risk', value: atRiskCount, tone: 'warn' },
    { label: 'Alerts received', value: alertsReceived },
  ]

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
