"""Passenger and Station Manager authentication endpoints.

Passenger identity is phone + NID, activated by a Twilio Verify OTP. Station
Manager accounts are never created here - see
`manage.py create_manager`.
"""

import json
import re

from django.contrib.auth.hashers import check_password
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .auth import new_token
from .models import Passenger, StationManager
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


@csrf_exempt
@require_http_methods(["POST"])
def passenger_signup(request):
    """Register phone + NID, then send the first OTP.

    The account exists in the database as soon as this returns, but stays
    unusable (is_phone_verified stays False) until verify_signup succeeds.
    """
    payload, error = _json_body(request)
    if error:
        return error

    name = str(payload.get("name", "")).strip()
    phone = str(payload.get("phone_number", "")).strip()
    nid = str(payload.get("nid_number", "")).strip()

    if not name:
        return JsonResponse({"error": "Name is required."}, status=400)
    if not phone:
        return JsonResponse({"error": "Phone number is required."}, status=400)
    if not NID_RE.match(nid):
        return JsonResponse(
            {"error": "NID must be exactly 10 or 17 digits, numbers only."},
            status=400,
        )
    if Passenger.objects.filter(phone=phone).exists():
        return JsonResponse(
            {"error": "This phone number already has an account."}, status=409
        )
    if Passenger.objects.filter(nid_number=nid).exists():
        return JsonResponse({"error": "This NID is already registered."}, status=409)

    Passenger.objects.create(name=name, phone=phone, nid_number=nid)
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
    """Confirm the OTP sent at signup. Activates the account and issues a token."""
    payload, error = _json_body(request)
    if error:
        return error

    phone = str(payload.get("phone_number", "")).strip()
    code = str(payload.get("code", "")).strip()

    passenger = Passenger.objects.filter(phone=phone).first()
    if passenger is None:
        return JsonResponse(
            {"error": "No signup in progress for this number."}, status=404
        )

    if not check_verification(phone, code):
        return JsonResponse({"error": "Incorrect or expired code."}, status=400)

    passenger.is_phone_verified = True
    passenger.auth_token = new_token()
    passenger.save()

    return JsonResponse(
        {
            "token": passenger.auth_token,
            "passenger": {"id": passenger.id, "name": passenger.name},
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def passenger_login_request_otp(request):
    """OTP login, step 1: send a fresh code to an already-verified number."""
    payload, error = _json_body(request)
    if error:
        return error

    phone = str(payload.get("phone_number", "")).strip()
    passenger = Passenger.objects.filter(phone=phone, is_phone_verified=True).first()
    if passenger is None:
        return JsonResponse({"error": "No verified account for this number."}, status=404)

    start_verification(phone)
    return JsonResponse({"message": "OTP sent."})


@csrf_exempt
@require_http_methods(["POST"])
def passenger_login_verify_otp(request):
    """OTP login, step 2: confirm the code and issue a fresh token.

    The token is rotated on every successful login, so signing in from a new
    place invalidates whatever token was issued before.
    """
    payload, error = _json_body(request)
    if error:
        return error

    phone = str(payload.get("phone_number", "")).strip()
    code = str(payload.get("code", "")).strip()

    passenger = Passenger.objects.filter(phone=phone, is_phone_verified=True).first()
    if passenger is None:
        return JsonResponse({"error": "No verified account for this number."}, status=404)

    if not check_verification(phone, code):
        return JsonResponse({"error": "Incorrect or expired code."}, status=400)

    passenger.auth_token = new_token()
    passenger.save()

    return JsonResponse(
        {
            "token": passenger.auth_token,
            "passenger": {"id": passenger.id, "name": passenger.name},
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def manager_login(request):
    """Station Manager login: username + password, issues a bearer token."""
    payload, error = _json_body(request)
    if error:
        return error

    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", ""))

    manager = StationManager.objects.filter(username=username).first()
    if manager is None or not check_password(password, manager.password_hash):
        return JsonResponse({"error": "Invalid username or password."}, status=401)

    manager.auth_token = new_token()
    manager.save()

    return JsonResponse({"token": manager.auth_token, "username": manager.username})
