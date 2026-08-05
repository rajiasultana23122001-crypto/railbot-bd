/** Fixed bottom-left "network online" indicator, shown on every page. */
function NetworkStatus() {
  return (
    <div className="network-status" role="status">
      <span className="network-status-dot pulse-dot" aria-hidden="true" />
      Network Online
    </div>
  )
}

export default NetworkStatus
