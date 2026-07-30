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
- **Backend:** Flask (Python REST API)
- **Database:** SQLite (development) / PostgreSQL (production)
- **Agents & AI:** Python decision-loop classes, scikit-learn, Google Gemini API
- **External APIs:** Twilio (voice calls), OpenWeatherMap (weather data)

## Project Structure

```
railbot-bd/
├── frontend/     React app (Passenger + Station Master dashboards)
└── backend/      Flask API and the five autonomous agents
```

## Getting Started

Requires Node.js 20+ and Python 3.11+. Run the two servers in separate terminals.

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python seed.py
venv\Scripts\python app.py
```

The API then answers on `http://localhost:5000`. `seed.py` rebuilds the SQLite
database from scratch, so it is safe to re-run at any time.

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
| `GET /api/agent-logs` | The full audit trail, newest first |

## Status

Frontend prototype and REST API are working. Both dashboards are built and
navigable, and the Flask API serves the same data from SQLite. Still to come:
connecting the dashboards to the API, then the five agents themselves.

## Team

- Istiak Ahammed Rumi
- Rajia Sultana
- Md. Arian Al Hasan
