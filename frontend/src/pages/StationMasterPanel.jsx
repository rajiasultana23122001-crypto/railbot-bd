/**
 * Station Master Control Panel — what station staff see.
 *
 * Station capacity, incoming trains and agent alerts arrive in a later step.
 */
function StationMasterPanel() {
  return (
    <>
      <div className="page-header">
        <p className="page-eyebrow">Station Control</p>
        <h1 className="page-title">Station Master Panel</h1>
        <p className="page-subtitle">
          Monitor platform crowding, incoming trains and the alerts raised by
          the Resource Agent.
        </p>
      </div>

      <div className="placeholder">Station overview is coming in a later step.</div>
    </>
  )
}

export default StationMasterPanel
