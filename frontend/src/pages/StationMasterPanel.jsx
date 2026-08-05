import { useEffect, useState } from 'react'

import BangladeshMap from '../components/BangladeshMap'
import CapacityMeter, { crowdLevel } from '../components/CapacityMeter'
import DelayForm from '../components/DelayForm'
import ManagerLogin from '../components/ManagerLogin'
import Sparkline from '../components/Sparkline'
import StatusBadge from '../components/StatusBadge'
import { ErrorMessage, Loading } from '../components/Feedback'
import {
  clearManagerToken,
  fetchStation,
  getManagerToken,
  reportDelay,
  runAgentCycle,
} from '../api/client'
import { useApi } from '../api/useApi'
import './Dashboard.css'

/** The station this panel monitors. Later this becomes a picker. */
const STATION_CODE = 'DHKA'

/**
 * Short tag shown in the coloured disc beside each agent's log entry.
 *
 * Two letters from the first word, not one from each: "Risk Agent" and
 * "Resource Agent" would both come out as RA otherwise, and the two do very
 * different things.
 */
function initials(agentName) {
  return agentName.slice(0, 2).toUpperCase()
}

/** Turn one agent's result into a single line for the summary strip. */
function summarise(result) {
  switch (result.agent) {
    case 'Risk Agent': {
      const { flagged, cleared } = result
      if (!flagged.length && !cleared.length) return 'no change in risk'
      const parts = []
      if (flagged.length) parts.push(`flagged ${flagged.join(', ')}`)
      if (cleared.length) parts.push(`cleared ${cleared.join(', ')}`)
      return parts.join('; ')
    }
    case 'Scheduler Agent':
      return result.adjusted.length
        ? result.adjusted
            .map((a) => `${a.train} +${a.recovered} min recovered`)
            .join('; ')
        : 'no time left to recover'
    case 'Manager Agent':
      return result.called.length
        ? result.called.map((c) => `called about ${c.train}`).join('; ')
        : 'every passenger already has the current time'
    case 'Resource Agent':
      return result.alerts.length
        ? `${result.alerts.length} platform alert(s) raised`
        : 'no change in crowding'
    case 'Advisor Agent':
      return result.newlyLogged
        ? `${result.newlyLogged} new suggestion(s)`
        : 'nothing new to advise'
    default:
      return ''
  }
}

/**
 * Station Master Control Panel — what station staff see.
 *
 * Crowding down the left, the work in the middle, the agents' running log on
 * the right: the two things staff act on stay visible while they type.
 */
function StationMasterPanel() {
  // Gates the whole panel: station() is a manager-only endpoint, so there is
  // nothing to fetch until a manager has signed in.
  const [signedIn, setSignedIn] = useState(() => Boolean(getManagerToken()))

  const { data, loading, error, errorStatus, reload } = useApi(
    () => fetchStation(STATION_CODE),
    { enabled: signedIn },
  )

  const [cycle, setCycle] = useState(null)
  const [running, setRunning] = useState(false)
  const [cycleError, setCycleError] = useState(null)

  // Which inbound train's route is traced on the map. Null means none.
  const [selectedTrain, setSelectedTrain] = useState(null)

  /** A token that stopped working (expired, rotated by a login elsewhere). */
  function handleAuthFailure() {
    clearManagerToken()
    setSignedIn(false)
  }

  // A token that looked valid at mount can still be rejected on first fetch
  // — it may have been rotated by a login elsewhere. Same fix either way:
  // drop back to the sign-in screen rather than show a raw 401.
  useEffect(() => {
    if (errorStatus === 401) handleAuthFailure()
  }, [errorStatus])

  /** Shared by both entry points: run something, then refresh this page. */
  async function runAndRefresh(action) {
    setRunning(true)
    setCycleError(null)
    try {
      const outcome = await action()
      setCycle(outcome)
      // The agents have just changed the data this page is showing.
      await reload()
    } catch (err) {
      if (err.status === 401) {
        handleAuthFailure()
      } else {
        setCycleError(err.message)
      }
    } finally {
      setRunning(false)
    }
  }

  const handleRunAgents = () => runAndRefresh(runAgentCycle)
  const handleReportDelay = (input) => runAndRefresh(() => reportDelay(input))

  const heading = (title) => (
    <div className="page-header page-header-row">
      <div>
        <p className="page-eyebrow">Station Control</p>
        <h1 className="page-title">{title}</h1>
      </div>
    </div>
  )

  if (!signedIn) {
    return (
      <>
        {heading('Station Master Panel')}
        <ManagerLogin onSuccess={() => setSignedIn(true)} />
      </>
    )
  }

  if (loading) {
    return (
      <>
        {heading('Station Master Panel')}
        <Loading what="station data" />
      </>
    )
  }

  // On a 401 the effect above clears the token and flips signedIn back to
  // false on the next render; render nothing for this one frame rather than
  // flash the raw error message.
  if (errorStatus === 401) {
    return null
  }

  if (error) {
    return (
      <>
        {heading('Station Master Panel')}
        <ErrorMessage message={error} />
      </>
    )
  }

  const { station, platforms, arrivals, agentAlerts } = data

  const occupancyPercent = Math.round(
    (station.passengersOnSite / station.capacity) * 100,
  )
  const crowdedPlatforms = platforms.filter(
    (p) => crowdLevel(Math.round((p.occupancy / p.capacity) * 100)) !== 'clear',
  ).length
  const delayedArrivals = arrivals.filter((a) => a.status !== 'on-time').length

  // Kept as an id rather than the object itself, so a refresh that rebuilds
  // the array does not lose the selection.
  const selected = arrivals.find((a) => a.id === selectedTrain) ?? null

  const stats = [
    {
      label: 'Passengers on site',
      value: station.passengersOnSite.toLocaleString(),
      seed: station.passengersOnSite,
      tone: null,
    },
    {
      label: 'Station occupancy',
      value: `${occupancyPercent}%`,
      seed: occupancyPercent * 31,
      tone: occupancyPercent >= 90 ? 'late' : occupancyPercent >= 70 ? 'warn' : null,
    },
    {
      label: 'Platforms under pressure',
      value: crowdedPlatforms,
      seed: crowdedPlatforms * 137 + 11,
      tone: 'warn',
    },
    {
      label: 'Arrivals off schedule',
      value: delayedArrivals,
      seed: delayedArrivals * 211 + 29,
      tone: 'late',
    },
  ]

  return (
    <>
      <div className="page-header page-header-row">
        <div>
          <p className="page-eyebrow">Station Control</p>
          <h1 className="page-title">{station.name}</h1>
          <p className="page-subtitle">
            Live platform crowding, inbound trains and the actions RailBot's
            agents have already taken.
          </p>
        </div>

        <button
          type="button"
          className="run-button"
          onClick={handleRunAgents}
          disabled={running}
        >
          {running ? 'Agents running…' : 'Run agent cycle'}
        </button>
      </div>

      {cycleError && <ErrorMessage message={cycleError} />}

      {cycle && (
        <section className="cycle-report" aria-label="Latest agent cycle">
          <h2 className="cycle-title">
            Observe → Reason → Act cycle at {cycle.ranAt}
          </h2>

          {cycle.reported && (
            <p className="cycle-input">
              <span className="cycle-input-label">Reported</span>
              {cycle.reported.train} running {cycle.reported.minutes} minutes late
              {' — '}
              {cycle.reported.scheduledDeparture} becomes{' '}
              {cycle.reported.departureAfterDelay}
              {cycle.settledDeparture !== cycle.reported.departureAfterDelay && (
                <>
                  , settled at <strong>{cycle.settledDeparture}</strong> after
                  recovery
                </>
              )}
            </p>
          )}

          <ol className="cycle-steps">
            {cycle.results.map((result) => (
              <li key={result.agent}>
                <span className="cycle-agent">{result.agent}</span>
                <span className="cycle-outcome">{summarise(result)}</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      <div className="station-grid">
        <div className="col-left">
          <section className="panel">
            <h2 className="panel-title">Network Map</h2>
            <BangladeshMap
              route={selected?.route}
              label={
                selected
                  ? `${selected.train} #${selected.trainNo} · ${selected.from} to Dhaka`
                  : null
              }
            />
          </section>

          <section className="panel">
            <h2 className="panel-title">Platform Crowding</h2>
            <ul className="platform-list">
              {platforms.map((p) => (
                <li className="platform-row" key={p.id}>
                  <div className="platform-head">
                    <span className="platform-name">Platform {p.id}</span>
                    <span className="platform-count">
                      {p.occupancy} / {p.capacity}
                    </span>
                  </div>
                  <CapacityMeter occupancy={p.occupancy} capacity={p.capacity} />
                  <p className="platform-waiting">
                    {p.waitingFor
                      ? `Waiting for ${p.waitingFor}`
                      : 'No train assigned'}
                  </p>
                </li>
              ))}
            </ul>
          </section>
        </div>

        <div className="col-mid">
          <section className="panel">
            <h2 className="panel-title">Report a Delay</h2>
            <p className="form-hint">
              Enter what has happened. The agents decide what to do about it.
            </p>
            <DelayForm onSubmit={handleReportDelay} busy={running} />
          </section>

          <section className="stat-row" aria-label="Station summary">
            {stats.map((stat) => (
              <div className="stat-tile" key={stat.label}>
                <div className="stat-body">
                  <p
                    className={`stat-value ${stat.tone ? `stat-${stat.tone}` : ''}`}
                  >
                    {stat.value}
                  </p>
                  <p className="stat-label">{stat.label}</p>
                </div>
                <span className="stat-art">
                  <Sparkline seed={stat.seed} tone={stat.tone ?? 'neutral'} />
                </span>
              </div>
            ))}
          </section>

          <section className="panel">
            <h2 className="panel-title">Inbound Trains</h2>
            <div className="table-scroll">
              <table className="arrivals-table">
                <thead>
                  <tr>
                    <th>Train</th>
                    <th>From</th>
                    <th>Scheduled</th>
                    <th>Expected</th>
                    <th>Platform</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {arrivals.map((a) => (
                    <tr
                      key={a.id}
                      className={a.id === selectedTrain ? 'is-selected' : ''}
                      onClick={() =>
                        setSelectedTrain((current) =>
                          current === a.id ? null : a.id,
                        )
                      }
                      // Reachable and toggleable from the keyboard, not just
                      // by pointer.
                      tabIndex={0}
                      role="button"
                      aria-pressed={a.id === selectedTrain}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault()
                          setSelectedTrain((current) =>
                            current === a.id ? null : a.id,
                          )
                        }
                      }}
                    >
                      <td>
                        <span className="cell-train">{a.train}</span>
                        <span className="cell-no">#{a.trainNo}</span>
                      </td>
                      <td>{a.from}</td>
                      <td className="num">{a.scheduled}</td>
                      <td className="num">
                        {a.status === 'delayed' ? (
                          <strong className="time-new">{a.expected}</strong>
                        ) : (
                          a.expected
                        )}
                      </td>
                      <td className="num">{a.platform}</td>
                      <td>
                        <StatusBadge status={a.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="table-note">
              {selected
                ? `Tracing ${selected.train} from ${selected.from}. Select it again to clear.`
                : 'Select a train to trace its route on the map.'}
            </p>
          </section>
        </div>

        <div className="col-side">
          <section className="panel">
            <h2 className="panel-title">Agent Log</h2>
            <ul className="alert-list">
              {agentAlerts.map((alert) => (
                <li className={`alert-row alert-${alert.severity}`} key={alert.id}>
                  <span className="alert-dot" aria-hidden="true">
                    {initials(alert.agent)}
                  </span>
                  <div className="alert-main">
                    <div className="alert-head">
                      <span className="alert-agent">{alert.agent}</span>
                      <span className="alert-time">{alert.time}</span>
                    </div>
                    <p className="alert-message">{alert.message}</p>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        </div>
      </div>
    </>
  )
}

export default StationMasterPanel
