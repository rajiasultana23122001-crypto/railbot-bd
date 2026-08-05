import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Runs an API call when the component mounts and reports its progress.
 *
 * Returns { data, loading, error, errorStatus, reload } — the three states
 * every server-backed screen has to handle, plus a way to fetch again after
 * something has changed on the server. errorStatus carries the HTTP status
 * of a failed request (e.g. 401), so a caller can tell "not signed in" apart
 * from any other failure without parsing the message text.
 *
 * Pass `{ enabled: false }` to skip fetching entirely — for a screen that
 * needs to gate on something (a sign-in) before it has anything to load.
 *
 * @param {() => Promise<any>} loader function that performs the request
 * @param {{ enabled?: boolean }} [options]
 */
export function useApi(loader, { enabled = true } = {}) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(enabled)
  const [error, setError] = useState(null)
  const [errorStatus, setErrorStatus] = useState(null)

  // Held in a ref so callers can pass an inline arrow function without it
  // re-triggering the request on every render.
  const loaderRef = useRef(loader)
  loaderRef.current = loader

  // Tracks whether the component is still on screen, so a request that
  // finishes after it unmounts does not try to update it.
  const activeRef = useRef(true)

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    setErrorStatus(null)

    return loaderRef
      .current()
      .then((result) => {
        if (activeRef.current) setData(result)
      })
      .catch((err) => {
        if (!activeRef.current) return
        setError(err.message)
        setErrorStatus(err.status ?? null)
      })
      .finally(() => {
        if (activeRef.current) setLoading(false)
      })
  }, [])

  useEffect(() => {
    activeRef.current = true
    if (enabled) load()
    else setLoading(false)

    return () => {
      activeRef.current = false
    }
  }, [load, enabled])

  return { data, loading, error, errorStatus, reload: load }
}
