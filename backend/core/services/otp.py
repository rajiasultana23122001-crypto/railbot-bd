"""OTP verification for passenger phone numbers, sent through sms.net.bd.

Twilio Verify used to own OTP generation, expiry, rate limiting and attempt
limits end-to-end - see the module this replaced, core/services/twilio_verify.py
in history. sms.net.bd only sends a text message, so this module and
core.models.OTPCode now do that work by hand:

- a 6-digit code from `secrets` (crypto-secure, not `random`)
- CODE_VALIDITY minutes before a code expires
- MAX_ATTEMPTS wrong guesses before a code is locked out
- RESEND_COOLDOWN before a fresh SMS is sent to the same number, so a
  passenger mashing "resend" does not burn through SMS credit
- the code is hashed (Django's password hasher) before it is stored, never
  kept in plaintext

Simulated whenever SMS_NET_BD_API_KEY is unset - the same convention
core.agents.manager_agent.send_sms already uses for delay texts. In that
mode the code is always "000000", matching the old Twilio simulated
behaviour, so local dev and CI never need a real key.
"""

import os
import secrets
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone

from core.agents.manager_agent import send_sms
from core.models import OTPCode

SIMULATED_CODE = "000000"

CODE_VALIDITY = timedelta(minutes=5)
MAX_ATTEMPTS = 5
RESEND_COOLDOWN = timedelta(minutes=1)


def _configured():
    return bool(os.environ.get("SMS_NET_BD_API_KEY"))


def _generate_code():
    if not _configured():
        return SIMULATED_CODE
    return "".join(secrets.choice("0123456789") for _ in range(6))


def start_verification(phone_number):
    """Send an OTP to phone_number. Returns a short status string.

    Skips sending (and reuses the still-valid code already on file) if one
    was sent to this number under a minute ago - that is the rate limit,
    not a rejection of the request.
    """
    cutoff = timezone.now() - RESEND_COOLDOWN
    pending = (
        OTPCode.objects.filter(phone_number=phone_number, is_used=False)
        .order_by("-created_at")
        .first()
    )
    if pending and pending.created_at >= cutoff and pending.attempts < MAX_ATTEMPTS:
        return "throttled"

    code = _generate_code()
    OTPCode.objects.create(phone_number=phone_number, code_hash=make_password(code))
    send_sms(
        phone_number,
        f"RailBot: your verification code is {code}. It expires in 5 minutes.",
    )
    return "sent"


def check_verification(phone_number, code):
    """Check a submitted code. Returns True if it was approved.

    Matches against the most recent unexpired, unused code for this number.
    A wrong guess still counts against MAX_ATTEMPTS even when it is the
    right code but the attempt budget is already spent - once locked out,
    the code is dead and start_verification has to be called again.
    """
    cutoff = timezone.now() - CODE_VALIDITY
    otp = (
        OTPCode.objects.filter(
            phone_number=phone_number, is_used=False, created_at__gte=cutoff
        )
        .order_by("-created_at")
        .first()
    )
    if otp is None or otp.attempts >= MAX_ATTEMPTS:
        return False

    otp.attempts += 1
    approved = check_password(code, otp.code_hash)
    if approved:
        otp.is_used = True
    otp.save()
    return approved
