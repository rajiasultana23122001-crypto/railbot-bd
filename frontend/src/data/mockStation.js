/**
 * Sample station state for the Station Master Panel.
 *
 * Like the passenger data, this mirrors the shape the Flask API will return so
 * the components survive the switch to real data unchanged.
 */

export const station = {
  name: 'Dhaka (Kamalapur)',
  code: 'DHKA',
  passengersOnSite: 3180,
  capacity: 3500,
  updatedAt: '14:20',
}

/** Per-platform crowding. occupancy and capacity are passenger counts. */
export const platforms = [
  { id: '1', occupancy: 305, capacity: 600, waitingFor: 'Mohanagar Provati' },
  { id: '2', occupancy: 545, capacity: 600, waitingFor: 'Parabat Express' },
  { id: '3', occupancy: 180, capacity: 550, waitingFor: 'Ekota Express' },
  { id: '4', occupancy: 470, capacity: 600, waitingFor: 'Subarna Express' },
  { id: '5', occupancy: 95, capacity: 500, waitingFor: null },
  { id: '6', occupancy: 585, capacity: 650, waitingFor: 'Padma Express' },
]

/** Trains due into this station over the next couple of hours. */
export const arrivals = [
  {
    id: 'A-704',
    train: 'Mohanagar Provati',
    trainNo: '704',
    from: 'Chattogram',
    scheduled: '14:35',
    expected: '14:35',
    platform: '1',
    status: 'on-time',
  },
  {
    id: 'A-710',
    train: 'Parabat Express',
    trainNo: '710',
    from: 'Sylhet',
    scheduled: '14:50',
    expected: '15:25',
    platform: '2',
    status: 'delayed',
  },
  {
    id: 'A-766',
    train: 'Ekota Express',
    trainNo: '766',
    from: 'Dinajpur',
    scheduled: '15:10',
    expected: '15:10',
    platform: '3',
    status: 'on-time',
  },
  {
    id: 'A-760',
    train: 'Padma Express',
    trainNo: '760',
    from: 'Rajshahi',
    scheduled: '15:40',
    expected: '15:40',
    platform: '6',
    status: 'at-risk',
  },
  {
    id: 'A-722',
    train: 'Chitra Express',
    trainNo: '764',
    from: 'Khulna',
    scheduled: '16:05',
    expected: '16:05',
    platform: '4',
    status: 'on-time',
  },
]

/**
 * What the agents have done, newest first.
 * severity drives the colour of the marker beside each entry.
 */
export const agentAlerts = [
  {
    id: 'AL-31',
    time: '14:18',
    agent: 'Resource Agent',
    severity: 'high',
    message:
      'Platform 6 is at 90% capacity with Padma Express still inbound. Open Waiting Room B and assign two crowd-control staff.',
  },
  {
    id: 'AL-30',
    time: '14:12',
    agent: 'Scheduler Agent',
    severity: 'medium',
    message:
      'Parabat Express delayed 35 min. Halts at Bhairab Bazar and Shaistaganj shortened; 12 minutes recovered.',
  },
  {
    id: 'AL-29',
    time: '14:05',
    agent: 'Manager Agent',
    severity: 'info',
    message: 'Delay calls placed to 214 passengers booked on Parabat Express.',
  },
  {
    id: 'AL-28',
    time: '13:52',
    agent: 'Risk Agent',
    severity: 'medium',
    message:
      'Heavy rainfall forecast near Ishwardi. Padma Express flagged with a 20-25 min delay risk.',
  },
]
