# RailBot BD — API reference

Every field the JSON actually carries, every status code an endpoint can
answer with, and what each refusal means. The README's API table says which
endpoints exist and who may call them; this is the level below that, for
anyone writing a client against them.

Base URL in development: `http://localhost:8000`. All paths below are
relative to it. Every response is JSON, errors included, and an error is
always a single `error` key holding a sentence meant to be shown to the
person who caused it:

```json
{ "error": "Only 1 SHOVAN seat(s) left." }
```

## Authentication

Send the token from `POST /api/auth/login` on every request except
`/api/health` and the auth endpoints themselves:

```
Authorization: Bearer <token>
```

`401` means no token, or one that is not recognised. `403` means the token
is valid but belongs to the other role — the passenger and authority APIs
are separate, and a passenger token never reads an operator's board.

Tokens come from `rest_framework.authtoken` and are rotated on every
successful login, so signing in again invalidates the previous token.

### POST /api/auth/passenger/signup

```json
{ "phone_number": "+8801700000000", "nid_number": "1010101010", "password": "secret123" }
```

`201` → `{ "message": "OTP sent. Confirm it to activate the account.", "phoneNumber": "+8801700000000" }`

The account exists at this point but cannot log in until the OTP is
confirmed.

| Status | When |
|---|---|
| `400` | Missing phone number or password, or an NID that is not 10 or 17 digits |
| `409` | That phone number already has an account, or that NID is registered |

### POST /api/auth/passenger/verify-signup

```json
{ "phone_number": "+8801700000000", "code": "482913" }
```

`200` → `{ "message": "Phone verified. You can now sign in." }`

| Status | When |
|---|---|
| `400` | The code is wrong or has expired |
| `404` | No signup is in progress for that number |

### POST /api/auth/authority/signup

```json
{ "phone_number": "+8801900000000", "authority_id": "BR-AUTH-1001", "password": "secret123" }
```

`201` → `{ "message": "Account created. You can now sign in." }`

No OTP step — the Authority ID is itself the proof of authorisation, so the
account is active immediately.

| Status | When |
|---|---|
| `400` | Missing field, or an Authority ID that was never issued |
| `409` | That phone number has an account, or that ID is already claimed |

### POST /api/auth/login

```json
{ "phone_number": "+8801700000000", "password": "railbot123" }
```

`200` → `{ "token": "9c1f...", "role": "passenger", "phoneNumber": "+8801700000000" }`

`role` is `passenger` or `authority`; the client reads it rather than asking
which kind of account this is.

| Status | When |
|---|---|
| `401` | Wrong password *or* unknown phone number — deliberately the same message, so login cannot be used to discover which numbers have accounts |
| `403` | The phone number has not been OTP-verified yet |

## Service

### GET /api/health

Public. The only endpoint that needs no token.

```json
{
  "status": "ok",
  "service": "railbot-bd",
  "database": "ok",
  "riskModelTrained": true
}
```

`503` with `"status": "degraded"` and `"database": "unreachable"` when the
database cannot be reached — an uptime probe should treat that as down.

`riskModelTrained` is `false` until `python ml/train_model.py` has been run.
That is not a `503`: booking, journeys and the timetable all work without
the model, but `POST /api/delays` and `POST /api/agents/run` answer `503`
while it is missing.

## Passenger endpoints

### GET /api/journeys

The signed-in passenger's own bookings — scoped to the account, not merely
to the role (see "Who sees which bookings" in the README).

```json
{
  "journeys": [
    {
      "id": "BR-12",
      "bookingId": 12,
      "train": "Subarna Express",
      "trainNo": "701",
      "from": "Dhaka (Kamalapur)",
      "to": "Chattogram",
      "date": "1 Aug 2026",
      "scheduledDeparture": "07:00",
      "expectedDeparture": "07:25",
      "platform": "4",
      "coach": "Snigdha / SNIGDHA-12",
      "status": "delayed",
      "delayMinutes": 25,
      "agentNote": "Called you about the new 07:25 departure.",
      "pnr": "BR7QX2M4KD",
      "bookingStatus": "confirmed",
      "seatClass": "SNIGDHA",
      "seatNumbers": ["SNIGDHA-12"],
      "passengerCount": 1,
      "farePaid": 464
    }
  ],
  "alertsReceived": 1
}
```

`status` is the agents' delay state (`on-time`, `at-risk`, `delayed`);
`bookingStatus` is the ticket's own lifecycle (`confirmed`, `cancelled`).
They are separate fields on purpose. `delayMinutes` is the delay that
remains *after* whatever the Scheduler Agent has already recovered.
`alertsReceived` counts the journeys an agent has acted on.

### GET /api/stations

```json
{ "stations": [{ "code": "CTG", "name": "Chattogram", "division": "Chattogram" }] }
```

### GET /api/trains/search?from=DHKA&to=CTG&date=1%20Aug%202026

All three parameters are required, and `from` must differ from `to`.
Availability and fare are for the leg travelled, not the train's whole
route.

```json
{
  "trains": [
    {
      "trainId": 3,
      "name": "Subarna Express",
      "number": "701",
      "from": "Dhaka (Kamalapur)",
      "to": "Chattogram",
      "departure": "07:00",
      "arrival": "12:00",
      "durationMinutes": 300,
      "distanceKm": 320.0,
      "seatClasses": [
        {
          "code": "SNIGDHA",
          "label": "Snigdha",
          "fare": 464,
          "totalSeats": 60,
          "availableSeats": 47
        }
      ]
    }
  ]
}
```

Results are ordered by departure time. A train that does not call at both
stations, in that order, is left out rather than returned with no seats.

| Status | When |
|---|---|
| `400` | A missing parameter, or the same station twice |

### GET /api/trains/&lt;train_id&gt;/seats?class=SNIGDHA&date=1%20Aug%202026

```json
{ "totalSeats": 60, "availableSeats": ["SNIGDHA-1", "SNIGDHA-4"] }
```

| Status | When |
|---|---|
| `400` | No date, or a class this train does not sell |
| `404` | No train with that id |

### POST /api/bookings

```json
{
  "trainId": 3,
  "date": "1 Aug 2026",
  "from": "DHKA",
  "to": "CTG",
  "seatClass": "SNIGDHA",
  "seatNumbers": ["SNIGDHA-12"],
  "passengers": [{ "name": "Rafiq Ahmed", "age": 34, "idNumber": "1010101010" }]
}
```

`seatNumbers` is optional — leave it out and the first free seats are
allocated. When it is sent it must hold exactly one free seat per passenger.

`201` → `{ "booking": { ...the journey shape above... } }`

Availability is re-checked inside the transaction rather than trusted from
an earlier `/seats` call, so two passengers racing for the last seat cannot
both win it.

| Status | When |
|---|---|
| `400` | Bad JSON, no date, a class the train does not sell, no passengers, a passenger with no name, or two stations this train does not run between |
| `404` | No train with that id |
| `409` | A requested seat has gone, or fewer seats are left than passengers |
| `503` | Five PNR generations collided in a row — retry (astronomically unlikely) |

### GET /api/bookings/&lt;pnr&gt;

The journey shape above, plus a `passengers` list:

```json
{
  "booking": {
    "pnr": "BR7QX2M4KD",
    "passengers": [
      { "name": "Rafiq Ahmed", "age": 34, "idNumber": "1010101010", "seatNumber": "SNIGDHA-12" }
    ]
  }
}
```

A PNR belonging to someone else answers `404`, not `403` — a `403` would
confirm the PNR is real.

### POST /api/bookings/&lt;booking_id&gt;/cancel

`200` → `{ "booking": { ..., "bookingStatus": "cancelled" } }`

The seats free themselves: availability is counted live off confirmed
bookings, so there is nothing else to release.

| Status | When |
|---|---|
| `404` | No such booking, or it is not this account's |
| `409` | Already cancelled |

## Either role

### GET /api/train-info

Every train in the network, with its route and its fares.

```json
{
  "trains": [
    {
      "name": "Subarna Express",
      "number": "701",
      "origin": "Dhaka (Kamalapur)",
      "destination": "Chattogram",
      "distanceKm": 320,
      "scheduledHalts": 8,
      "route": ["Dhaka (Kamalapur)", "Cumilla", "Chattogram"],
      "seatClasses": [{ "code": "SNIGDHA", "label": "Snigdha", "fare": 464 }]
    }
  ]
}
```

## Authority endpoints

### GET /api/station/&lt;code&gt;

Everything the Station Master Panel draws, in one response, so the meters
cannot disagree with the alerts printed beside them. Codes are matched
case-insensitively.

```json
{
  "station": {
    "name": "Dhaka (Kamalapur)",
    "code": "DHKA",
    "division": "Dhaka",
    "passengersOnSite": 3180,
    "capacity": 3500
  },
  "platforms": [
    { "id": "4", "occupancy": 420, "capacity": 500, "waitingFor": "Subarna Express" }
  ],
  "arrivals": [
    {
      "id": "A-701",
      "train": "Subarna Express",
      "trainNo": "701",
      "from": "Dhaka (Kamalapur)",
      "scheduled": "07:00",
      "expected": "07:25",
      "platform": "4",
      "status": "delayed",
      "route": ["Dhaka (Kamalapur)", "Cumilla", "Chattogram"]
    }
  ],
  "agentAlerts": [
    { "agent": "Manager Agent", "severity": "info", "message": "Called 3 passengers about train 701." }
  ]
}
```

`404` when no station carries that code.

### GET /api/trains

Trains a delay can be reported against — the ones someone has actually
booked. This is what fills the Report a Delay picker.

```json
{
  "trains": [
    {
      "trainNo": "701",
      "name": "Subarna Express",
      "destination": "Chattogram",
      "status": "on-time",
      "scheduledDeparture": "07:00"
    }
  ]
}
```

### GET /api/agent-logs

The full audit trail, newest first.

```json
{ "logs": [{ "agent": "Risk Agent", "severity": "warning", "message": "Train 759 at 72% risk of delay." }] }
```

### POST /api/delays

```json
{ "trainNo": "701", "minutes": 25 }
```

Applies the delay to every non-cancelled booking on that train, keeps the
arrivals board in step, then runs one full agent cycle.

```json
{
  "reported": {
    "train": "Subarna Express",
    "minutes": 25,
    "scheduledDeparture": "07:00",
    "departureAfterDelay": "07:25",
    "passengersAffected": 3
  },
  "settledDeparture": "07:18",
  "ranAt": "14:32",
  "results": [{ "agent": "Risk Agent" }]
}
```

`reported.departureAfterDelay` is the delay as entered; `settledDeparture`
is where the Scheduler Agent left it. They differ whenever the Scheduler
found time to claw back — which is why the reported figures are read before
the cycle runs rather than after.

| Status | When |
|---|---|
| `400` | Bad JSON, or a `minutes` value that is not a positive number |
| `404` | No booked journey on that train |
| `503` | The Risk Agent's model has not been trained — run `python ml/train_model.py` |

### POST /api/agents/run

One Observe → Reason → Act pass across all five agents, on demand.

```json
{ "ranAt": "14:32", "results": [{ "agent": "Manager Agent" }] }
```

Each entry in `results` always carries `agent`; its remaining keys are that
agent's own summary of what it changed, so they differ per agent. `503`
while the risk model is missing, as above.
