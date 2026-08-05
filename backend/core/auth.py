"""Bearer-token auth for the passenger and station-manager APIs.

No Django session, no DRF - deliberately, since neither was already in use
(see core/models.py). A token is issued at signup/login and sent back as
`Authorization: Bearer <token>` on every call that needs it. Two roles live
in two separate tables (Passenger, StationManager), so "which decorator
guards this route" already answers the role question - there's no shared
role column to keep in sync.
"""

import secrets
from functools import wraps

from django.http import JsonResponse

from .models import Passenger, StationManager


def new_token():
    """A fresh opaque bearer token. 64 hex characters, effectively unguessable."""
    return secrets.token_hex(32)


def _bearer_token(request):
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    return header[len("Bearer ") :].strip() or None


def passenger_required(view):
    """Only a signed-in passenger may call the wrapped view.

    Attaches the Passenger row as request.passenger for the view to use.
    """

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        token = _bearer_token(request)
        passenger = token and Passenger.objects.filter(auth_token=token).first()
        if not passenger:
            return JsonResponse({"error": "Sign in required."}, status=401)
        request.passenger = passenger
        return view(request, *args, **kwargs)

    return wrapped


def station_manager_required(view):
    """Only a signed-in Station Manager may call the wrapped view.

    Attaches the StationManager row as request.station_manager.
    """

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        token = _bearer_token(request)
        manager = token and StationManager.objects.filter(auth_token=token).first()
        if not manager:
            return JsonResponse({"error": "Station manager sign-in required."}, status=401)
        request.station_manager = manager
        return view(request, *args, **kwargs)

    return wrapped
