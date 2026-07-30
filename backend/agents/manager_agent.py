"""Manager Agent - tells passengers about delays without being asked.

Observes journeys that have slipped, reasons about what each passenger needs to
hear, and places the call.

The call itself is simulated: place_call() records what would be spoken instead
of dialling. Swapping in Twilio means filling in that one function - everything
that decides who to call and what to say stays exactly as it is.
"""

import os

from models import Booking, db

from .base import BaseAgent


def place_call(phone, message):
    """Deliver a spoken delay notice.

    Simulated unless Twilio credentials are present. Returns a short string
    describing what happened, which the agent writes into the audit trail.
    """
    if os.environ.get("TWILIO_ACCOUNT_SID") and os.environ.get("TWILIO_AUTH_TOKEN"):
        # Live call goes here: build TwiML from `message` and dial `phone`.
        pass

    return f"simulated call to {phone}"


class ManagerAgent(BaseAgent):
    name = "Manager Agent"

    def observe(self):
        """Delayed journeys where the passenger is holding a stale time.

        Comparing against the time last read out - rather than merely whether a
        call happened - means a passenger gets called again when the Scheduler
        Agent moves their departure, and is left alone when nothing changed.
        """
        return [
            booking
            for booking in Booking.query.filter_by(status="delayed").all()
            if booking.notified_departure != booking.expected_departure
        ]

    def reason(self, observation):
        """Compose what each passenger should hear."""
        decisions = []
        for booking in observation:
            # A passenger who was already given a time is being corrected, not
            # told for the first time, and the call should say so.
            is_update = booking.notified_departure is not None

            opening = (
                "This is RailBot from Bangladesh Railway with an updated time for"
                if is_update
                else "This is RailBot from Bangladesh Railway. Your train,"
            )
            spoken = (
                f"{opening} {booking.train.name} to {booking.train.destination}. "
                f"It is running {booking.current_delay} minutes late and now departs "
                f"at {booking.expected_departure} from platform {booking.platform}."
            )
            decisions.append(
                {"booking": booking, "spoken": spoken, "isUpdate": is_update}
            )
        return decisions

    def act(self, decision):
        """Place each call and record it against the journey."""
        called = []

        for item in decision:
            booking = item["booking"]
            passenger = booking.passenger

            outcome = place_call(passenger.phone, item["spoken"])

            # Remember what was said, so the next cycle knows whether this
            # passenger still holds the right time.
            booking.notified_departure = booking.expected_departure

            booking.agent_note = (
                f"Manager Agent called you with the updated departure time. "
                if item["isUpdate"]
                else f"Manager Agent called you about the "
                f"{booking.current_delay} minute delay. "
            ) + (
                f"Your train now departs at {booking.expected_departure} "
                f"from platform {booking.platform}."
            )

            kind = "Updated time" if item["isUpdate"] else "Delay call"
            self.log(
                f"{kind} read out to {passenger.name} for {booking.train.name} - "
                f"now departing {booking.expected_departure} ({outcome}).",
                severity="info",
            )
            called.append(
                {
                    "passenger": passenger.name,
                    "train": booking.train.name,
                    "departure": booking.expected_departure,
                }
            )

        db.session.commit()
        return {"examined": len(decision), "called": called}
