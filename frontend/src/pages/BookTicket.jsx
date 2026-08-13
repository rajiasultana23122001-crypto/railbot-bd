import { useState } from 'react'
import { Link } from 'react-router-dom'

import SeatPicker from '../components/SeatPicker'
import { ErrorMessage, Loading } from '../components/Feedback'
import { IconTicket } from '../components/icons'
import {
  createBooking,
  fetchSeats,
  fetchStations,
  searchTrains,
} from '../api/client'
import { useApi, useAuthRedirectOnFailure } from '../api/useApi'
import './Dashboard.css'

const MONTHS = [
  'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
]

/** ISO (from <input type="date">) to the "1 Aug 2026" style the rest of the
 * app already displays travel dates in. */
function formatDisplayDate(iso) {
  if (!iso) return ''
  const [year, month, day] = iso.split('-').map(Number)
  return `${day} ${MONTHS[month - 1]} ${year}`
}

function formatDuration(minutes) {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return `${h}h ${m}m`
}

const STEPS = [
  { key: 'search', label: 'Search' },
  { key: 'results', label: 'Select Train' },
  { key: 'seats', label: 'Seats' },
  { key: 'review', label: 'Review' },
  { key: 'confirmed', label: 'Ticket' },
]

/**
 * The booking flow — search a route, pick a train and class, optionally pick
 * seats, enter who's travelling, confirm. Modeled on eticket.railway.gov.bd's
 * own steps, built entirely from the form/card classes the rest of the app
 * already defines in Dashboard.css.
 */
function BookTicket() {
  const { data: stationsData, loading: stationsLoading, error: stationsError, errorStatus } =
    useApi(fetchStations)
  useAuthRedirectOnFailure(errorStatus)

  const [step, setStep] = useState('search')

  // ---- search ----
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [date, setDate] = useState('')
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState(null)
  const [results, setResults] = useState([])

  // ---- train + class ----
  const [selectedTrain, setSelectedTrain] = useState(null)
  const [selectedClass, setSelectedClass] = useState(null)

  // ---- seats ----
  const [seatCount, setSeatCount] = useState(1)
  const [seatMap, setSeatMap] = useState(null)
  const [seatsLoading, setSeatsLoading] = useState(false)
  const [seatsError, setSeatsError] = useState(null)
  const [selectedSeats, setSelectedSeats] = useState([])

  // ---- passengers + confirm ----
  const [passengers, setPassengers] = useState([])
  const [confirming, setConfirming] = useState(false)
  const [confirmError, setConfirmError] = useState(null)
  const [booking, setBooking] = useState(null)

  const today = new Date().toISOString().slice(0, 10)

  function swapStations() {
    setFrom(to)
    setTo(from)
  }

  async function handleSearch(event) {
    event.preventDefault()
    setSearching(true)
    setSearchError(null)
    try {
      const data = await searchTrains({ from, to, date: formatDisplayDate(date) })
      setResults(data.trains)
      setStep('results')
    } catch (err) {
      setSearchError(err.message)
    } finally {
      setSearching(false)
    }
  }

  async function pickClass(train, seatClass) {
    setSelectedTrain(train)
    setSelectedClass(seatClass)
    setSeatCount(1)
    setSelectedSeats([])
    setSeatMap(null)
    setSeatsError(null)
    setStep('seats')

    setSeatsLoading(true)
    try {
      const data = await fetchSeats({
        trainId: train.trainId,
        seatClass: seatClass.code,
        date: formatDisplayDate(date),
      })
      setSeatMap(data)
    } catch (err) {
      setSeatsError(err.message)
    } finally {
      setSeatsLoading(false)
    }
  }

  function changeSeatCount(next) {
    const max = Math.min(6, selectedClass?.availableSeats ?? 1)
    const clamped = Math.max(1, Math.min(next, max))
    setSeatCount(clamped)
    setSelectedSeats((current) => current.slice(0, clamped))
  }

  function toggleSeat(seat) {
    setSelectedSeats((current) =>
      current.includes(seat)
        ? current.filter((s) => s !== seat)
        : current.length < seatCount
          ? [...current, seat]
          : current,
    )
  }

  function goToReview() {
    setPassengers(
      Array.from({ length: seatCount }, (_, i) => passengers[i] ?? { name: '', age: '', idNumber: '' }),
    )
    setConfirmError(null)
    setStep('review')
  }

  function updatePassenger(index, field, value) {
    setPassengers((current) =>
      current.map((p, i) => (i === index ? { ...p, [field]: value } : p)),
    )
  }

  async function handleConfirm() {
    setConfirming(true)
    setConfirmError(null)
    try {
      const data = await createBooking({
        trainId: selectedTrain.trainId,
        date: formatDisplayDate(date),
        from,
        to,
        seatClass: selectedClass.code,
        seatNumbers: selectedSeats.length === seatCount ? selectedSeats : undefined,
        passengers: passengers.map((p) => ({
          name: p.name.trim(),
          age: p.age ? Number(p.age) : undefined,
          idNumber: p.idNumber.trim() || undefined,
        })),
      })
      setBooking(data.booking)
      setStep('confirmed')
    } catch (err) {
      setConfirmError(err.message)
    } finally {
      setConfirming(false)
    }
  }

  function startOver() {
    setStep('search')
    setResults([])
    setSelectedTrain(null)
    setSelectedClass(null)
    setBooking(null)
    setConfirmError(null)
  }

  const header = (
    <div className="page-header">
      <p className="page-eyebrow">Passenger View</p>
      <h1 className="page-title">Book a Ticket</h1>
      <p className="page-subtitle">
        Search a route, pick a train and class, and confirm — the ticket
        appears on your dashboard the moment it's booked.
      </p>
    </div>
  )

  if (stationsLoading) {
    return (
      <>
        {header}
        <Loading what="the station list" />
      </>
    )
  }

  if (errorStatus === 401 || errorStatus === 403) return null

  if (stationsError) {
    return (
      <>
        {header}
        <ErrorMessage message={stationsError} />
      </>
    )
  }

  const stations = stationsData.stations
  const stepIndex = STEPS.findIndex((s) => s.key === step)

  return (
    <>
      {header}

      <nav className="step-tabs" aria-label="Booking progress">
        {STEPS.map((s, i) => (
          <span
            key={s.key}
            className={`step-tab ${i === stepIndex ? 'is-active' : ''} ${i < stepIndex ? 'is-done' : ''}`}
          >
            {i + 1}. {s.label}
          </span>
        ))}
      </nav>

      {step === 'search' && (
        <section className="panel">
          <h2 className="panel-title">Search Trains</h2>
          {searchError && <ErrorMessage message={searchError} />}
          <form className="delay-form" onSubmit={handleSearch}>
            <div className="field">
              <label htmlFor="from-station">From</label>
              <select
                id="from-station"
                value={from}
                onChange={(e) => setFrom(e.target.value)}
                required
              >
                <option value="" disabled>Select station</option>
                {stations.map((s) => (
                  <option key={s.code} value={s.code}>{s.name}</option>
                ))}
              </select>
            </div>

            <button
              type="button"
              className="run-button"
              style={{ height: 42 }}
              onClick={swapStations}
              aria-label="Swap From and To"
              title="Swap"
            >
              ⇄
            </button>

            <div className="field">
              <label htmlFor="to-station">To</label>
              <select
                id="to-station"
                value={to}
                onChange={(e) => setTo(e.target.value)}
                required
              >
                <option value="" disabled>Select station</option>
                {stations.map((s) => (
                  <option key={s.code} value={s.code}>{s.name}</option>
                ))}
              </select>
            </div>

            <div className="field field-narrow">
              <label htmlFor="travel-date">Date</label>
              <input
                id="travel-date"
                type="date"
                min={today}
                value={date}
                onChange={(e) => setDate(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="run-button" disabled={searching}>
              {searching ? 'Searching…' : 'Search Train'}
            </button>
          </form>
        </section>
      )}

      {step === 'results' && (
        <>
          <button type="button" className="run-button" onClick={() => setStep('search')} style={{ marginBottom: 16 }}>
            ← New Search
          </button>

          {results.length === 0 ? (
            <p className="placeholder">No trains run between these two stations.</p>
          ) : (
            <section className="journey-list">
              {results.map((train) => (
                <article className="journey-card" key={train.trainId}>
                  <div className="journey-top">
                    <div className="journey-head">
                      <span className="journey-icon" aria-hidden="true">
                        <IconTicket />
                      </span>
                      <div>
                        <h2 className="journey-train">
                          {train.name}
                          <span className="journey-no">#{train.number}</span>
                        </h2>
                        <p className="journey-route">
                          {train.from} <span aria-hidden="true">→</span> {train.to}
                        </p>
                      </div>
                    </div>
                  </div>

                  <dl className="journey-facts">
                    <div>
                      <dt>Departs</dt>
                      <dd>{train.departure}</dd>
                    </div>
                    <div>
                      <dt>Arrives</dt>
                      <dd>{train.arrival}</dd>
                    </div>
                    <div>
                      <dt>Duration</dt>
                      <dd>{formatDuration(train.durationMinutes)}</dd>
                    </div>
                    <div>
                      <dt>Distance</dt>
                      <dd>{train.distanceKm} km</dd>
                    </div>
                  </dl>

                  <div className="class-option-row">
                    {train.seatClasses.map((cls) => (
                      <button
                        type="button"
                        key={cls.code}
                        className="class-option"
                        disabled={cls.availableSeats === 0}
                        onClick={() => pickClass(train, cls)}
                      >
                        <span className="class-option-label">{cls.label}</span>
                        <span className="class-option-fare">৳{cls.fare}</span>
                        <span className="class-option-seats">
                          {cls.availableSeats === 0
                            ? 'Sold out'
                            : `${cls.availableSeats} of ${cls.totalSeats} left`}
                        </span>
                      </button>
                    ))}
                  </div>
                </article>
              ))}
            </section>
          )}
        </>
      )}

      {step === 'seats' && selectedTrain && selectedClass && (
        <section className="panel">
          <h2 className="panel-title">
            {selectedTrain.name} · {selectedClass.label}
          </h2>
          <p className="form-hint">
            {selectedTrain.from} → {selectedTrain.to} · {formatDisplayDate(date)} ·
            ৳{selectedClass.fare} per seat
          </p>

          <div className="field field-narrow" style={{ marginBottom: 16 }}>
            <label htmlFor="seat-count">Passengers</label>
            <input
              id="seat-count"
              type="number"
              min={1}
              max={Math.min(6, selectedClass.availableSeats)}
              value={seatCount}
              onChange={(e) => changeSeatCount(Number(e.target.value) || 1)}
            />
          </div>

          {seatsLoading && <Loading what="the seat map" />}
          {seatsError && <ErrorMessage message={seatsError} />}

          {seatMap && (
            <>
              <p className="form-hint">
                Optionally pick {seatCount} specific seat{seatCount > 1 ? 's' : ''} below,
                or leave none selected and RailBot will assign them.
              </p>
              <SeatPicker
                seats={seatMap.availableSeats}
                count={seatCount}
                selected={selectedSeats}
                onToggle={toggleSeat}
              />
            </>
          )}

          <button
            type="button"
            className="run-button"
            style={{ marginTop: 20 }}
            disabled={!seatMap || (selectedSeats.length !== 0 && selectedSeats.length !== seatCount)}
            onClick={goToReview}
          >
            Continue
          </button>
          {selectedSeats.length !== 0 && selectedSeats.length !== seatCount && (
            <p className="form-hint form-hint-error">
              Pick {seatCount} seat{seatCount > 1 ? 's' : ''}, or none to let RailBot assign them.
            </p>
          )}
        </section>
      )}

      {step === 'review' && selectedTrain && selectedClass && (
        <section className="panel">
          <h2 className="panel-title">Review &amp; Confirm</h2>

          <dl className="journey-facts" style={{ marginTop: 0, paddingTop: 0, borderTop: 'none' }}>
            <div>
              <dt>Train</dt>
              <dd>{selectedTrain.name} #{selectedTrain.number}</dd>
            </div>
            <div>
              <dt>Route</dt>
              <dd>{selectedTrain.from} → {selectedTrain.to}</dd>
            </div>
            <div>
              <dt>Date</dt>
              <dd>{formatDisplayDate(date)}</dd>
            </div>
            <div>
              <dt>Class</dt>
              <dd>{selectedClass.label}</dd>
            </div>
          </dl>

          <div className="fare-row-list" style={{ marginTop: 18 }}>
            {passengers.map((p, i) => (
              <div className="field" key={i} style={{ marginBottom: 12 }}>
                <label htmlFor={`pax-name-${i}`}>
                  {selectedSeats[i] ? `Seat ${selectedSeats[i]}` : `Passenger ${i + 1}`} — Name
                </label>
                <input
                  id={`pax-name-${i}`}
                  type="text"
                  value={p.name}
                  onChange={(e) => updatePassenger(i, 'name', e.target.value)}
                  required
                />
                <div className="delay-form" style={{ marginTop: 8 }}>
                  <div className="field field-narrow">
                    <label htmlFor={`pax-age-${i}`}>Age</label>
                    <input
                      id={`pax-age-${i}`}
                      type="number"
                      min={0}
                      value={p.age}
                      onChange={(e) => updatePassenger(i, 'age', e.target.value)}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor={`pax-id-${i}`}>NID / Passport (optional)</label>
                    <input
                      id={`pax-id-${i}`}
                      type="text"
                      value={p.idNumber}
                      onChange={(e) => updatePassenger(i, 'idNumber', e.target.value)}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="fare-row">
            <span>{selectedClass.label} × {passengers.length}</span>
            <span>৳{selectedClass.fare} each</span>
          </div>
          <div className="fare-row">
            <span>Total fare</span>
            <span>৳{selectedClass.fare * passengers.length}</span>
          </div>

          {confirmError && <ErrorMessage message={confirmError} />}

          <button
            type="button"
            className="run-button"
            style={{ marginTop: 16 }}
            disabled={confirming || passengers.some((p) => !p.name.trim())}
            onClick={handleConfirm}
          >
            {confirming ? 'Processing payment…' : 'Pay & Confirm'}
          </button>
        </section>
      )}

      {step === 'confirmed' && booking && (
        <section className="panel">
          <h2 className="panel-title">Booking Confirmed</h2>
          <p className="pnr-label">PNR</p>
          <p className="pnr-display">{booking.pnr}</p>

          <dl className="journey-facts">
            <div>
              <dt>Train</dt>
              <dd>{booking.train} #{booking.trainNo}</dd>
            </div>
            <div>
              <dt>Route</dt>
              <dd>{booking.from} → {booking.to}</dd>
            </div>
            <div>
              <dt>Date</dt>
              <dd>{booking.date}</dd>
            </div>
            <div>
              <dt>Departure</dt>
              <dd>{booking.scheduledDeparture}</dd>
            </div>
            <div>
              <dt>Class / Seats</dt>
              <dd>{booking.seatClass} / {booking.seatNumbers.join(', ')}</dd>
            </div>
            <div>
              <dt>Fare Paid</dt>
              <dd>৳{booking.farePaid}</dd>
            </div>
          </dl>

          <div className="delay-form" style={{ marginTop: 20 }}>
            <button type="button" className="run-button" onClick={startOver}>
              Book Another Ticket
            </button>
            <Link to="/passenger" className="run-button" style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center' }}>
              Go to My Journeys
            </Link>
          </div>
        </section>
      )}
    </>
  )
}

export default BookTicket
