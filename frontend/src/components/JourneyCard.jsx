import { useState } from 'react'

import StatusBadge from './StatusBadge'
import { IconTrain } from './icons'
import { cancelBooking } from '../api/client'

/**
 * One booked journey.
 *
 * When a train is delayed the scheduled time is struck through and the new
 * expected time is shown beside it, so the passenger sees both at once.
 * A cancelled ticket stays visible (booking history), just dimmed and with
 * its own badge instead of the agent-driven on-time/at-risk/delayed one.
 *
 * @param {{ journey: object, onCancelled?: () => void }} props
 */
function JourneyCard({ journey, onCancelled }) {
  const isLate = journey.status === 'delayed'
  const isCancelled = journey.bookingStatus === 'cancelled'
  const [cancelling, setCancelling] = useState(false)
  const [cancelError, setCancelError] = useState(null)

  async function handleCancel() {
    setCancelling(true)
    setCancelError(null)
    try {
      await cancelBooking(journey.bookingId)
      onCancelled?.()
    } catch (err) {
      setCancelError(err.message)
      setCancelling(false)
    }
  }

  return (
    <article
      className={`journey-card journey-${journey.status} ${isCancelled ? 'journey-cancelled' : ''}`}
    >
      <div className="journey-top">
        <div className="journey-head">
          <span className="journey-icon" aria-hidden="true">
            <IconTrain />
          </span>
          <div>
            <h2 className="journey-train">
              {journey.train}
              <span className="journey-no">#{journey.trainNo}</span>
            </h2>
            <p className="journey-route">
              {journey.from} <span aria-hidden="true">→</span> {journey.to}
            </p>
          </div>
        </div>
        {isCancelled ? (
          <span className="badge badge-cancelled">Cancelled</span>
        ) : (
          <StatusBadge status={journey.status} />
        )}
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
          <dd>{journey.platform ?? '—'}</dd>
        </div>
        <div>
          <dt>Coach / Seat</dt>
          <dd>{journey.coach}</dd>
        </div>
        {journey.pnr && (
          <div>
            <dt>PNR</dt>
            <dd>{journey.pnr}</dd>
          </div>
        )}
        {journey.passengerCount > 1 && (
          <div>
            <dt>Passengers</dt>
            <dd>{journey.passengerCount}</dd>
          </div>
        )}
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

      {!isCancelled && journey.bookingStatus === 'confirmed' && journey.bookingId && (
        <div className="journey-actions">
          {cancelError && <span className="form-hint form-hint-error">{cancelError}</span>}
          <button
            type="button"
            className="run-button run-button-danger"
            onClick={handleCancel}
            disabled={cancelling}
          >
            {cancelling ? 'Cancelling…' : 'Cancel Ticket'}
          </button>
        </div>
      )}
    </article>
  )
}

export default JourneyCard
