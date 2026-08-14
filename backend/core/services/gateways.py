"""Adapter - one interface over message providers that share nothing.

sms.net.bd wants a GET with api_key, msg and to as query parameters, and a
number in 880-prefixed digits. Twilio wants a POST with basic auth, JSON,
and E.164. Firebase, when push notifications arrive in Week 11, wants a
device token and no phone number at all.

The Manager Agent should not know any of that. It has a passenger and
something to tell them; how that reaches a handset is somebody else's
problem. MessageGateway is the interface the agent is written against, and
each adapter translates it into whatever the provider underneath expects.

Adding a provider means adding an adapter. It does not mean touching the
agent, which is the point.
"""

import os
import re

import requests

SMS_NET_BD_ENDPOINT = "https://api.sms.net.bd/sendsms"
REQUEST_TIMEOUT_SECONDS = 10


class MessageGateway:
    """The interface the Manager Agent is written against.

    send() returns (delivered, detail) and never raises. The agent uses
    `delivered` to decide whether to mark a passenger as told, and a gateway
    that raised instead would take the whole cycle down over one unreachable
    provider - losing the Resource and Advisor agents queued behind it. The
    detail string goes into the audit trail either way.
    """

    name = "gateway"

    def send(self, phone, message):
        raise NotImplementedError

    def is_configured(self):
        """Whether this gateway has what it needs to reach a real handset."""
        raise NotImplementedError


class SmsNetBdAdapter(MessageGateway):
    """Adapts sms.net.bd's HTTP API to MessageGateway."""

    name = "sms.net.bd"

    def __init__(self, api_key=None, endpoint=SMS_NET_BD_ENDPOINT):
        # Read at construction rather than at import, so a test can build one
        # with an explicit key without touching the environment.
        self._api_key = api_key if api_key is not None else os.environ.get(
            "SMS_NET_BD_API_KEY"
        )
        self._endpoint = endpoint

    def is_configured(self):
        return bool(self._api_key)

    @staticmethod
    def normalize(phone):
        """Reduce a stored number to the shape sms.net.bd expects.

        Accepts the messy forms a number might actually be stored in -
        "+8801700000000", "880 1700-000000", "01700000000" - and returns the
        880-prefixed digits-only form. This is the translation half of the
        adapter: the interface deals in phone numbers, the provider deals in
        one particular spelling of them.
        """
        digits = re.sub(r"\D", "", phone or "")
        if digits.startswith("880"):
            return digits
        if digits.startswith("0"):
            return "880" + digits[1:]
        # A 10-digit local number with no leading 0 - uncommon, but cheap to
        # handle rather than send upstream to be silently rejected.
        if len(digits) == 10:
            return "880" + digits
        return digits

    def send(self, phone, message):
        to = self.normalize(phone)
        try:
            response = requests.get(
                self._endpoint,
                params={"api_key": self._api_key, "msg": message, "to": to},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            return False, f"SMS to {to} failed: {exc}"
        return True, f"SMS sent to {to}"


class SimulatedGateway(MessageGateway):
    """Reports success without sending anything.

    Used when no provider is configured, which is every local checkout and
    every CI run. It reports delivered so that the rest of the cycle behaves
    exactly as it would in production - the Manager Agent records the
    passenger as notified and does not retry them next cycle. A simulated
    gateway that reported failure would exercise the retry path forever and
    tell you nothing about the normal one.
    """

    name = "simulated"

    def is_configured(self):
        return True

    def send(self, phone, message):
        return True, f"simulated SMS to {SmsNetBdAdapter.normalize(phone)}"


def default_gateway():
    """The gateway to use when nobody has specified one.

    Real provider if it has credentials, simulation otherwise. This is the
    only place that decision is made, so nothing else in the codebase has to
    branch on whether an API key happens to be set.
    """
    sms = SmsNetBdAdapter()
    return sms if sms.is_configured() else SimulatedGateway()
