import { OUTLINE, VIEW } from '../data/bangladesh'
import {
  CORRIDORS,
  LABELLED,
  SHORT_NAME,
  STATIONS,
  pathFor,
  project,
} from '../data/stations'

/**
 * Bangladesh with the intercity network drawn on it.
 *
 * Station positions are real coordinates projected onto the viewBox, so the
 * lines land where they belong on the country. The backend sends a train's
 * route as a list of station names and this traces it.
 */
function BangladeshMap({ route, label }) {
  const active = pathFor(route)
  const onRoute = new Set(route ?? [])

  return (
    <figure className="bd-map">
      <svg
        viewBox={`0 0 ${VIEW.width} ${VIEW.height}`}
        role="img"
        aria-labelledby="mapTitle mapDesc"
      >
        <title id="mapTitle">Bangladesh Railway intercity network</title>
        <desc id="mapDesc">
          {active
            ? `The route ${label} is highlighted across the network.`
            : 'The intercity network, with no route selected.'}
        </desc>

        {/* The country itself, from the published boundary */}
        <path className="bd-land" d={OUTLINE} fillRule="evenodd" />

        {/* The whole network, faint */}
        {CORRIDORS.map((corridor, i) => {
          const d = pathFor(corridor)
          return d ? <path key={i} className="bd-route" d={d} /> : null
        })}

        {/* The selected service, on top */}
        {active && <path className="bd-route is-active" d={active} />}

        {/* Stations */}
        {Object.keys(STATIONS).map((name) => {
          const p = project(name)
          if (!p) return null
          const isOn = onRoute.has(name)
          const isNamed = LABELLED.has(name) || isOn
          const text = SHORT_NAME[name] ?? name
          return (
            <g key={name} className={`bd-city ${isOn ? 'is-active' : ''}`}>
              <circle cx={p.x} cy={p.y} r={isOn ? 5 : 3.2} />
              {isNamed && (
                <text
                  x={p.x}
                  y={p.y - 9}
                  textAnchor={p.x > 300 ? 'end' : p.x < 80 ? 'start' : 'middle'}
                >
                  {text}
                </text>
              )}
            </g>
          )
        })}
      </svg>

      <figcaption className="bd-caption">
        {active ? (
          <>
            <span className="bd-caption-tag">Route</span>
            {label}
          </>
        ) : (
          'Select an inbound train to trace its route.'
        )}
      </figcaption>
    </figure>
  )
}

export default BangladeshMap
