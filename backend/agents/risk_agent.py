"""Risk Agent — predicts which journeys are about to slip.

Observes route conditions and weather, reasons with the trained model, and
flags journeys whose predicted delay probability crosses the threshold.
"""

from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd

from models import Booking, db

from .base import BaseAgent
from .weather import current_weather

MODEL_PATH = Path(__file__).resolve().parent.parent / "ml" / "risk_model.pkl"

# Flag a journey once the model puts its delay probability at or above this.
# Lower catches more real delays but cries wolf more often; 0.60 keeps the
# passenger-facing warnings credible.
RISK_THRESHOLD = 0.60

RUSH_HOURS = {7, 8, 9, 17, 18, 19, 20}

_model = None


def load_model():
    """Load the trained model once and reuse it."""
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"{MODEL_PATH.name} is missing. Run: python ml/train_model.py"
            )
        _model = joblib.load(MODEL_PATH)
    return _model


class RiskAgent(BaseAgent):
    name = "Risk Agent"

    def observe(self):
        """Every journey not already known to be delayed, plus its conditions."""
        observations = []
        for booking in Booking.query.filter(Booking.status != "delayed").all():
            train = booking.train
            departure_hour = int(booking.scheduled_departure.split(":")[0])
            observations.append(
                {
                    "booking": booking,
                    "features": {
                        "weather": current_weather(train.destination),
                        "current_delay_minutes": booking.delay_minutes,
                        "distance_km": train.distance_km,
                        "scheduled_halts": train.scheduled_halts,
                        "hour_of_day": departure_hour,
                        "is_rush_hour": 1 if departure_hour in RUSH_HOURS else 0,
                    },
                }
            )
        return observations

    def reason(self, observation):
        """Ask the model how likely each journey is to be delayed."""
        if not observation:
            return []

        model = load_model()
        frame = pd.DataFrame([o["features"] for o in observation])
        probabilities = model.predict_proba(frame)[:, 1]

        decisions = []
        for item, probability in zip(observation, probabilities):
            decisions.append(
                {
                    "booking": item["booking"],
                    "weather": item["features"]["weather"],
                    "probability": float(probability),
                    "at_risk": probability >= RISK_THRESHOLD,
                }
            )
        return decisions

    def act(self, decision):
        """Flag the risky journeys and clear those that no longer qualify."""
        flagged, cleared = [], []

        for item in decision:
            booking = item["booking"]
            percent = round(item["probability"] * 100)

            if item["at_risk"] and booking.status != "at-risk":
                booking.status = "at-risk"
                booking.agent_note = (
                    f"Risk Agent puts the chance of a delay at {percent}% "
                    f"({item['weather'].replace('_', ' ')} forecast on this route). "
                    "You will be called if the delay is confirmed."
                )
                self.log(
                    f"{booking.train.name} flagged at {percent}% delay risk "
                    f"({item['weather'].replace('_', ' ')}).",
                    severity="medium",
                )
                flagged.append(booking.train.name)

            elif not item["at_risk"] and booking.status == "at-risk":
                booking.status = "on-time"
                booking.agent_note = None
                self.log(
                    f"{booking.train.name} no longer at risk "
                    f"(now {percent}%); warning withdrawn.",
                    severity="info",
                )
                cleared.append(booking.train.name)

        db.session.commit()
        return {
            "examined": len(decision),
            "flagged": flagged,
            "cleared": cleared,
        }
