"""Facade - one door into the delay subsystem.

Reporting a delay touches a lot: validate the input, find every booking on
the train, mark each one, keep the arrivals board in step, run five agents in
a fixed order, and read the reported figures before the Scheduler moves them.
That sequence lived inside a view, which meant the view knew the order of
operations, and anything else that wanted to report a delay - a management
command, a test, the CLI runner, an import from an operations feed - had to
know it too, or go through HTTP to get at it.

RailBotFacade holds the sequence in one place and exposes it as a method.
The view becomes what a view should be: parse a request, call one thing,
shape a response.

The facade adds no rules of its own. Everything here already existed; it
simply has a name now, and one caller can no longer get the order wrong.
"""

from datetime import datetime

from core.agents import run_cycle
from core.models import Booking, Station
from core.agents.scheduler_agent import add_minutes, sync_arrivals

MIN_DELAY_MINUTES = 1
MAX_DELAY_MINUTES = 300


class DelayReportError(Exception):
    """A delay report that cannot be accepted.

    Carries the HTTP status the caller should use, so the view does not have
    to map error kinds back onto status codes - which would put a second copy
    of that knowledge outside the facade.
    """

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


class RailBotFacade:
    """The operations the system offers, as plain method calls."""

    # ---- delay reporting -------------------------------------------------

    @staticmethod
    def validate_delay_report(train_no_raw, minutes_raw):
        """Check a report before anything acts on it.

        Separate from report_delay() so a caller can validate without
        applying - and so the rules have one home. Returns the cleaned
        (train_no, minutes) pair; raises DelayReportError otherwise, each
        with its own message, because a station master who mistyped should
        not have to guess which of four things went wrong.
        """
        train_no = str(train_no_raw or "").strip()
        if not train_no:
            raise DelayReportError("Pick a train first.")

        # bool is a subclass of int, so int(True) is 1 - a checkbox posted
        # into this field would otherwise book a one-minute delay.
        if isinstance(minutes_raw, bool):
            raise DelayReportError("Delay must be a whole number of minutes.")

        try:
            minutes = int(minutes_raw)
        except (TypeError, ValueError):
            raise DelayReportError("Delay must be a whole number of minutes.")

        if not MIN_DELAY_MINUTES <= minutes <= MAX_DELAY_MINUTES:
            raise DelayReportError(
                f"Delay must be between {MIN_DELAY_MINUTES} and "
                f"{MAX_DELAY_MINUTES} minutes."
            )

        return train_no, minutes

    @staticmethod
    def report_delay(train_no_raw, minutes_raw):
        """Apply a delay and let the agents respond. The whole sequence.

        Returns what the caller needs to confirm the report: the delay as it
        was entered, the departure the Scheduler settled on, and what each
        agent did.
        """
        train_no, minutes = RailBotFacade.validate_delay_report(
            train_no_raw, minutes_raw
        )

        # A cancelled booking is not a delayed one - the passenger is not
        # travelling, and texting them a new departure time would be worse
        # than saying nothing. Matches how the Manager Agent selects.
        bookings = list(
            Booking.objects.select_related("train")
            .filter(train__number=train_no)
            .exclude(booking_status="cancelled")
        )
        if not bookings:
            raise DelayReportError(
                f"No booked journey on train {train_no}.", status=404
            )

        # A delay is a fact about the train, so it lands on every booking
        # aboard it - the Manager Agent selects on status and would never see
        # a passenger this loop skipped.
        for booking in bookings:
            booking.status = "delayed"
            booking.delay_minutes = minutes
            booking.recovered_minutes = 0
            booking.expected_departure = add_minutes(
                booking.scheduled_departure, minutes
            )
            booking.notified_departure = None
            booking.agent_note = None
            booking.save()
            sync_arrivals(booking)

        # Read these before the cycle: afterwards the Scheduler has already
        # pulled expected_departure earlier, and reporting that back as "the
        # delay you entered" would not add up.
        first = bookings[0]
        reported = {
            "train": first.train.name,
            "minutes": minutes,
            "scheduledDeparture": first.scheduled_departure,
            "departureAfterDelay": first.expected_departure,
            "passengersAffected": len(bookings),
        }

        results = run_cycle()

        first.refresh_from_db()

        return {
            "reported": reported,
            "settledDeparture": first.expected_departure,
            "ranAt": datetime.now().strftime("%H:%M"),
            "results": results,
        }

    # ---- cycles ----------------------------------------------------------

    @staticmethod
    def run_agent_cycle():
        """One Observe-Reason-Act pass across all five agents."""
        return {
            "ranAt": datetime.now().strftime("%H:%M"),
            "results": run_cycle(),
        }

    # ---- reads -----------------------------------------------------------

    @staticmethod
    def station_picture(code):
        """One station's full operating picture.

        Assembled in one call so the meters cannot disagree with the alerts
        beside them - four separate requests would each arrive at a different
        moment.
        """
        station = Station.objects.filter(code=str(code).upper()).first()
        if station is None:
            raise DelayReportError(f"No station with code {code}.", status=404)
        return station
