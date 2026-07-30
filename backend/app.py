"""RailBot BD — Flask REST API.

Serves the data behind both dashboards. Run it with:

    venv\\Scripts\\python app.py

The API then answers on http://localhost:5000.
"""

from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

from agents.scheduler_agent import add_minutes
from models import AgentLog, Arrival, Booking, Platform, Station, Train, db

BASE_DIR = Path(__file__).resolve().parent


def create_app():
    app = Flask(__name__)

    # SQLite lives beside this file. It is gitignored - run seed.py to rebuild.
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{BASE_DIR / 'railbot.db'}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # The React dev server runs on a different port, so the browser needs
    # permission to call this API from there.
    CORS(app, origins=["http://localhost:5173"])

    register_routes(app)
    return app


def register_routes(app):
    @app.get("/api/health")
    def health():
        """Quick check that the API is alive."""
        return jsonify({"status": "ok", "service": "railbot-bd"})

    @app.get("/api/journeys")
    def journeys():
        """Every booked journey, for the Passenger Dashboard."""
        bookings = Booking.query.all()
        # A journey carries an agent note exactly when an agent has already
        # acted on it — a call placed, or a risk flagged. That is what the
        # passenger means by "alerts received".
        alerts_received = sum(1 for b in bookings if b.agent_note)
        return jsonify(
            {
                "journeys": [b.to_dict() for b in bookings],
                "alertsReceived": alerts_received,
            }
        )

    @app.get("/api/station/<code>")
    def station(code):
        """Everything the Station Master Panel shows for one station."""
        station = Station.query.filter_by(code=code.upper()).first()
        if station is None:
            return jsonify({"error": f"No station with code {code}"}), 404

        platforms = Platform.query.filter_by(station_id=station.id).all()
        arrivals = Arrival.query.filter_by(station_id=station.id).all()
        # Newest decision first, which is how the panel reads.
        logs = AgentLog.query.order_by(AgentLog.id.desc()).all()

        return jsonify(
            {
                "station": station.to_dict(),
                "platforms": [p.to_dict() for p in platforms],
                "arrivals": [a.to_dict() for a in arrivals],
                "agentAlerts": [log.to_dict() for log in logs],
            }
        )

    @app.get("/api/agent-logs")
    def agent_logs():
        """The full audit trail, newest first — read by the Advisor Agent."""
        logs = AgentLog.query.order_by(AgentLog.id.desc()).all()
        return jsonify({"logs": [log.to_dict() for log in logs]})

    @app.get("/api/trains")
    def trains():
        """Trains a delay can be reported against — those someone has booked."""
        bookings = Booking.query.all()
        return jsonify(
            {
                "trains": [
                    {
                        "trainNo": b.train.number,
                        "name": b.train.name,
                        "destination": b.train.destination,
                        "status": b.status,
                        "scheduledDeparture": b.scheduled_departure,
                    }
                    for b in bookings
                ]
            }
        )

    @app.post("/api/delays")
    def report_delay():
        """Report a train as running late, then let the agents respond.

        This is the operator-facing entry point: a station master enters what
        has happened, and the agents work out what to do about it.
        """
        payload = request.get_json(silent=True) or {}
        train_no = str(payload.get("trainNo", "")).strip()
        raw_minutes = payload.get("minutes")

        if not train_no:
            return jsonify({"error": "Pick a train first."}), 400

        try:
            minutes = int(raw_minutes)
        except (TypeError, ValueError):
            return jsonify({"error": "Delay must be a whole number of minutes."}), 400

        if not 1 <= minutes <= 300:
            return jsonify({"error": "Delay must be between 1 and 300 minutes."}), 400

        booking = (
            Booking.query.join(Train).filter(Train.number == train_no).first()
        )
        if booking is None:
            return jsonify({"error": f"No booked journey on train {train_no}."}), 404

        # Record the delay as freshly reported: nothing recovered yet, and the
        # passenger has not been told, so the agents have work to do.
        booking.status = "delayed"
        booking.delay_minutes = minutes
        booking.recovered_minutes = 0
        booking.expected_departure = add_minutes(booking.scheduled_departure, minutes)
        booking.notified_departure = None
        booking.agent_note = None
        db.session.commit()

        # Read these before the agents run: afterwards expected_departure has
        # already been pulled earlier by the Scheduler, and reporting that back
        # as "the delay you entered" would not add up.
        train_name = booking.train.name
        departure_after_delay = booking.expected_departure

        from agents import run_cycle

        try:
            results = run_cycle()
        except FileNotFoundError as exc:
            return jsonify({"error": str(exc)}), 503

        return jsonify(
            {
                "reported": {
                    "train": train_name,
                    "minutes": minutes,
                    "scheduledDeparture": booking.scheduled_departure,
                    "departureAfterDelay": departure_after_delay,
                },
                "settledDeparture": booking.expected_departure,
                "ranAt": datetime.now().strftime("%H:%M"),
                "results": results,
            }
        )

    @app.post("/api/agents/run")
    def run_agents():
        """Run one Observe - Reason - Act cycle across all five agents.

        Returns what each agent did, so the dashboard can show the cycle
        happening rather than only its after-effects.
        """
        from agents import run_cycle

        try:
            results = run_cycle()
        except FileNotFoundError as exc:
            # The Risk Agent's model has not been trained yet.
            return jsonify({"error": str(exc)}), 503

        return jsonify({"ranAt": datetime.now().strftime("%H:%M"), "results": results})


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
