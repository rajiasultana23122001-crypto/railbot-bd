/**
 * A small trend line drawn beside a station figure.
 *
 * The shape is derived from the value itself rather than random, so the same
 * reading always draws the same line and the panel does not appear to jitter
 * between refreshes.
 */
function buildSeries(seed, points = 12) {
  const values = []
  let x = seed
  for (let i = 0; i < points; i += 1) {
    // A small deterministic shuffle; enough movement to read as a trend.
    x = (x * 9301 + 49297) % 233280
    values.push(x / 233280)
  }
  return values
}

function Sparkline({ seed = 42, tone = 'neutral', width = 62, height = 22 }) {
  const values = buildSeries(Math.round(seed) || 7)
  const max = Math.max(...values)
  const min = Math.min(...values)
  const span = max - min || 1

  const step = width / (values.length - 1)
  const points = values.map((v, i) => {
    const y = height - 2 - ((v - min) / span) * (height - 5)
    return `${(i * step).toFixed(1)},${y.toFixed(1)}`
  })

  const line = `M${points.join(' L')}`
  const area = `${line} L${width},${height} L0,${height} Z`

  return (
    <svg
      className={`sparkline spark-${tone}`}
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      aria-hidden="true"
    >
      <path className="spark-area" d={area} />
      <path className="spark-line" d={line} />
    </svg>
  )
}

export default Sparkline
