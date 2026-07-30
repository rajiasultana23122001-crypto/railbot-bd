/** Shown while a dashboard is waiting for the API. */
export function Loading({ what }) {
  return (
    <div className="feedback" role="status">
      Loading {what}…
    </div>
  )
}

/**
 * Shown when the API could not be read.
 * The message names the actual problem so the fix is obvious during a demo.
 */
export function ErrorMessage({ message }) {
  return (
    <div className="feedback feedback-error" role="alert">
      <strong>Could not load data</strong>
      <span>{message}</span>
    </div>
  )
}
