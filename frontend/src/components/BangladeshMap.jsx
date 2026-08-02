import {
  CORRIDORS,
  LABELLED,
  SHORT_NAME,
  STATIONS,
  VIEW,
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

        {/* Country outline */}
        <path
          className="bd-land"
          d="M62,74 L92,56 L122,74 L152,60 L178,80 L202,66 L234,86 L252,70 L270,98
             L302,88 L324,112 L346,130 L353,160 L338,182 L351,202 L344,232 L353,264
             L340,302 L349,332 L336,370 L345,402 L330,442 L339,482 L326,520 L312,548
             L280,556 L250,540 L232,510 L205,522 L180,506 L160,522 L140,500 L120,514
             L98,488 L109,456 L90,430 L106,400 L88,372 L97,340 L78,310 L87,280
             L66,250 L75,214 L58,186 L67,150 L50,120 Z"
        />

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
