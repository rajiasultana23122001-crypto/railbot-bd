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
| **Manager Agent** | Notifies passengers of delays through autonomous voice calls |
| **Risk Agent** | Predicts delay risk from telemetry and weather using an ML model |
| **Scheduler Agent** | Recalculates routes and adjusts the master timetable |
| **Resource Agent** | Monitors station crowding and allocates staff and waiting rooms |
| **Advisor Agent** | Logs every agent decision and suggests long-term improvements |

## Tech Stack

- **Frontend:** React.js — Passenger Dashboard and Station Master Control Panel
- **Backend:** Django (Python REST API)
- **Database:** SQLite (development) / PostgreSQL (production)
- **Agents & AI:** Python decision-loop classes, scikit-learn, Google Gemini API
- **External APIs:** Twilio (voice calls), OpenWeatherMap (weather data)

## Project Structure

```
railbot-bd/
├── frontend/          React app (Passenger + Station Master dashboards)
└── backend/
    ├── railbot/       Django project — settings and root URLs
    ├── core/          Django app — models, views, and the five agents
    │   ├── models.py      7 tables, including the agent_logs audit trail
    │   ├── views.py       the API endpoints
    │   ├── agents/        BaseAgent plus the five agents
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
venv\Scripts\python ml\generate_dataset.py
venv\Scripts\python ml\train_model.py
venv\Scripts\python manage.py migrate
venv\Scripts\python manage.py seed
venv\Scripts\python manage.py runserver
```

The API then answers on `http://localhost:8000`. `manage.py seed` clears and
reloads the sample data, so it is safe to re-run at any time. The two `ml`
scripts build the Risk Agent's model and only need running once.

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

| Endpoint | Returns |
|---|---|
| `GET /api/health` | Service check |
| `GET /api/journeys` | Booked journeys for the Passenger Dashboard |
| `GET /api/station/<code>` | Platforms, arrivals and agent alerts for one station |
| `GET /api/trains` | Trains a delay can be reported against |
| `GET /api/agent-logs` | The full audit trail, newest first |
| `POST /api/delays` | Report a train as late, then run a cycle |
| `POST /api/agents/run` | Runs one cycle across all five agents |

## How the agents work

Every agent subclasses `BaseAgent` and implements the same three steps —
`observe()`, `reason()`, `act()` — with `run()` executing them in order. No agent
can act without first observing and reasoning, and every action it takes is
written to `agent_logs`, which is the audit trail the Advisor Agent reads back.

They run in the order a delay actually propagates:

1. **Risk Agent** predicts which journeys are about to slip, using the trained model
2. **Scheduler Agent** recovers what time it can on those already late
3. **Manager Agent** calls passengers with the times the Scheduler just settled
4. **Resource Agent** moves staff to platforms filling up as a result
5. **Advisor Agent** reviews everything the other four just did

Running Manager before Scheduler would call passengers with times about to
change, so the sequence is part of the design.

Agents never call each other. They communicate only through the database, so
any one of them can be changed or removed without touching the rest.

To run a cycle without the frontend: `venv\Scripts\python manage.py run_agents`

Agents act on *change*: re-running a cycle when nothing has moved produces no
new calls, no repeated alerts and no duplicate advice.

To run a cycle without the frontend: `venv\Scripts\python run_agents.py`

## The Risk Agent's model

A random forest over six features — weather, current delay, route distance,
scheduled halts, hour of day, and whether it is rush hour. Bangladesh Railway
publishes no delay dataset, so `ml/generate_dataset.py` synthesises one from
documented rules about how delays behave, and the model learns those
relationships back.

On held-out data it scores **0.76 accuracy** and **0.80 ROC AUC**, against a
0.66 baseline from always predicting "on time". A journey is flagged once its
predicted delay probability reaches 0.60.

## Status

Working end to end: both dashboards read live data from the Django API, and all
five agents run against the database with the Risk Agent driven by a trained
model. Voice calls are simulated — `place_call()` in the Manager Agent is the
single function Twilio slots into.

## Team

- Istiak Ahammed Rumi
- Rajia Sultana
- Md. Arian Al Hasan
