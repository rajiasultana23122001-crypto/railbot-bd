/**
 * Returns the crowding level for a fill percentage.
 * Kept as a plain function so the Resource Agent's thresholds live in one place.
 */
export function crowdLevel(percent) {
  if (percent >= 90) return 'critical'
  if (percent >= 70) return 'busy'
  return 'clear'
}

/**
 * Horizontal bar showing how full a platform is.
 *
 * The bar carries a level class as well as its width, so the state is readable
 * without relying on colour alone — the percentage is printed beside it.
 */
function CapacityMeter({ occupancy, capacity }) {
  const percent = Math.round((occupancy / capacity) * 100)
  const level = crowdLevel(percent)

  return (
    <div className="meter">
      <div
        className="meter-track"
        role="meter"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`${percent} percent full`}
      >
        {/* Cap the visual fill at 100% even if a platform is over capacity. */}
        <div
          className={`meter-fill meter-${level}`}
          style={{ width: `${Math.min(percent, 100)}%` }}
        />
      </div>
      <span className={`meter-value meter-text-${level}`}>{percent}%</span>
    </div>
  )
}

export default CapacityMeter
