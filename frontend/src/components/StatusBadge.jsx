/** Human-readable label for each status the agents can assign. */
const LABELS = {
  'on-time': 'On Time',
  'at-risk': 'Delay Risk',
  delayed: 'Delayed',
}

/**
 * Coloured pill showing a journey's current status.
 * The colour is carried by a modifier class so status reads at a glance,
 * not only from the text.
 */
function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{LABELS[status] ?? status}</span>
}

export default StatusBadge
