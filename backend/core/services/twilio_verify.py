"""Twilio Verify wrapper for passenger phone verification.

Verify - not a hand-rolled SMS-plus-random-code system - owns OTP
generation, expiry, rate limiting and attempt limits. This module only
starts and checks a verification against the Service SID configured in the
environment.

Simulated unless TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and
TWILIO_VERIFY_SERVICE_SID are all set - the same convention
core.agents.manager_agent.place_call already uses, so local dev and CI never
need real Twilio credentials. In simulated mode, the code "000000" is always
accepted; anything else is rejected.

One-time setup before this can go live: create a Verify Service in the
Twilio Console (Verify -> Services -> Create new service) or via
`client.verify.v2.services.create(friendly_name="RailBot BD")`, then put its
SID (starts with "VA") in TWILIO_VERIFY_SERVICE_SID.
"""

import os

SIMULATED_CODE = "000000"


def _configured():
    return all(
        os.environ.get(name)
        for name in (
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN",
            "TWILIO_VERIFY_SERVICE_SID",
        )
    )


def _service():
    # Imported lazily so the `twilio` package is only required once real
    # credentials are actually configured.
    from twilio.rest import Client

    client = Client(
        os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"]
    )
    return client.verify.v2.services(os.environ["TWILIO_VERIFY_SERVICE_SID"])


def start_verification(phone_number):
    """Send an OTP to phone_number. Returns a short status string."""
    if not _configured():
        return "simulated-pending"

    verification = _service().verifications.create(to=phone_number, channel="sms")
    return verification.status


def check_verification(phone_number, code):
    """Check a submitted code. Returns True if it was approved."""
    if not _configured():
        return code == SIMULATED_CODE

    check = _service().verification_checks.create(to=phone_number, code=code)
    return check.status == "approved"
