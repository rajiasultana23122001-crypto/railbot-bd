import { useEffect, useState } from 'react'

/**
 * Runs an API call once when the component mounts and reports its progress.
 *
 * Returns { data, loading, error } — the three states every screen that loads
 * from a server has to handle.
 *
 * @param {() => Promise<any>} loader function that performs the request
 */
export function useApi(loader) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    // If the component unmounts mid-request, skip the state update so React
    // is not asked to update a screen that is no longer on the page.
    let active = true

    setLoading(true)
    setError(null)

    loader()
      .then((result) => {
        if (active) setData(result)
      })
      .catch((err) => {
        if (active) setError(err.message)
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return { data, loading, error }
}
