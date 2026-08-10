/**
 * Side elevation of an intercity train, for the top of the Passenger
 * Dashboard.
 *
 * Drawn rather than photographed, for three reasons: it costs no network
 * request, it stays sharp at any width, and it can be coloured from the
 * same CSS tokens as everything else — so it follows the light/dark
 * toggle instead of being a picture that only suits one of them.
 *
 * Decorative: aria-hidden, and it carries no information the page does not
 * already state in text.
 */
function TrainArt() {
  // One coach, drawn twice. Keeping the geometry in a function is what
  // makes the two identical rather than nearly identical.
  const coach = (x, label) => {
    const windows = [0, 1, 2, 3, 4, 5, 6].map((i) => x + 28 + i * 38)
    return (
      <g key={x}>
        <rect className="ta-body" x={x} y="56" width="310" height="86" rx="4" />

        {windows.map((wx) => (
          <rect key={wx} className="ta-window" x={wx} y="72" width="26" height="28" rx="2" />
        ))}

        {/* Door seams, near each end. */}
        <path className="ta-seam" d={`M${x + 16} 56v86M${x + 294} 56v86`} />

        <rect className="ta-stripe" x={x + 6} y="126" width="298" height="10" />
        <rect className="ta-underframe" x={x + 10} y="142" width="290" height="6" />

        {label && (
          <text className="ta-label" x={x + 155} y="118" textAnchor="middle">
            BANGLADESH RAILWAY
          </text>
        )}

        {/* Two bogies, two wheels each. */}
        {[x + 70, x + 240].map((bx) =>
          [bx - 17, bx + 17].map((wx) => (
            <g key={wx}>
              <circle className="ta-wheel" cx={wx} cy="156" r="12" />
              <circle className="ta-hub" cx={wx} cy="156" r="4" />
            </g>
          )),
        )}
      </g>
    )
  }

  return (
    <svg
      className="ta"
      /* Cropped to the drawing rather than starting at 0: nothing sits above
         y=56, and the empty strip left a band a third taller than it needed
         to be. */
      viewBox="0 36 1200 158"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      {/* Speed lines, behind and to the left — the train is moving right. */}
      <g className="ta-speed">
        <path d="M18 84h54M4 104h56M24 124h54" />
      </g>

      {coach(90, true)}
      {coach(415, false)}

      {/* Couplings. Drawn at the underframe, thick enough to read as a
          connection rather than as two stray marks near the wheels. */}
      <path className="ta-coupling" d="M400 145h15M725 145h15" />

      {/* Locomotive: a straight body to x=1000, then a raked nose. */}
      <path className="ta-body" d="M740 56h260l90 48v38H740z" />

      {[766, 804, 842].map((x) => (
        <rect key={x} className="ta-window" x={x} y="72" width="26" height="28" rx="2" />
      ))}

      {/* Cab windscreen, following the rake of the nose. */}
      <path className="ta-window" d="M950 72h65l43 28H950z" />

      <path className="ta-seam" d="M900 56v86" />
      <rect className="ta-stripe" x="746" y="126" width="338" height="10" />
      <rect className="ta-underframe" x="750" y="142" width="330" height="6" />

      {[820, 1010].map((bx) =>
        [bx - 17, bx + 17].map((wx) => (
          <g key={wx}>
            <circle className="ta-wheel" cx={wx} cy="156" r="12" />
            <circle className="ta-hub" cx={wx} cy="156" r="4" />
          </g>
        )),
      )}

      {/* Headlamp, and the light it throws ahead. */}
      <circle className="ta-lamp" cx="1074" cy="117" r="5" />
      <path className="ta-beam" d="M1086 112h26M1086 117h34M1086 122h26" />

      {/* Track: two rails and the sleepers under them. */}
      <path className="ta-rail" d="M0 168h1200" />
      <path className="ta-rail-thin" d="M0 174h1200" />
      <g className="ta-sleeper">
        {Array.from({ length: 43 }, (_, i) => (
          <path key={i} d={`M${8 + i * 28} 176v11`} />
        ))}
      </g>
    </svg>
  )
}

export default TrainArt
