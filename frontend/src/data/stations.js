/**
 * Where the stations are, and how the network joins them up.
 *
 * Coordinates are real, so the map is a projection of the country rather than
 * a drawing. The backend sends a train's route as a list of these names; this
 * file is what turns that list into a line on screen.
 */

import { PROJECTION, VIEW } from './bangladesh'

export { VIEW }

// latitude, longitude
export const STATIONS = {
  'Dhaka (Kamalapur)': [23.7328, 90.4265],
  'Biman Bandar': [23.8513, 90.4045],
  'Bhairab Bazar': [24.05, 90.98],
  Brahmanbaria: [23.957, 91.112],
  Akhaura: [23.87, 91.21],
  Cumilla: [23.46, 91.18],
  Feni: [23.02, 91.4],
  Chattogram: [22.34, 91.83],
  // The station sits east of the town centre, inland of the beach.
  "Cox's Bazar": [21.4419, 92.0105],
  Srimangal: [24.31, 91.73],
  Sylhet: [24.899, 91.87],
  Kishoreganj: [24.44, 90.78],
  Mymensingh: [24.75, 90.4],
  Mohanganj: [24.85, 90.98],
  Jamalpur: [24.92, 89.94],
  Tangail: [24.25, 89.92],
  Ishwardi: [24.13, 89.07],
  Natore: [24.41, 88.99],
  Rajshahi: [24.37, 88.6],
  Santahar: [24.79, 88.99],
  Bogura: [24.85, 89.37],
  Parbatipur: [25.66, 88.92],
  Dinajpur: [25.63, 88.64],
  Panchagarh: [26.33, 88.56],
  Chilahati: [26.1, 88.95],
  Rangpur: [25.75, 89.25],
  Lalmonirhat: [25.92, 89.45],
  Kurigram: [25.81, 89.64],
  Kushtia: [23.9, 89.12],
  Rajbari: [23.76, 89.65],
  Faridpur: [23.6, 89.83],
  Jashore: [23.17, 89.21],
  Benapole: [23.04, 88.94],
  Khulna: [22.82, 89.56],
  Chandpur: [23.23, 90.65],
  Noakhali: [22.87, 91.1],
}

/** The corridors drawn as the faint background network. */
export const CORRIDORS = [
  ['Dhaka (Kamalapur)', 'Biman Bandar', 'Bhairab Bazar', 'Brahmanbaria', 'Akhaura', 'Cumilla', 'Feni', 'Chattogram'],
  ['Chattogram', "Cox's Bazar"],
  ['Akhaura', 'Srimangal', 'Sylhet'],
  ['Bhairab Bazar', 'Kishoreganj'],
  ['Biman Bandar', 'Mymensingh', 'Jamalpur'],
  ['Mymensingh', 'Mohanganj'],
  ['Dhaka (Kamalapur)', 'Tangail', 'Ishwardi', 'Natore', 'Rajshahi'],
  ['Natore', 'Santahar', 'Bogura', 'Parbatipur', 'Dinajpur', 'Panchagarh'],
  ['Parbatipur', 'Chilahati'],
  ['Parbatipur', 'Rangpur', 'Lalmonirhat', 'Kurigram'],
  ['Ishwardi', 'Kushtia', 'Jashore', 'Khulna'],
  ['Jashore', 'Benapole'],
  ['Dhaka (Kamalapur)', 'Rajbari', 'Faridpur'],
  ['Cumilla', 'Chandpur'],
  ['Feni', 'Noakhali'],
]

/** Stations big enough to name on the map without crowding it. */
export const LABELLED = new Set([
  'Dhaka (Kamalapur)',
  'Chattogram',
  "Cox's Bazar",
  'Sylhet',
  'Rajshahi',
  'Khulna',
  'Panchagarh',
  'Rangpur',
  'Mymensingh',
  'Jashore',
  'Ishwardi',
  'Cumilla',
])

/** Shorter names for the map, where space is tight. */
export const SHORT_NAME = {
  'Dhaka (Kamalapur)': 'Dhaka',
  'Biman Bandar': 'Biman Bandar',
}

/**
 * Longitude and latitude onto viewBox coordinates.
 *
 * Uses the constants the country outline was generated with, so a station
 * always lands on the part of the map it belongs to.
 */
export function project(name) {
  const point = STATIONS[name]
  if (!point) return null
  const [lat, lon] = point
  const { kx, scale, minX, minY, pad } = PROJECTION
  return {
    x: (lon * kx - minX) * scale + pad,
    y: (-lat - minY) * scale + pad,
  }
}

/** Turn a list of station names into an SVG path, skipping any it cannot place. */
export function pathFor(route) {
  if (!route || route.length < 2) return null
  const points = route.map(project).filter(Boolean)
  if (points.length < 2) return null
  return points.map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
}
