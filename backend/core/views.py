"""RailBot BD - REST endpoints.

Serves the data behind both dashboards. The JSON shapes come straight from each
model's to_dict(), so the React components need no changes.
"""

import json
from datetime import datetime

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .agents import run_cycle
from .agents.scheduler_agent import add_minutes
from .auth import any_role_required, authority_required, passenger_required
from .models import AgentLog, Arrival, Booking, Platform, Station, Train


@require_http_methods(["GET"])
def health(request):
    """Quick check that the API is alive."""
    return JsonResponse({"status": "ok", "service": "railbot-bd"})


@passenger_required
@require_http_methods(["GET"])
def journeys(request):
    """Every booked journey, for the Passenger Dashboard. Passenger-only.

    Returns every booking in the system, not only the signed-in passenger's
    own - Profile.passenger exists for that link but nothing wires it up to
    this endpoint yet, so scoping by identity is a follow-up, not done here.
    """
    bookings = Booking.objects.select_related("train", "passenger").all()

    # A journey carries an agent note exactly when an agent has already acted
    # on it - a call placed, or a risk flagged. That is what the passenger
    # means by "alerts received".
    alerts_received = sum(1 for b in bookings if b.agent_note)

    return JsonResponse(
        {
            "journeys": [b.to_dict() for b in bookings],
            "alertsReceived": alerts_received,
        }
    )


@authority_required
@require_http_methods(["GET"])
def station(request, code):
    """Everything the Station Master Panel shows for one station.

    Platforms, arrivals and logs come back together so the meters can never
    disagree with the alerts printed beside them. Authority-only: this is
    the operator's board, not something a passenger's session can reach.
    """
    try:
        found = Station.objects.get(code=code.upper())
    except Station.DoesNotExist:
        return JsonResponse({"error": f"No station with code {code}"}, status=404)

    platforms = Platform.objects.filter(station=found)
    arrivals = Arrival.objects.filter(station=found).select_related("train")
    # Newest decision first, which is how the panel reads.
    logs = AgentLog.objects.order_by("-id")

    return JsonResponse(
        {
            "station": found.to_dict(),
            "platforms": [p.to_dict() for p in platforms],
            "arrivals": [a.to_dict() for a in arrivals],
            "agentAlerts": [log.to_dict() for log in logs],
        }
    )


@authority_required
@require_http_methods(["GET"])
def trains(request):
    """Trains a delay can be reported against - those someone has booked.

    Authority-only: this feeds the Report a Delay picker, an operator tool.
    """
    bookings = Booking.objects.select_related("train").all()
    return JsonResponse(
        {
            "trains": [
                {
                    "trainNo": b.train.number,
                    "name": b.train.name,
                    "destination": b.train.destination,
                    "status": b.status,
                    "scheduledDeparture": b.scheduled_departure,
                }
                for b in bookings
            ]
        }
    )


@any_role_required
@require_http_methods(["GET"])
def train_info(request):
    """Every train in the network - the Timetable, open to either role."""
    all_trains = Train.objects.order_by("number")
    return JsonResponse({"trains": [t.to_dict() for t in all_trains]})


@authority_required
@require_http_methods(["GET"])
def agent_logs(request):
    """The full audit trail, newest first - read by the Advisor Agent.

    Authority-only: this is the same audit trail the Station Master Panel's
    agent log already surfaces, not passenger-facing data.
    """
    logs = AgentLog.objects.order_by("-id")
    return JsonResponse({"logs": [log.to_dict() for log in logs]})


# csrf_exempt because this API is called by the React dev server, not by a
# Django-rendered form carrying a CSRF token.
@csrf_exempt
@authority_required
@require_http_methods(["POST"])
def report_delay(request):
    """Report a train as running late, then let the agents respond.

    This is the operator-facing entry point: a station master enters what has
    happened, and the agents work out what to do about it. Authority-only,
    same reasoning as `station` above.
    """
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Body must be JSON."}, status=400)

    train_no = str(payload.get("trainNo", "")).strip()
    raw_minutes = payload.get("minutes")

    if not train_no:
        return JsonResponse({"error": "Pick a train first."}, status=400)

    try:
        minutes = int(raw_minutes)
    except (TypeError, ValueError):
        return JsonResponse(
            {"error": "Delay must be a whole number of minutes."}, status=400
        )

    if not 1 <= minutes <= 300:
        return JsonResponse(
            {"error": "Delay must be between 1 and 300 minutes."}, status=400
        )

    booking = (
        Booking.objects.select_related("train").filter(train__number=train_no).first()
    )
    if booking is None:
        return JsonResponse(
            {"error": f"No booked journey on train {train_no}."}, status=404
        )

    # Record the delay as freshly reported: nothing recovered yet, and the
    # passenger has not been told, so the agents have work to do.
    booking.status = "delayed"
    booking.delay_minutes = minutes
    booking.recovered_minutes = 0
    booking.expected_departure = add_minutes(booking.scheduled_departure, minutes)
    booking.notified_departure = None
    booking.agent_note = None
    booking.save()

    # Read these before the agents run: afterwards expected_departure has
    # already been pulled earlier by the Scheduler, and reporting that back as
    # "the delay you entered" would not add up.
    train_name = booking.train.name
    scheduled = booking.scheduled_departure
    departure_after_delay = booking.expected_departure

    try:
        results = run_cycle()
    except FileNotFoundError as exc:
        return JsonResponse({"error": str(exc)}, status=503)

    booking.refresh_from_db()

    return JsonResponse(
        {
            "reported": {
                "train": train_name,
                "minutes": minutes,
                "scheduledDeparture": scheduled,
                "departureAfterDelay": departure_after_delay,
            },
            "settledDeparture": booking.expected_departure,
            "ranAt": datetime.now().strftime("%H:%M"),
            "results": results,
        }
    )


@csrf_exempt
@authority_required
@require_http_methods(["POST"])
def run_agents(request):
    """Run one Observe - Reason - Act cycle across all five agents.

    Returns what each agent did, so the dashboard can show the cycle happening
    rather than only its after-effects. Authority-only: triggering a cycle on
    demand is an operator action, not a passenger one.
    """
    try:
        results = run_cycle()
    except FileNotFoundError as exc:
        # The Risk Agent's model has not been trained yet.
        return JsonResponse({"error": str(exc)}, status=503)

    return JsonResponse(
        {"ranAt": datetime.now().strftime("%H:%M"), "results": results}
    )
