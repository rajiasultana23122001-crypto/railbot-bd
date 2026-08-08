"""Passenger and Authority authentication endpoints.

Passenger signup is NID + phone + password; the phone is then OTP-confirmed
through Twilio Verify before the account can log in (Verify owns expiry,
rate limiting and attempt limits - no hand-rolled code system). Authority
signup is phone + a pre-issued Authority ID + password; the ID must already
exist in the AuthorityID table and not be claimed yet - nothing here
generates or accepts an arbitrary ID. Login is shared: phone + password,
role read back off the account rather than asked for.
"""

import json
import re

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.authtoken.models import Token

from .models import AuthorityID, Passenger, Profile
from .services.twilio_verify import check_verification, start_verification

# Accepts the 10-digit (old) or 17-digit (new) Bangladesh NID format, digits
# only. Nothing else is accepted - no dashes, no letters.
NID_RE = re.compile(r"^(\d{10}|\d{17})$")


def _json_body(request):
    """Parse the request body as JSON, or return a 400 response to send back."""
    try:
        return json.loads(request.body or b"{}"), None
    except json.JSONDecodeError:
        return None, JsonResponse({"error": "Body must be JSON."}, status=400)


def _issue_token(user):
    """A fresh token for this user, replacing any old one (rotate on login)."""
    Token.objects.filter(user=user).delete()
    return Token.objects.create(user=user).key


@csrf_exempt
@require_http_methods(["POST"])
def passenger_signup(request):
    """Register NID + phone + password, then send the first OTP.

    The account exists as soon as this returns, but Profile.is_phone_verified
    stays False - and login is refused - until verify_signup succeeds.
    """
    payload, error = _json_body(request)
    if error:
        return error

    phone = str(payload.get("phone_number", "")).strip()
    nid = str(payload.get("nid_number", "")).strip()
    password = str(payload.get("password", ""))

    if not phone:
        return JsonResponse({"error": "Phone number is required."}, status=400)
    if not NID_RE.match(nid):
        return JsonResponse(
            {"error": "NID must be exactly 10 or 17 digits, numbers only."},
            status=400,
        )
    if not password:
        return JsonResponse({"error": "Password is required."}, status=400)

    if User.objects.filter(username=phone).exists():
        return JsonResponse(
            {"error": "This phone number already has an account."}, status=409
        )
    if Profile.objects.filter(nid_number=nid).exists():
        return JsonResponse({"error": "This NID is already registered."}, status=409)

    try:
        with transaction.atomic():
            user = User.objects.create_user(username=phone, password=password)
            Profile.objects.create(
                user=user,
                role=Profile.ROLE_PASSENGER,
                phone_number=phone,
                nid_number=nid,
                # If a seat was already booked at the counter against this
                # number, that record belongs to this account from the start.
                # Only an unclaimed one: the link is one-to-one, so a record
                # some other account already holds is left alone rather than
                # taken. No match is normal - Profile.own_bookings falls back
                # to matching on the phone number itself.
                passenger=Passenger.objects.filter(
                    phone=phone, profile__isnull=True
                ).first(),
            )
    except IntegrityError:
        # Lost a race against another signup with the same phone or NID
        # between the checks above and this write.
        return JsonResponse(
            {"error": "This phone number or NID is already registered."}, status=409
        )

    start_verification(phone)

    return JsonResponse(
        {
            "message": "OTP sent. Confirm it to activate the account.",
            "phoneNumber": phone,
        },
        status=201,
    )


@csrf_exempt
@require_http_methods(["POST"])
def passenger_verify_signup(request):
    """Confirm the OTP sent at signup. Activates the account for login."""
    payload, error = _json_body(request)
    if error:
        return error

    phone = str(payload.get("phone_number", "")).strip()
    code = str(payload.get("code", "")).strip()

    profile = Profile.objects.filter(
        phone_number=phone, role=Profile.ROLE_PASSENGER
    ).first()
    if profile is None:
        return JsonResponse(
            {"error": "No signup in progress for this number."}, status=404
        )

    if not check_verification(phone, code):
        return JsonResponse({"error": "Incorrect or expired code."}, status=400)

    profile.is_phone_verified = True
    profile.save()

    return JsonResponse({"message": "Phone verified. You can now sign in."})


@csrf_exempt
@require_http_methods(["POST"])
def authority_signup(request):
    """Register phone + a pre-issued Authority ID + password.

    Active immediately - the ID itself is the proof of authorization, so
    there is no separate verification step the way passenger signup has one.
    """
    payload, error = _json_body(request)
    if error:
        return error

    phone = str(payload.get("phone_number", "")).strip()
    authority_id_code = str(payload.get("authority_id", "")).strip()
    password = str(payload.get("password", ""))

    if not phone:
        return JsonResponse({"error": "Phone number is required."}, status=400)
    if not authority_id_code:
        return JsonResponse({"error": "Authority ID is required."}, status=400)
    if not password:
        return JsonResponse({"error": "Password is required."}, status=400)

    if User.objects.filter(username=phone).exists():
        return JsonResponse(
            {"error": "This phone number already has an account."}, status=409
        )

    authority_id = AuthorityID.objects.filter(code=authority_id_code).first()
    if authority_id is None:
        return JsonResponse(
            {"error": "Authority ID not recognized. Check the ID issued to you."},
            status=400,
        )
    if authority_id.is_claimed:
        return JsonResponse(
            {"error": "This Authority ID has already been claimed."}, status=409
        )

    try:
        with transaction.atomic():
            user = User.objects.create_user(username=phone, password=password)
            Profile.objects.create(
                user=user,
                role=Profile.ROLE_AUTHORITY,
                phone_number=phone,
                authority_id=authority_id,
            )
    except IntegrityError:
        # Lost a race against another signup with the same phone, or another
        # signup that claimed this exact Authority ID a moment earlier.
        return JsonResponse(
            {
                "error": "This phone number already has an account, or that "
                "Authority ID was just claimed by someone else."
            },
            status=409,
        )

    return JsonResponse({"message": "Account created. You can now sign in."}, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def login(request):
    """Shared login for both roles: phone + password. Role comes off the account."""
    payload, error = _json_body(request)
    if error:
        return error

    phone = str(payload.get("phone_number", "")).strip()
    password = str(payload.get("password", ""))

    user = authenticate(request, username=phone, password=password)
    if user is None:
        # Deliberately the same message whether the phone doesn't exist or
        # the password is wrong - telling those apart lets someone probe
        # which phone numbers have accounts.
        return JsonResponse(
            {"error": "Invalid phone number or password."}, status=401
        )

    profile = getattr(user, "profile", None)
    if profile is None:
        return JsonResponse({"error": "This account has no role set up."}, status=403)

    if profile.role == Profile.ROLE_PASSENGER and not profile.is_phone_verified:
        return JsonResponse(
            {"error": "Verify your phone number before signing in."}, status=403
        )

    return JsonResponse(
        {
            "token": _issue_token(user),
            "role": profile.role,
            "phoneNumber": profile.phone_number,
        }
    )
