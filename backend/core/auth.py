"""Role-based auth for the passenger and authority APIs.

Uses DRF's own Token model (rest_framework.authtoken) for token storage and
generation - real, well-tested random keys, one per Django User - but checks
it by hand in a plain decorator rather than switching views over to DRF's
APIView/serializer machinery, since nothing else in this project uses DRF.
"Authorization: Bearer <token>" is this project's own header convention
(DRF's built-in TokenAuthentication class would expect "Token <token>"
instead, but that class is never invoked here - only its Token model is).

Role lives on Profile, one per User, so "which decorator guards this route"
and "what does request.profile.role say" always agree.
"""

from functools import wraps

from django.http import JsonResponse
from rest_framework.authtoken.models import Token

from .models import Profile


def _bearer_token(request):
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    return header[len("Bearer ") :].strip() or None


def _authenticated_user(request):
    """The Django User for a valid bearer token, or None."""
    key = _bearer_token(request)
    if not key:
        return None
    token = Token.objects.select_related("user__profile").filter(key=key).first()
    return token.user if token else None


def _require_role(role, no_token_message, wrong_role_message):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            user = _authenticated_user(request)
            if user is None:
                return JsonResponse({"error": no_token_message}, status=401)

            profile = getattr(user, "profile", None)
            if profile is None or profile.role != role:
                return JsonResponse({"error": wrong_role_message}, status=403)

            request.user = user
            request.profile = profile
            return view(request, *args, **kwargs)

        return wrapped

    return decorator


passenger_required = _require_role(
    Profile.ROLE_PASSENGER,
    no_token_message="Sign in required.",
    wrong_role_message="This is a passenger-only endpoint.",
)

authority_required = _require_role(
    Profile.ROLE_AUTHORITY,
    no_token_message="Authority sign-in required.",
    wrong_role_message="This is an authority-only endpoint.",
)


def any_role_required(view):
    """Signed in as either role - used for the timetable, open to both."""

    @wraps(view)
    def wrapped(request, *args, **kwargs):
        user = _authenticated_user(request)
        profile = getattr(user, "profile", None) if user else None
        if profile is None:
            return JsonResponse({"error": "Sign in required."}, status=401)

        request.user = user
        request.profile = profile
        return view(request, *args, **kwargs)

    return wrapped
