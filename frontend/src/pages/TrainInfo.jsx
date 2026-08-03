import { useMemo, useState } from 'react'

import { ErrorMessage, Loading } from '../components/Feedback'
import { IconTrain } from '../components/icons'
import { fetchTrainInfo } from '../api/client'
import { useApi } from '../api/useApi'
import './Dashboard.css'

/**
 * Train Info — every service in the network, for a passenger deciding which
 * train and seat class to book.
 *
 * The search box filters on name, number and either endpoint at once, since
 * a passenger is as likely to look up "Sylhet" as "Parabat".
 */
function TrainInfo() {
  const { data, loading, error } = useApi(fetchTrainInfo)
  const [query, setQuery] = useState('')

  const trains = useMemo(() => {
    if (!data) return []
    const q = query.trim().toLowerCase()
    if (!q) return data.trains
    return data.trains.filter((train) =>
      [train.name, train.number, train.origin, train.destination]
        .join(' ')
        .toLowerCase()
        .includes(q),
    )
  }, [data, query])

  const header = (
    <div className="page-header">
      <p className="page-eyebrow">Passenger View</p>
      <h1 className="page-title">Trains &amp; Routes</h1>
      <p className="page-subtitle">
        Browse every intercity train Bangladesh Railway runs, with the route it
        follows and the fare for each seat class.
      </p>
    </div>
  )

  if (loading) {
    return (
      <>
        {header}
        <Loading what="the train list" />
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

  return (
    <>
      {header}

      <div className="field" style={{ maxWidth: 360, marginBottom: 20 }}>
        <label htmlFor="train-search">Search</label>
        <input
          id="train-search"
          type="text"
          placeholder="Train name, number or station"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </div>

      <section className="journey-list">
        {trains.map((train) => (
          <article className="journey-card" key={train.number}>
            <div className="journey-top">
              <div className="journey-head">
                <span className="journey-icon" aria-hidden="true">
                  <IconTrain />
                </span>
                <div>
                  <h2 className="journey-train">
                    {train.name}
                    <span className="journey-no">#{train.number}</span>
                  </h2>
                  <p className="journey-route">
                    {train.origin} <span aria-hidden="true">→</span> {train.destination}
                  </p>
                </div>
              </div>
            </div>

            <dl className="journey-facts">
              <div>
                <dt>Distance</dt>
                <dd>{train.distanceKm} km</dd>
              </div>
              <div>
                <dt>Scheduled halts</dt>
                <dd>{train.scheduledHalts}</dd>
              </div>
              <div>
                <dt>Stations served</dt>
                <dd>{train.route.length}</dd>
              </div>
            </dl>

            <div className="seat-class-row">
              {train.seatClasses.map((seat) => (
                <span className="seat-chip" key={seat.code}>
                  {seat.label}
                  <strong>৳{seat.fare}</strong>
                </span>
              ))}
            </div>
          </article>
        ))}

        {trains.length === 0 && (
          <p className="table-note">No train matches "{query}".</p>
        )}
      </section>
    </>
  )
}

export default TrainInfo
