"""Manager Agent - tells passengers about delays without being asked.

Observes journeys that have slipped, reasons about what each passenger needs
to hear, and sends the text.

Two things this agent deliberately does not know: how a message reaches a
handset, and how a message is worded. The first is a MessageGateway
(core.services.gateways), the second a NotificationStrategy
(core.services.message_strategy). Adding a channel or a new kind of notice
is a new class in one of those modules, not another branch in here.
"""

from core.models import Booking
from core.services.gateways import SmsNetBdAdapter, default_gateway
from core.services.message_strategy import strategy_for

from .base import BaseAgent


def normalize_bd_phone(phone):
    """Reduce a stored phone number to sms.net.bd's expected shape.

    Kept as a module-level name because callers and tests import it. The
    translation itself now lives with the adapter that needs it.
    """
    return SmsNetBdAdapter.normalize(phone)


def send_sms(phone, message, gateway=None):
    """Send one SMS through whichever gateway is configured.

    Returns (sent, detail) rather than raising - detail is a short string for
    the audit trail either way, and `sent` is what act() uses to decide
    whether to mark this passenger as notified or leave it for the next cycle
    to retry.

    Kept as a module-level function, rather than folded into the agent, so
    that the existing tests patching this name still work.
    """
    return (gateway or default_gateway()).send(phone, message)


class ManagerAgent(BaseAgent):
    name = "Manager Agent"

    def observe(self):
        """Delayed journeys where the passenger is holding a stale time.

        Comparing against the time last read out - rather than merely whether
        a message went out - means a passenger gets texted again when the
        Scheduler Agent moves their departure, and is left alone when nothing
        changed.
        """
        return [
            booking
            for booking in Booking.objects.filter(status="delayed")
            .exclude(booking_status="cancelled")
            .select_related("train", "passenger")
            if booking.notified_departure != booking.expected_departure
        ]

    def reason(self, observation):
        """Compose what each passenger should be texted.

        The wording is a strategy chosen from what the passenger currently
        holds - first news, or a correction to a time that has moved. This
        method picks one and asks it; it does not know how either is worded.
        """
        decisions = []
        for booking in observation:
            strategy = strategy_for(booking)
            decisions.append(
                {
                    "booking": booking,
                    "message": strategy.compose_sms(booking),
                    "strategy": strategy,
                }
            )
        return decisions

    def act(self, decision):
        """Text each passenger and record it against the journey.

        A failed send does not update notified_departure or agent_note - the
        booking looks untouched to the next cycle, so it gets retried rather
        than silently treated as if the passenger already knows.
        """
        called = []

        for item in decision:
            booking = item["booking"]
            strategy = item["strategy"]
            passenger = booking.passenger

            sent, outcome = send_sms(passenger.phone, item["message"])

            if not sent:
                self.log(
                    f"SMS to {passenger.name} for {booking.train.name} failed "
                    f"- will retry next cycle ({outcome}).",
                    severity="high",
                )
                continue

            # Remember what was said, so the next cycle knows whether this
            # passenger still holds the right time.
            booking.notified_departure = booking.expected_departure
            booking.agent_note = strategy.compose_note(booking)
            booking.save()

            self.log(
                f"{strategy.log_label} texted to {passenger.name} for "
                f"{booking.train.name} - now departing "
                f"{booking.expected_departure} ({outcome}).",
                severity="info",
            )
            called.append(
                {
                    "passenger": passenger.name,
                    "train": booking.train.name,
                    "departure": booking.expected_departure,
                }
            )

        return {"examined": len(decision), "called": called}
