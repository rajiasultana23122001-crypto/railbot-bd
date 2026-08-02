/**
 * Bangladesh with the railway routes RailBot watches.
 *
 * City positions come from real coordinates projected onto the viewBox, so the
 * network sits where it should on the country rather than being placed by eye.
 * Selecting a train lights its route.
 */

// Longitude 88.0-92.7 and latitude 20.6-26.7 mapped onto a 400 x 560 box.
const CITIES = {
  Dhaka: { x: 205, y: 274, label: 'Dhaka' },
  Chattogram: { x: 322, y: 398, label: 'Chattogram' },
  Sylhet: { x: 329, y: 165, label: 'Sylhet' },
  Rajshahi: { x: 51, y: 214, label: 'Rajshahi' },
  Dinajpur: { x: 54, y: 98, label: 'Dinajpur' },
  Khulna: { x: 133, y: 356, label: 'Khulna' },
}

/**
 * Each route bends through the junctions the line actually passes, so a
 * highlighted route reads as a railway rather than a ruler line.
 */
const ROUTES = {
  Chattogram: 'M205,274 L232,300 L258,330 L288,362 L322,398',
  Sylhet: 'M205,274 L232,248 L258,222 L292,192 L329,165',
  Rajshahi: 'M205,274 L172,262 L136,244 L94,226 L51,214',
  Dinajpur: 'M205,274 L170,254 L132,214 L96,158 L54,98',
  Khulna: 'M205,274 L188,300 L172,322 L152,340 L133,356',
}

/** "Dhaka (Kamalapur)" and "Dhaka" are the same place to this map. */
export function cityKey(name) {
  if (!name) return null
  const plain = name.replace(/\s*\(.*?\)\s*/g, '').trim()
  return CITIES[plain] ? plain : null
}

function BangladeshMap({ activeCity, activeLabel }) {
  const active = activeCity && ROUTES[activeCity] ? activeCity : null

  return (
    <figure className="bd-map">
      <svg viewBox="0 0 400 560" role="img" aria-labelledby="mapTitle mapDesc">
        <title id="mapTitle">Railway routes across Bangladesh</title>
        <desc id="mapDesc">
          {active
            ? `The route between Dhaka and ${CITIES[active].label} is highlighted.`
            : 'Routes from Dhaka to Chattogram, Sylhet, Rajshahi, Dinajpur and Khulna.'}
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

        {/* Every route, drawn faint */}
        {Object.entries(ROUTES).map(([city, d]) => (
          <path
            key={city}
            className={`bd-route ${active === city ? 'is-active' : ''}`}
            d={d}
          />
        ))}

        {/* Stations */}
        {Object.entries(CITIES).map(([key, city]) => {
          const isEnd = key === active || (active && key === 'Dhaka')
          return (
            <g key={key} className={`bd-city ${isEnd ? 'is-active' : ''}`}>
              <circle cx={city.x} cy={city.y} r={key === 'Dhaka' ? 6 : 5} />
              <text
                x={city.x}
                y={city.y - 12}
                textAnchor={city.x > 300 ? 'end' : city.x < 90 ? 'start' : 'middle'}
              >
                {city.label}
              </text>
            </g>
          )
        })}
      </svg>

      <figcaption className="bd-caption">
        {active ? (
          <>
            <span className="bd-caption-tag">Route</span>
            {activeLabel ?? `Dhaka — ${CITIES[active].label}`}
          </>
        ) : (
          'Select an inbound train to trace its route.'
        )}
      </figcaption>
    </figure>
  )
}

export default BangladeshMap
