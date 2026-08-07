"""Manager Agent - tells passengers about delays without being asked.

Observes journeys that have slipped, reasons about what each passenger needs
to hear, and sends the text. send_sms() is the only function that talks to
sms.net.bd - everything that decides who to message and what to say stays
exactly as it was when this used to place a (simulated) voice call.
"""

import os
import re

import requests

from core.models import Booking

from .base import BaseAgent

SMS_NET_BD_ENDPOINT = "https://api.sms.net.bd/sendsms"


def normalize_bd_phone(phone):
    """Reduce a stored phone number to sms.net.bd's expected shape.

    Accepts the messy forms a phone number might actually be stored in -
    "+8801700000000", "880 1700-000000", "01700000000" - and returns the
    880-prefixed, digits-only form (e.g. "8801700000000"). sms.net.bd also
    accepts the bare 01X form, but standardising on one shape here means
    nothing downstream has to branch on which one it got.
    """
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("880"):
        return digits
    if digits.startswith("0"):
        return "880" + digits[1:]
    # A 10-digit local number with no leading 0 at all - uncommon, but cheap
    # to handle rather than send it upstream to be silently rejected.
    if len(digits) == 10:
        return "880" + digits
    return digits


def send_sms(phone, message):
    """Send one SMS through sms.net.bd.

    Simulated unless SMS_NET_BD_API_KEY is set, matching how the Twilio
    voice call this replaced used to behave without credentials. Returns
    (sent, detail) rather than raising - detail is a short string for the
    audit trail either way, and `sent` is what act() uses to decide whether
    to mark this passenger as notified or leave it for the next cycle to
    retry.
    """
    to = normalize_bd_phone(phone)
    api_key = os.environ.get("SMS_NET_BD_API_KEY")

    if not api_key:
        return True, f"simulated SMS to {to}"

    try:
        response = requests.get(
            SMS_NET_BD_ENDPOINT,
            params={"api_key": api_key, "msg": message, "to": to},
            timeout=10,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        return False, f"SMS to {to} failed: {exc}"

    return True, f"SMS sent to {to}"


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
            for booking in Booking.objects.filter(status="delayed").select_related(
                "train", "passenger"
            )
            if booking.notified_departure != booking.expected_departure
        ]

    def reason(self, observation):
        """Compose what each passenger should be texted.

        Kept short on purpose - this is an SMS, not the spoken script it
        replaced, and a long message risks splitting across multiple
        segments for no benefit.
        """
        decisions = []
        for booking in observation:
            # A passenger who was already texted a time is being corrected,
            # not told for the first time, and the message should say so.
            is_update = booking.notified_departure is not None

            opening = (
                "RailBot: updated delay for"
                if is_update
                else "RailBot: your train"
            )
            message = (
                f"{opening} {booking.train.name} to {booking.train.destination} - "
                f"now {booking.current_delay} min late, departs "
                f"{booking.expected_departure} from platform {booking.platform}."
            )
            decisions.append(
                {"booking": booking, "message": message, "isUpdate": is_update}
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

            booking.agent_note = (
                "Manager Agent texted you the updated departure time. "
                if item["isUpdate"]
                else f"Manager Agent texted you about the "
                f"{booking.current_delay} minute delay. "
            ) + (
                f"Your train now departs at {booking.expected_departure} "
                f"from platform {booking.platform}."
            )
            booking.save()

            kind = "Updated time" if item["isUpdate"] else "Delay notice"
            self.log(
                f"{kind} texted to {passenger.name} for {booking.train.name} - "
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

        return {"examined": len(decision), "called": called}
