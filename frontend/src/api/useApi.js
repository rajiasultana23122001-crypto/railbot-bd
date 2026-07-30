import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Runs an API call when the component mounts and reports its progress.
 *
 * Returns { data, loading, error, reload } — the three states every
 * server-backed screen has to handle, plus a way to fetch again after
 * something has changed on the server.
 *
 * @param {() => Promise<any>} loader function that performs the request
 */
export function useApi(loader) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

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

    return loaderRef
      .current()
      .then((result) => {
        if (activeRef.current) setData(result)
      })
      .catch((err) => {
        if (activeRef.current) setError(err.message)
      })
      .finally(() => {
        if (activeRef.current) setLoading(false)
      })
  }, [])

  useEffect(() => {
    activeRef.current = true
    load()

    return () => {
      activeRef.current = false
    }
  }, [load])

  return { data, loading, error, reload: load }
}
