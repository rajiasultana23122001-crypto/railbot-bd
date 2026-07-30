import CapacityMeter, { crowdLevel } from '../components/CapacityMeter'
import StatusBadge from '../components/StatusBadge'
import { station, platforms, arrivals, agentAlerts } from '../data/mockStation'
import './Dashboard.css'

/**
 * Station Master Control Panel — what station staff see.
 *
 * Laid out summary first, then the two things staff act on: which platforms are
 * filling up, and what the agents have already decided.
 */
function StationMasterPanel() {
  const occupancyPercent = Math.round(
    (station.passengersOnSite / station.capacity) * 100,
  )
  const crowdedPlatforms = platforms.filter(
    (p) => crowdLevel(Math.round((p.occupancy / p.capacity) * 100)) !== 'clear',
  ).length
  const delayedArrivals = arrivals.filter((a) => a.status !== 'on-time').length

  const stats = [
    { label: 'Passengers on site', value: station.passengersOnSite.toLocaleString() },
    {
      label: 'Station occupancy',
      value: `${occupancyPercent}%`,
      tone: occupancyPercent >= 90 ? 'late' : occupancyPercent >= 70 ? 'warn' : null,
    },
    { label: 'Platforms under pressure', value: crowdedPlatforms, tone: 'warn' },
    { label: 'Arrivals off schedule', value: delayedArrivals, tone: 'late' },
  ]

  return (
    <>
      <div className="page-header">
        <p className="page-eyebrow">Station Control</p>
        <h1 className="page-title">{station.name}</h1>
        <p className="page-subtitle">
          Live platform crowding, inbound trains and the actions RailBot's agents
          have already taken. Updated at {station.updatedAt}.
        </p>
      </div>

      <section className="stat-row" aria-label="Station summary">
        {stats.map((stat) => (
          <div className="stat-tile" key={stat.label}>
            <p className={`stat-value ${stat.tone ? `stat-${stat.tone}` : ''}`}>
              {stat.value}
            </p>
            <p className="stat-label">{stat.label}</p>
          </div>
        ))}
      </section>

      <div className="panel-grid">
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
                  {p.waitingFor ? `Waiting for ${p.waitingFor}` : 'No train assigned'}
                </p>
              </li>
            ))}
          </ul>
        </section>

        <section className="panel">
          <h2 className="panel-title">Agent Activity</h2>
          <ul className="alert-list">
            {agentAlerts.map((alert) => (
              <li className={`alert-row alert-${alert.severity}`} key={alert.id}>
                <div className="alert-head">
                  <span className="alert-agent">{alert.agent}</span>
                  <span className="alert-time">{alert.time}</span>
                </div>
                <p className="alert-message">{alert.message}</p>
              </li>
            ))}
          </ul>
        </section>
      </div>

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
                <tr key={a.id}>
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
      </section>
    </>
  )
}

export default StationMasterPanel
