# RailBot BD

An Autonomous Multi-Agent Management System for Train Delay Coordination.

**Course:** CSE 327 — Software Engineering
**Instructor:** Reeshoon Sayera (RSY)

## Problem

Bangladesh Railway faces chronic train delays, causing passenger inconvenience and
station overcrowding. There is currently no intelligent system to proactively manage
these delays. RailBot BD replaces passive delay tracking with active, autonomous
coordination using five AI agents that observe conditions, reason about the best
response, and act without waiting for a human operator.

## The Five Agents

Every agent follows the same **Observe → Reason → Act** cycle.

| Agent | Responsibility |
|---|---|
| **Manager Agent** | Notifies passengers of delays by SMS, sent without a human triggering it |
| **Risk Agent** | Predicts delay risk from telemetry and weather using an ML model |
| **Scheduler Agent** | Recalculates routes and adjusts the master timetable |
| **Resource Agent** | Monitors station crowding and allocates staff and waiting rooms |
| **Advisor Agent** | Logs every agent decision and suggests long-term improvements |

## Tech Stack

- **Frontend:** React.js — Passenger Dashboard, Station Master Control Panel, Timetable
- **Backend:** Django (Python REST API), token auth via `rest_framework.authtoken`
- **Database:** SQLite (development) / PostgreSQL (production)
- **Agents & AI:** Python decision-loop classes, scikit-learn, Google Gemini API
- **External APIs:** sms.net.bd (delay notices and OTP verification); OpenWeatherMap is named in the design but not yet wired up — see "Where the weather comes from" below

## Project Structure

```
railbot-bd/
├── frontend/          React app (Passenger + Station Master dashboards)
└── backend/
    ├── railbot/       Django project — settings and root URLs
    ├── core/          Django app — models, views, auth, booking, and the five agents
    │   ├── models.py      Booking, Train, TrainStop, Station, Profile, AuthorityID, ...
    │   ├── views.py       the data + booking API endpoints, role-gated
    │   ├── auth.py        bearer-token check + role decorators
    │   ├── auth_views.py  signup/login endpoints
    │   ├── scheduler.py   APScheduler job that runs the agent cycle on a timer
    │   ├── agents/        BaseAgent plus the five agents
    │   ├── services/      otp.py, gemini.py, booking.py — the outward-facing calls
    │   └── management/    seed and run_agents commands
    └── ml/            dataset generator, trainer, and the saved model
```

## Getting Started

Requires Node.js 20+ and Python 3.11+. Run the two servers in separate terminals.

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt
copy .env.example .env
venv\Scripts\python ml\generate_dataset.py
venv\Scripts\python ml\train_model.py
venv\Scripts\python manage.py migrate
venv\Scripts\python manage.py seed
venv\Scripts\python manage.py runserver
```

The API then answers on `http://localhost:8000`. `manage.py seed` clears and
reloads the sample data (and loads a handful of test Authority IDs — see
Authentication below), so it is safe to re-run at any time. The two `ml`
scripts build the Risk Agent's model and only need running once.

`.env` holds the third-party credentials — see `.env.example` for what each
one does. Leave it unfilled for local dev; every one of them has a fallback,
and nothing about the system's behaviour depends on which are present:

| Variable | Without it |
|---|---|
| `SMS_NET_BD_API_KEY` | The Manager Agent's delay texts are simulated, and passenger OTP accepts `000000` |
| `OPENWEATHER_API_KEY` | No effect either way — see "Where the weather comes from" below |
| `GEMINI_API_KEY` | The Advisor Agent's briefing is written from a template |

No JWT secret or similar is needed — auth uses DRF's Token model, which
generates its own random key per user rather than signing anything with a
shared secret.

**Where the weather comes from:** `core/agents/weather.py`'s
`current_weather()` checks for `OPENWEATHER_API_KEY`, but the branch that
would call the live API is an empty `pass` — nothing is wired up yet. A
condition is always produced by the same seeded-per-destination random
choice, whether or not a key is set. Treat this as simulated, not as a live
integration, until that branch is filled in.

The agent cycle also runs on its own: `core/scheduler.py` starts an
APScheduler `BackgroundScheduler` from `CoreConfig.ready()` and fires
`run_cycle()` automatically every `AGENT_CYCLE_MINUTES` (default 5) for as
long as `runserver` is up, in addition to the manual triggers below
(`manage.py run_agents`, the Run Agents button, and `POST /api/delays`).

Django's admin is available at `http://localhost:8000/admin` once a superuser
exists (`manage.py createsuperuser`) — useful for browsing the agent log during
a demo.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The dashboards are then served at `http://localhost:5173`.

## API

Every endpoint below except `health` and the six under Authentication
requires `Authorization: Bearer <token>` — see Authentication for how a
token is issued. "Role" is who the endpoint answers for; a request from the
other role gets `403`, no token gets `401`.

| Endpoint | Role | Returns |
|---|---|---|
| `GET /api/health` | — (public) | Service check |
| `GET /api/journeys` | Passenger | The signed-in passenger's own booked journeys |
| `GET /api/train-info` | Either | Every train in the network — the Timetable |
| `GET /api/station/<code>` | Authority | Platforms, arrivals and agent alerts for one station |
| `GET /api/trains` | Authority | Trains a delay can be reported against |
| `GET /api/agent-logs` | Authority | The full audit trail, newest first |
| `POST /api/delays` | Authority | Report a train as late, then run a cycle |
| `POST /api/agents/run` | Authority | Runs one cycle across all five agents |
| `GET /api/stations` | Passenger | Every station in the network, for the booking search's From/To pickers |
| `GET /api/trains/search` | Passenger | Trains between two stations on a date, with fare and seat availability per class |
| `GET /api/trains/<id>/seats` | Passenger | The seat map for one train, class and date |
| `POST /api/bookings` | Passenger | Book seats on a train; returns the ticket, PNR included |
| `GET /api/bookings/<pnr>` | Passenger | One ticket by its PNR |
| `POST /api/bookings/<id>/cancel` | Passenger | Cancel a booking; its seats become bookable again immediately |

## Authentication

Two roles, **Passenger** and **Authority**, each with their own signup and a
login shared by both.

| Endpoint | Method | Body |
|---|---|---|
| `/api/auth/passenger/signup` | POST | `phone_number`, `nid_number`, `password` |
| `/api/auth/passenger/verify-signup` | POST | `phone_number`, `code` |
| `/api/auth/authority/signup` | POST | `phone_number`, `authority_id`, `password` |
| `/api/auth/login` | POST | `phone_number`, `password` (either role) |

**Passenger signup** takes an NID (10-digit old format or 17-digit new
format, digits only) and a phone number, both unique per account. The phone
is then OTP-confirmed through sms.net.bd — `verify-signup` with the code
activates the account. Login is refused until that happens. NID uniqueness
is checked, but the NID itself is never verified against a government
database — `nid_verified`-style manual checking is a future addition, not
something this system can do.

**Authority signup** takes a phone number and a BD Railway-issued Authority
ID that must already exist in the `AuthorityID` table — nothing here
generates or accepts an arbitrary ID, and each one can be claimed once. No
OTP step: the ID itself is the proof of authorization, so the account is
active immediately. `manage.py seed` loads five example IDs
(`BR-AUTH-1001` through `BR-AUTH-1005`) to test signup against; pick any
unclaimed one.

**Login** is phone + password for both roles — the response carries which
role the account is, so the frontend doesn't have to ask. Wrong password and
unknown phone number return the same error message on purpose, so a login
attempt can't be used to check which phone numbers have accounts.

Tokens come from `rest_framework.authtoken`'s `Token` model — a random key
per user, rotated (old one invalidated) on every successful login. Checked
by a plain decorator (`core/auth.py`), not DRF's own view layer — nothing
else in this project runs as a DRF view.

### Who sees which bookings

A passenger token proves you are *a* passenger. It is not a reason to read
every other passenger's travel plans, so `/api/journeys` is scoped to the
account asking for it (`Profile.own_bookings`):

1. the `Passenger` record a Station Authority linked to the account, if one
   was linked;
2. otherwise any `Passenger` record carrying the account's phone number — a
   seat is booked at the counter against a number, so that number is the
   link.

Both directions work because bookings and signups happen in either order.
Booking first, then signing up, claims the record at signup; signing up
first and booking later is caught by the phone-number match. The authority
endpoints are deliberately *not* scoped — an operator's board is supposed to
show the whole station.

### Demo logins

`manage.py seed` creates two passenger accounts, both password
`railbot123`, so signing in as each shows a different list — that is the
scoping above, visible:

| Phone | Sees |
|---|---|
| `+8801700000000` | 3 journeys — trains 701, 709 (delayed), 759 (at risk) |
| `+8801800000000` | 2 journeys — trains 705, 725, both on time |

Both are pre-verified, since there is no real handset behind either number
to receive an OTP. They exist only in the demo database `seed` rebuilds on
every run.

## Booking

A signed-in passenger can search a route, pick a train and seat class,
optionally pick specific seats, and confirm — the result is an ordinary
`Booking` row, so it appears on the dashboard and gets picked up by the five
agents exactly like a row `manage.py seed` created.

1. `GET /api/stations` — populate the From/To pickers.
2. `GET /api/trains/search` — every train running between those two stations
   on that date, with fare and remaining seats per class (`TrainStop`
   supplies the per-station timetable, so this works for any two stops on a
   train's line, not only its endpoints).
3. `GET /api/trains/<id>/seats` — the seat map for one class/date, if the
   passenger wants to choose specific seats rather than let the booking pick
   any free one.
4. `POST /api/bookings` — creates the `Booking` (plus one `BookingPassenger`
   row per rider, name/age/ID), generates the PNR, and re-checks
   availability inside the transaction so two passengers can't both win the
   last seat.
5. `POST /api/bookings/<id>/cancel` — sets the booking's status to
   `cancelled`. Seats free themselves immediately: availability is always
   counted live off confirmed bookings, never held in a separate counter.

**Known simplification:** seat availability is tracked per (train, date,
class) as a whole, not per boarding/alighting segment. Booking any leg of a
route on a date holds that seat for the entire date, rather than freeing it
for a later passenger travelling a non-overlapping stretch the way the real
reservation system can.

A booking's own `status` field (on-time / at-risk / delayed) is the agents'
to write, same as any seeded row. Cancelling is a separate `booking_status`
field the agents never touch going the other way — a cancelled ticket is
excluded from every agent's `observe()` so it can't come back to life with a
recovered departure time or a delay text.

## How the agents work

Every agent subclasses `BaseAgent` and implements the same three steps —
`observe()`, `reason()`, `act()` — with `run()` executing them in order. No agent
can act without first observing and reasoning, and every action it takes is
written to `agent_logs`, which is the audit trail the Advisor Agent reads back.

They run in the order a delay actually propagates:

1. **Risk Agent** predicts which journeys are about to slip, using the trained model
2. **Scheduler Agent** recovers what time it can on those already late
3. **Manager Agent** texts passengers with the times the Scheduler just settled
4. **Resource Agent** moves staff to platforms filling up as a result
5. **Advisor Agent** reviews everything the other four just did

Running Manager before Scheduler would call passengers with times about to
change, so the sequence is part of the design.

Agents never call each other. They communicate only through the database, so
any one of them can be changed or removed without touching the rest.

### Where the language model sits

The Advisor Agent is the only one that uses Gemini, and it uses it for one
thing: turning figures the other four already produced into two or three
sentences of shift briefing for the station master.

It decides nothing. Every recommendation in the log comes from a rule in
`AdvisorAgent.reason()`, which runs identically whether or not a key is set,
and no output of `core/services/gemini.py` is ever written back to a
Booking, a Platform or a Train — it only becomes one line in the audit
trail. The model is handed the figures and told not to invent trains,
platforms, times or causes.

That boundary is deliberate. A model that could re-platform a train or
withdraw a delay notice would be a far worse failure than an awkward
sentence, and `test_gemini.py` asserts it directly: the agent is run with a
mocked Gemini reply that reads like an instruction, and every train,
platform and booking is compared before and after.

Without `GEMINI_API_KEY`, `_template_briefing()` writes the same paragraph
from the same figures. Failures — a bad key, a timeout, a safety-blocked
reply — fall back to it too, so a slow text-generation API can never take
the control room down with it. The panel labels which one wrote the
briefing rather than letting the fallback pass for the model.

To run a cycle without the frontend: `venv\Scripts\python manage.py run_agents`

Agents act on *change*: re-running a cycle when nothing has moved produces no
new calls, no repeated alerts and no duplicate advice.

## The network data

`backend/core/data/network.py` holds the intercity network: 36 stations, 15
corridors and 52 services covering Dhaka–Chattogram, Cox's Bazar, Sylhet,
Rajshahi, Khulna, the northern lines to Panchagarh and Chilahati, and the
Mymensingh and Kishoreganj branches.

Station coordinates are real latitude and longitude, projected onto the map's
viewBox in `frontend/src/data/stations.js`, so a route is drawn where it
actually runs rather than placed by eye. Selecting an inbound train traces its
route across the country.

**On accuracy:** train names, numbers and the stations each service calls at
are compiled from published route information. The departure times, distances
and halt counts are representative, not lifted from the current official
timetable — Bangladesh Railway publishes no machine-readable feed, and the
open-data portal's intercity dataset is a PDF last updated in 2017. They exist
to give the Risk Agent's model realistic inputs. Verify against the official
timetable before treating any figure here as authoritative.

## The Risk Agent's model

A random forest over six features — weather, current delay, route distance,
scheduled halts, hour of day, and whether it is rush hour. Bangladesh Railway
publishes no delay dataset, so `ml/generate_dataset.py` synthesises one from
documented rules about how delays behave, and the model learns those
relationships back.

On held-out data it scores **0.76 accuracy** and **0.80 ROC AUC**, against a
0.66 baseline from always predicting "on time". A journey is flagged once its
predicted delay probability reaches 0.60.

## Screens

| Route | Role | What it is |
|---|---|---|
| `/auth` | — | Role picker: Passenger or Authority |
| `/auth/passenger` | — | Passenger sign up / sign in |
| `/auth/authority` | — | Authority sign up / sign in |
| `/passenger` | Passenger | Passenger Dashboard — booked journeys and their delay status |
| `/book` | Passenger | Book a Ticket — search, seat selection, review and PNR confirmation |
| `/station-master` | Authority | Station Master Panel — crowding, inbound trains, agent log, network map |
| `/trains` | Either | Trains & Routes (Timetable) — every service in the network with its route and fares |

The left rail navigates between the three role-gated screens, filtered to
whichever the signed-in role can actually reach. Typing a URL for the other
role's screen redirects back to your own home rather than showing it -
enforced again on the backend (see API above), since a frontend redirect
alone is not access control.

## Documentation

- [Software Requirements Specification](docs/RailBot_BD_SRS.docx) — v1.1, IEEE 830 format
- [UML diagrams](docs/diagrams/) — use case, sequence (×2), communication, activity, and class diagrams, approved by course faculty
- [Design patterns applied](backend/PATTERNS.md) — where each pattern lives and why two were rejected
- [Defect register](backend/BUGS.md) — bugs found by the test suite and how they were fixed

## Tests

```
cd backend
venv\Scripts\python manage.py test
```

116 tests in `core/tests/`, grouped by what each one defends rather than by
which module it touches:

| File | Defends |
|---|---|
| `test_journeys.py` | A passenger sees their own bookings and nobody else's |
| `test_auth.py` | Role separation, signup rules, token rotation |
| `test_agents.py` | Observe-Reason-Act, and that a repeated cycle does not act twice |
| `test_gemini.py` | The briefing works without a key, and the model decides nothing |
| `test_risk.py` | The risk threshold, its own repeat-alert rule, and the six features fed to the model |
| `test_contract.py` | The exact JSON keys the React dashboards read, so a rename in a model doesn't silently break a card |
| `test_delays.py` | `POST /api/delays` reaches every affected booking and rejects bad input |
| `test_bookings.py` | Search pricing, booking, seat exhaustion, cancellation, and cross-account scoping |

Most of these were written against bugs this project actually had. The
Scheduler once sized its recovery budget against the *remaining* delay, so
every cycle found more to trim and a 35-minute delay eventually vanished.
The Manager checked only whether a passenger had been contacted, never
whether the time it had given them was still true. The Resource Agent
re-logged the same crowding alert every five minutes. Each has a test named
after the behaviour it is holding in place, so none of them can come back
without something turning red.

`manage.py test` runs green: 116/116. It wasn't always — `test_contract.py`
and `test_delays.py` each still carry a handful of tests marked
`EXPECTED FAILURE` in their own docstring, left over from when they caught
six real bugs (`report_delay` reaching only one passenger per delayed train,
a `ZeroDivisionError` in the Resource Agent, a substring match crediting
Platform 1 with Platform 10's alerts, and three more).
[`backend/BUGS.md`](backend/BUGS.md) documents all six worst-first with the
exact line at fault; the docstring label is now historical, not a live
warning, since the fixes have landed.

The four tests covering the full five-agent cycle need `ml/risk_model.pkl`,
which is a build product and not in version control. They skip rather than
fail when it is missing, so a fresh clone runs green before
`python ml/train_model.py` has been run.

## Status

Working end to end: every screen reads live data from the Django API, a
passenger can book and cancel a real ticket without touching the admin, and
all five agents run against the database with the Risk Agent driven by a
trained model and the Advisor Agent's briefing written by Gemini.

Two things reach outside the system, each through exactly one function so it
can be found and swapped: `send_sms()` for delay texts and passenger OTP,
and `write_briefing()` for the shift briefing. Both fall back when their key
is absent, which is how the project runs locally and in tests. What falls
back is the *outside call* — the agents' own decisions are made by the same
rules either way.

A third function, `current_weather()`, has the same shape but isn't wired up
yet — see "Where the weather comes from" above. It always returns a seeded,
simulated condition regardless of `OPENWEATHER_API_KEY`.

## Team

- Istiak Ahammed Rumi
- Rajia Sultana
- Md. Arian Al Hasan
