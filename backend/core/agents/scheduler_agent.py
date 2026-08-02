"""Scheduler Agent - claws back time on journeys that have already slipped.

Observes delayed journeys, reasons about how much can be recovered by trimming
halts at minor stations, and rewrites the expected departure accordingly.
"""

from core.models import Booking

from .base import BaseAgent

# A minor halt can realistically be shortened by about this much without
# leaving passengers behind.
MINUTES_SAVED_PER_HALT = 1.5

# Never trim more than this share of a delay; beyond it the timetable stops
# being believable and station staff lose trust in it.
MAX_RECOVERY_SHARE = 0.4


def add_minutes(hhmm, minutes):
    """Shift a HH:MM string by a number of minutes, wrapping past midnight."""
    hours, mins = (int(part) for part in hhmm.split(":"))
    total = (hours * 60 + mins + minutes) % (24 * 60)
    return f"{total // 60:02d}:{total % 60:02d}"


class SchedulerAgent(BaseAgent):
    name = "Scheduler Agent"

    def observe(self):
        """Journeys currently running late."""
        return list(Booking.objects.filter(status="delayed").select_related("train"))

    def reason(self, observation):
        """Work out how many minutes each journey can still recover.

        The budget is sized against the original delay and reduced by whatever
        has already been clawed back, so running the cycle repeatedly cannot
        keep trimming the same halts until the delay disappears.
        """
        decisions = []
        for booking in observation:
            trimmable_halts = max(booking.train.scheduled_halts - 2, 0)
            possible = int(trimmable_halts * MINUTES_SAVED_PER_HALT)
            budget = int(booking.delay_minutes * MAX_RECOVERY_SHARE)
            remaining_budget = budget - booking.recovered_minutes

            recoverable = min(possible, remaining_budget)

            if recoverable > 0:
                decisions.append({"booking": booking, "recovered": recoverable})
        return decisions

    def act(self, decision):
        """Pull the expected departure earlier by the minutes recovered."""
        adjusted = []

        for item in decision:
            booking = item["booking"]
            recovered = item["recovered"]

            booking.expected_departure = add_minutes(
                booking.expected_departure, -recovered
            )
            booking.recovered_minutes += recovered
            booking.save()

            self.log(
                f"{booking.train.name} delayed. Halts trimmed at minor stations; "
                f"{recovered} minutes recovered, now due {booking.expected_departure} "
                f"({booking.current_delay} min late).",
                severity="medium",
            )
            adjusted.append(
                {
                    "train": booking.train.name,
                    "recovered": recovered,
                    "newDeparture": booking.expected_departure,
                }
            )

        return {"examined": len(decision), "adjusted": adjusted}
