/**
 * Available seats for one train/class/date, as clickable chips.
 *
 * Picking a specific seat is optional in the API (POST /api/bookings books
 * whatever is free if no seatNumbers are sent) — this is what lets a
 * passenger do it anyway, the same as the real site's seat map, just as a
 * flat list rather than a coach diagram.
 */
function SeatPicker({ seats, count, selected, onToggle }) {
  return (
    <div className="seat-picker-grid" role="group" aria-label="Available seats">
      {seats.map((seat) => {
        const isSelected = selected.includes(seat)
        const atLimit = !isSelected && selected.length >= count
        return (
          <button
            type="button"
            key={seat}
            className={`seat-chip-btn ${isSelected ? 'is-selected' : ''}`}
            onClick={() => onToggle(seat)}
            disabled={atLimit}
            aria-pressed={isSelected}
          >
            {seat}
          </button>
        )
      })}
    </div>
  )
}

export default SeatPicker
