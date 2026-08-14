"""RailBot BD - REST endpoints.

Serves the data behind both dashboards. The JSON shapes come straight from each
model's to_dict(), so the React components need no changes.
"""

import json
from datetime import datetime

from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .facade import DelayReportError, RailBotFacade
from .auth import any_role_required, authority_required, passenger_required
from .data.network import SEAT_CLASSES
from .models import (
    AgentLog,
    Arrival,
    Booking,
    BookingPassenger,
    Passenger,
    Platform,
    Station,
    Train,
    generate_pnr,
)
from .services.booking import available_seats, duration_minutes, leg_for


@require_http_methods(["GET"])
def health(request):
    """Quick check that the API is alive."""
    return JsonResponse({"status": "ok", "service": "railbot-bd"})


@passenger_required
@require_http_methods(["GET"])
def journeys(request):
    """The signed-in passenger's own journeys, for the Passenger Dashboard.

    Scoped by who is asking, not merely by role: holding a valid passenger
    token proves you are *a* passenger, which is not a reason to read every
    other passenger's travel plans. Profile decides which bookings are this
    account's - see Profile.own_bookings.
    """
    bookings = request.profile.own_bookings().select_related("train", "passenger")

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
    bookings = Booking.objects.exclude(booking_status="cancelled").select_related("train")
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

    The sequence itself - validate, mark every booking, keep the arrivals
    board in step, run the five agents in order, and read the reported figures
    before the Scheduler moves them - lives in RailBotFacade. It has to happen
    in that order, and a view is the wrong place to be the only thing that
    knows it: a management command or an operations feed reporting a delay
    would otherwise have to reimplement it or go through HTTP to reach it.
    """
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Body must be JSON."}, status=400)

    try:
        result = RailBotFacade.report_delay(
            payload.get("trainNo"), payload.get("minutes")
        )
    except DelayReportError as exc:
        # The facade decides both the message and the status - a bad train
        # number is a 404, a bad minutes value is a 400 - so the view does not
        # hold a second copy of that mapping.
        return JsonResponse({"error": exc.message}, status=exc.status)
    except FileNotFoundError as exc:
        # The Risk Agent's model has not been trained yet.
        return JsonResponse({"error": str(exc)}, status=503)

    return JsonResponse(result)


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
        return JsonResponse(RailBotFacade.run_agent_cycle())
    except FileNotFoundError as exc:
        # The Risk Agent's model has not been trained yet.
        return JsonResponse({"error": str(exc)}, status=503)


# ---------------- Booking ----------------
#
# Everything below turns a search into an owned row in Booking - the table
# /api/journeys, and all five agents, already read. Passenger-only, the same
# reasoning as /api/journeys itself: booking a ticket is a passenger action.


def _passenger_for(profile):
    """The Passenger row this account's new booking should be filed under.

    Mirrors Profile.own_bookings' own matching rule so a booking made here
    is immediately visible there: reuse the linked Passenger if one exists,
    otherwise reuse an unclaimed record already carrying this phone number
    (e.g. left over from an earlier booking), otherwise create one.
    """
    if profile.passenger_id:
        return profile.passenger
    passenger, _ = Passenger.objects.get_or_create(
        phone=profile.phone_number,
        profile__isnull=True,
        defaults={"name": profile.phone_number},
    )
    return passenger


@passenger_required
@require_http_methods(["GET"])
def stations(request):
    """Every station in the network, for the booking search's From/To pickers."""
    rows = Station.objects.order_by("name")
    return JsonResponse(
        {
            "stations": [
                {"code": s.code, "name": s.name, "division": s.division} for s in rows
            ]
        }
    )


@passenger_required
@require_http_methods(["GET"])
def train_search(request):
    """Trains that run between two stations, with fare and seat availability
    for the leg actually travelled - not the train's whole route."""
    from_code = request.GET.get("from", "").strip().upper()
    to_code = request.GET.get("to", "").strip().upper()
    date = request.GET.get("date", "").strip()

    if not from_code or not to_code or not date:
        return JsonResponse({"error": "from, to and date are all required."}, status=400)
    if from_code == to_code:
        return JsonResponse({"error": "Pick two different stations."}, status=400)

    results = []
    for train in Train.objects.prefetch_related("stops__station"):
        leg = leg_for(train, from_code, to_code)
        if leg is None:
            continue
        from_stop, to_stop = leg
        leg_distance = round(to_stop.distance_km - from_stop.distance_km, 1)

        seat_classes = []
        for code in train.seat_classes:
            if code not in SEAT_CLASSES:
                continue
            total, available = available_seats(train, code, date)
            seat_classes.append(
                {
                    "code": code,
                    "label": SEAT_CLASSES[code]["label"],
                    "fare": round(SEAT_CLASSES[code]["taka_per_km"] * leg_distance),
                    "totalSeats": total,
                    "availableSeats": len(available),
                }
            )

        results.append(
            {
                "trainId": train.id,
                "name": train.name,
                "number": train.number,
                "from": from_stop.station.name,
                "to": to_stop.station.name,
                "departure": from_stop.departure,
                "arrival": to_stop.arrival,
                "durationMinutes": duration_minutes(from_stop, to_stop),
                "distanceKm": leg_distance,
                "seatClasses": seat_classes,
            }
        )

    results.sort(key=lambda r: r["departure"] or "")
    return JsonResponse({"trains": results})


@passenger_required
@require_http_methods(["GET"])
def train_seats(request, train_id):
    """The seat map for one train/class/date - what the seat picker shows."""
    train = Train.objects.filter(id=train_id).first()
    if train is None:
        return JsonResponse({"error": "No such train."}, status=404)

    seat_class = request.GET.get("class", "").strip()
    date = request.GET.get("date", "").strip()

    if seat_class not in train.seat_classes:
        return JsonResponse(
            {"error": f"{train.name} does not sell {seat_class or '(no class given)'}."},
            status=400,
        )
    if not date:
        return JsonResponse({"error": "date is required."}, status=400)

    total, available = available_seats(train, seat_class, date)
    return JsonResponse({"totalSeats": total, "availableSeats": available})


@csrf_exempt
@passenger_required
@require_http_methods(["POST"])
def create_booking(request):
    """Book seats on a train, generating the PNR that makes it a real ticket.

    Availability is re-checked inside the transaction rather than trusted
    from an earlier /seats call, so two passengers racing for the last seat
    can't both win it - the second gets a 409 and can try again.
    """
    try:
        payload = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Body must be JSON."}, status=400)

    train = Train.objects.filter(id=payload.get("trainId")).first()
    if train is None:
        return JsonResponse({"error": "No such train."}, status=404)

    date = str(payload.get("date", "")).strip()
    from_code = str(payload.get("from", "")).strip().upper()
    to_code = str(payload.get("to", "")).strip().upper()
    seat_class = str(payload.get("seatClass", "")).strip()
    passengers_payload = payload.get("passengers") or []
    requested_seats = payload.get("seatNumbers") or []

    if not date:
        return JsonResponse({"error": "Travel date is required."}, status=400)
    if seat_class not in train.seat_classes:
        return JsonResponse(
            {"error": f"{train.name} does not sell {seat_class or '(no class given)'}."},
            status=400,
        )
    if not passengers_payload:
        return JsonResponse({"error": "At least one passenger is required."}, status=400)
    if not all(str(p.get("name", "")).strip() for p in passengers_payload):
        return JsonResponse({"error": "Every passenger needs a name."}, status=400)

    leg = leg_for(train, from_code, to_code)
    if leg is None:
        return JsonResponse(
            {"error": "This train does not run between those two stations."}, status=400
        )
    from_stop, to_stop = leg
    count = len(passengers_payload)

    with transaction.atomic():
        total, available = available_seats(train, seat_class, date)

        if requested_seats:
            if len(set(requested_seats)) != count or any(
                seat not in available for seat in requested_seats
            ):
                return JsonResponse(
                    {"error": "One or more selected seats are no longer available."},
                    status=409,
                )
            seat_numbers = list(requested_seats)
        else:
            if len(available) < count:
                return JsonResponse(
                    {"error": f"Only {len(available)} {seat_class} seat(s) left."},
                    status=409,
                )
            seat_numbers = available[:count]

        leg_distance = round(to_stop.distance_km - from_stop.distance_km, 1)
        fare_each = round(SEAT_CLASSES[seat_class]["taka_per_km"] * leg_distance)
        fare_total = fare_each * count

        pnr = generate_pnr()
        for _ in range(5):
            if not Booking.objects.filter(pnr=pnr).exists():
                break
            pnr = generate_pnr()

        booking = Booking.objects.create(
            train=train,
            passenger=_passenger_for(request.profile),
            travel_date=date,
            scheduled_departure=from_stop.departure,
            expected_departure=from_stop.departure,
            coach=f"{SEAT_CLASSES[seat_class]['label']} / {', '.join(seat_numbers)}",
            status="on-time",
            pnr=pnr,
            booking_status="confirmed",
            seat_class=seat_class,
            seat_numbers=seat_numbers,
            passenger_count=count,
            fare_paid=fare_total,
            # Only set when boarding/alighting isn't the train's own
            # origin/destination - to_dict() falls back to the train's own
            # names otherwise.
            origin_station=from_stop.station if from_stop.station.name != train.origin else None,
            destination_station=to_stop.station
            if to_stop.station.name != train.destination
            else None,
        )

        for seat, rider in zip(seat_numbers, passengers_payload):
            BookingPassenger.objects.create(
                booking=booking,
                name=str(rider.get("name", "")).strip(),
                age=rider.get("age") or None,
                id_number=str(rider.get("idNumber") or "").strip() or None,
                seat_number=seat,
            )

    return JsonResponse({"booking": booking.to_dict()}, status=201)


@passenger_required
@require_http_methods(["GET"])
def booking_detail(request, pnr):
    """One ticket by its PNR - scoped the same way /api/journeys is, so a
    PNR that exists but belongs to someone else 404s rather than 403s (that
    would confirm the PNR is real)."""
    booking = (
        request.profile.own_bookings()
        .filter(pnr=pnr)
        .select_related("train")
        .prefetch_related("passengers_detail")
        .first()
    )
    if booking is None:
        return JsonResponse({"error": "No ticket found with that PNR."}, status=404)

    data = booking.to_dict()
    data["passengers"] = [p.to_dict() for p in booking.passengers_detail.all()]
    return JsonResponse({"booking": data})


@csrf_exempt
@passenger_required
@require_http_methods(["POST"])
def cancel_booking(request, booking_id):
    """Cancel a booking. Seats free themselves - availability is computed
    live off booking_status='confirmed' rows, nothing else to release."""
    booking = request.profile.own_bookings().filter(id=booking_id).first()
    if booking is None:
        return JsonResponse({"error": "No such booking."}, status=404)
    if booking.booking_status == "cancelled":
        return JsonResponse({"error": "This booking is already cancelled."}, status=409)

    booking.booking_status = "cancelled"
    booking.save()
    return JsonResponse({"booking": booking.to_dict()})
