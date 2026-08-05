import { useEffect, useState } from 'react'

import { STATIONS } from '../data/stations'
import { fetchStation, fetchTrainInfo } from './client'

const STATION_COUNT = Object.keys(STATIONS).length

/** How often the top bar's figures refresh themselves, in milliseconds. */
const REFRESH_MS = 30000

/**
 * Network-wide figures for the top bar: how many trains run, how many
 * stations they call at, and what fraction of Dhaka's inbound board is
 * currently on time.
 *
 * Real numbers, not decoration: the train and station counts come straight
 * from the same data the rest of the app reads, and the on-time figure is
 * the Dhaka arrivals board the Station Master Panel already shows. Failures
 * are swallowed — the top bar should never be the thing that breaks a page —
 * so a stat just holds its last good value (or null) until the next refresh.
 */
export function useLiveStats() {
  const [trainCount, setTrainCount] = useState(null)
  const [onTimePercent, setOnTimePercent] = useState(null)

  useEffect(() => {
    let active = true

    async function refresh() {
      try {
        const trains = await fetchTrainInfo()
        if (active) setTrainCount(trains.trains.length)
      } catch {
        // keep the last known value
      }

      try {
        const station = await fetchStation('DHKA')
        if (active && station.arrivals.length) {
          const onTime = station.arrivals.filter(
            (a) => a.status === 'on-time',
          ).length
          setOnTimePercent(Math.round((onTime / station.arrivals.length) * 100))
        }
      } catch {
        // keep the last known value
      }
    }

    refresh()
    const timer = setInterval(refresh, REFRESH_MS)
    return () => {
      active = false
      clearInterval(timer)
    }
  }, [])

  return {
    stationCount: STATION_COUNT,
    trainCount,
    onTimePercent,
  }
}
