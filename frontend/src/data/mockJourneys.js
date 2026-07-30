/**
 * Sample passenger journeys.
 *
 * This stands in for the Flask API while the frontend is being built. Once the
 * backend exists, the dashboard will fetch the same shape from /api/journeys
 * and nothing in the components has to change.
 *
 * status is one of: 'on-time' | 'at-risk' | 'delayed'
 * agentNote explains, in the passenger's words, what RailBot already did.
 */
export const journeys = [
  {
    id: 'BR-702',
    train: 'Subarna Express',
    trainNo: '702',
    from: 'Dhaka (Kamalapur)',
    to: 'Chattogram',
    date: '1 Aug 2026',
    scheduledDeparture: '07:00',
    expectedDeparture: '07:00',
    platform: '4',
    coach: 'SNIGDHA / C1-24',
    status: 'on-time',
    delayMinutes: 0,
    agentNote: null,
  },
  {
    id: 'BR-709',
    train: 'Parabat Express',
    trainNo: '709',
    from: 'Dhaka (Kamalapur)',
    to: 'Sylhet',
    date: '1 Aug 2026',
    scheduledDeparture: '18:45',
    expectedDeparture: '19:20',
    platform: '2',
    coach: 'SHOVAN / D3-11',
    status: 'delayed',
    delayMinutes: 35,
    agentNote:
      'Manager Agent called you at 17:52 with the new departure time. Scheduler Agent trimmed halts at Bhairab Bazar and Shaistaganj to recover 12 minutes.',
  },
  {
    id: 'BR-759',
    train: 'Padma Express',
    trainNo: '759',
    from: 'Dhaka (Kamalapur)',
    to: 'Rajshahi',
    date: '2 Aug 2026',
    scheduledDeparture: '23:00',
    expectedDeparture: '23:00',
    platform: '6',
    coach: 'AC_S / B2-07',
    status: 'at-risk',
    delayMinutes: 0,
    agentNote:
      'Risk Agent predicts a 20-25 minute delay from heavy rainfall forecast near Ishwardi. You will be called if the delay is confirmed.',
  },
  {
    id: 'BR-765',
    train: 'Ekota Express',
    trainNo: '765',
    from: 'Dhaka (Kamalapur)',
    to: 'Dinajpur',
    date: '3 Aug 2026',
    scheduledDeparture: '10:10',
    expectedDeparture: '10:10',
    platform: '3',
    coach: 'SHOVAN / F1-45',
    status: 'on-time',
    delayMinutes: 0,
    agentNote: null,
  },
]

/** Alerts the Manager Agent has already delivered to this passenger. */
export const alertsReceived = 2
