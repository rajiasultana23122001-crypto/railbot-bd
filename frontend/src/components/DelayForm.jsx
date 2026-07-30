import { useEffect, useState } from 'react'

import { fetchTrains } from '../api/client'

/**
 * Where a station master reports that a train is running late.
 *
 * This is the operator's way into the system: they enter what has happened,
 * and the agents work out what to do about it.
 */
function DelayForm({ onSubmit, busy }) {
  const [trains, setTrains] = useState([])
  const [trainNo, setTrainNo] = useState('')
  const [minutes, setMinutes] = useState('30')
  const [loadError, setLoadError] = useState(null)

  useEffect(() => {
    let active = true
    fetchTrains()
      .then((data) => {
        if (!active) return
        setTrains(data.trains)
        // Preselect the first train so the form is usable in one click.
        if (data.trains.length) setTrainNo(data.trains[0].trainNo)
      })
      .catch((err) => {
        if (active) setLoadError(err.message)
      })
    return () => {
      active = false
    }
  }, [])

  function handleSubmit(event) {
    event.preventDefault()
    onSubmit({ trainNo, minutes: Number(minutes) })
  }

  if (loadError) {
    return <p className="form-hint form-hint-error">{loadError}</p>
  }

  return (
    <form className="delay-form" onSubmit={handleSubmit}>
      <div className="field">
        <label htmlFor="train">Train</label>
        <select
          id="train"
          value={trainNo}
          onChange={(event) => setTrainNo(event.target.value)}
          disabled={busy}
        >
          {trains.map((train) => (
            <option key={train.trainNo} value={train.trainNo}>
              {train.name} #{train.trainNo} — {train.scheduledDeparture}
            </option>
          ))}
        </select>
      </div>

      <div className="field field-narrow">
        <label htmlFor="minutes">Minutes late</label>
        <input
          id="minutes"
          type="number"
          min="1"
          max="300"
          value={minutes}
          onChange={(event) => setMinutes(event.target.value)}
          disabled={busy}
          required
        />
      </div>

      <button type="submit" className="run-button" disabled={busy || !trainNo}>
        {busy ? 'Agents working…' : 'Report delay'}
      </button>
    </form>
  )
}

export default DelayForm
