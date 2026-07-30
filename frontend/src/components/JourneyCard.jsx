import StatusBadge from './StatusBadge'

/**
 * One booked journey.
 *
 * When a train is delayed the scheduled time is struck through and the new
 * expected time is shown beside it, so the passenger sees both at once.
 */
function JourneyCard({ journey }) {
  const isLate = journey.status === 'delayed'

  return (
    <article className={`journey-card journey-${journey.status}`}>
      <div className="journey-top">
        <div>
          <h2 className="journey-train">
            {journey.train}
            <span className="journey-no">#{journey.trainNo}</span>
          </h2>
          <p className="journey-route">
            {journey.from} <span aria-hidden="true">→</span> {journey.to}
          </p>
        </div>
        <StatusBadge status={journey.status} />
      </div>

      <dl className="journey-facts">
        <div>
          <dt>Date</dt>
          <dd>{journey.date}</dd>
        </div>
        <div>
          <dt>Departure</dt>
          <dd>
            {isLate ? (
              <>
                <s className="time-old">{journey.scheduledDeparture}</s>{' '}
                <strong className="time-new">{journey.expectedDeparture}</strong>
              </>
            ) : (
              journey.scheduledDeparture
            )}
          </dd>
        </div>
        <div>
          <dt>Platform</dt>
          <dd>{journey.platform}</dd>
        </div>
        <div>
          <dt>Coach / Seat</dt>
          <dd>{journey.coach}</dd>
        </div>
      </dl>

      {isLate && (
        <p className="journey-delay">Running {journey.delayMinutes} minutes late</p>
      )}

      {journey.agentNote && (
        <p className="agent-note">
          <span className="agent-note-label">RailBot</span>
          {journey.agentNote}
        </p>
      )}
    </article>
  )
}

export default JourneyCard
