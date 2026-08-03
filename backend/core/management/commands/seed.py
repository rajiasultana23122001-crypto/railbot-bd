"""Fill the database with sample data.

    python manage.py seed

Clears every table first, so it is safe to re-run whenever the sample data
changes or a demo needs a clean slate.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from core.data.network import TRAINS as NETWORK_TRAINS
from core.data.network import seat_classes_for
from core.models import (
    AgentLog,
    Arrival,
    Booking,
    Passenger,
    Platform,
    Station,
    Train,
)

BOOKINGS = [
    # train number, date, scheduled, expected, platform, coach, status, delay, note
    ("701", "1 Aug 2026", "07:00", "07:00", "4", "SNIGDHA / C1-24", "on-time", 0, None),
    (
        "709",
        "1 Aug 2026",
        "18:45",
        "19:20",
        "2",
        "SHOVAN / D3-11",
        "delayed",
        35,
        "Manager Agent called you at 17:52 with the new departure time. "
        "Scheduler Agent trimmed halts at Brahmanbaria and Srimangal to recover 12 minutes.",
    ),
    (
        "759",
        "2 Aug 2026",
        "23:00",
        "23:00",
        "6",
        "AC_S / B2-07",
        "at-risk",
        0,
        "Risk Agent predicts a 20-25 minute delay from heavy rainfall forecast "
        "near Ishwardi. You will be called if the delay is confirmed.",
    ),
    ("705", "3 Aug 2026", "10:10", "10:10", "3", "SHOVAN / F1-45", "on-time", 0, None),
    ("725", "3 Aug 2026", "21:45", "21:45", "5", "AC_B / A1-12", "on-time", 0, None),
]

PLATFORMS = [
    # number, occupancy, capacity, waiting for
    ("1", 305, 600, "Mohanagar Provati"),
    ("2", 545, 600, "Parabat Express"),
    ("3", 180, 550, "Ekota Express"),
    ("4", 470, 600, "Subarna Express"),
    ("5", 95, 500, None),
    ("6", 585, 650, "Padma Express"),
]

ARRIVALS = [
    # train number, scheduled, expected, platform, status
    ("704", "14:35", "14:35", "1", "on-time"),
    ("710", "14:50", "15:25", "2", "delayed"),
    ("706", "15:10", "15:10", "3", "on-time"),
    ("760", "15:40", "15:40", "6", "at-risk"),
    ("764", "16:05", "16:05", "4", "on-time"),
    ("722", "16:30", "16:30", "1", "on-time"),
    ("766", "16:55", "17:20", "5", "delayed"),
    ("814", "17:15", "17:15", "2", "on-time"),
]

# Oldest first, so the auto-increment id matches the real order of events.
AGENT_LOGS = [
    (
        "Risk Agent",
        "medium",
        "13:52",
        "Heavy rainfall forecast near Ishwardi. Padma Express flagged with a "
        "20-25 min delay risk.",
    ),
    (
        "Manager Agent",
        "info",
        "14:05",
        "Delay calls placed to 214 passengers booked on Parabat Express.",
    ),
    (
        "Scheduler Agent",
        "medium",
        "14:12",
        "Parabat Express delayed 35 min. Halts at Bhairab Bazar and Shaistaganj "
        "shortened; 12 minutes recovered.",
    ),
    (
        "Resource Agent",
        "high",
        "14:18",
        "Platform 6 is at 90% capacity with Padma Express still inbound. "
        "Open Waiting Room B and assign two crowd-control staff.",
    ),
]


class Command(BaseCommand):
    help = "Clear the database and load the RailBot BD sample data."

    @transaction.atomic
    def handle(self, *args, **options):
        for model in (AgentLog, Arrival, Platform, Booking, Station, Passenger, Train):
            model.objects.all().delete()

        # Origin and destination are the ends of the route, so the two can
        # never disagree with the stations the train actually calls at.
        trains = {}
        for name, number, route, distance, halts in NETWORK_TRAINS:
            trains[number] = Train.objects.create(
                name=name,
                number=number,
                origin=route[0],
                destination=route[-1],
                distance_km=distance,
                scheduled_halts=halts,
                route=route,
                seat_classes=seat_classes_for(number),
            )

        passenger = Passenger.objects.create(
            name="Istiak Ahammed Rumi", phone="+8801700000000"
        )

        for number, date, sched, exp, plat, coach, status, delay, note in BOOKINGS:
            Booking.objects.create(
                train=trains[number],
                passenger=passenger,
                travel_date=date,
                scheduled_departure=sched,
                expected_departure=exp,
                platform=plat,
                coach=coach,
                status=status,
                delay_minutes=delay,
                agent_note=note,
                # The passenger was told the delayed time; the Scheduler Agent
                # has not yet had a chance to improve on it.
                notified_departure=exp if status == "delayed" else None,
            )

        station = Station.objects.create(
            name="Dhaka (Kamalapur)",
            code="DHKA",
            passengers_on_site=3180,
            capacity=3500,
        )

        for number, occupancy, capacity, waiting_for in PLATFORMS:
            Platform.objects.create(
                station=station,
                number=number,
                occupancy=occupancy,
                capacity=capacity,
                waiting_for=waiting_for,
            )

        for number, scheduled, expected, plat, status in ARRIVALS:
            Arrival.objects.create(
                station=station,
                train=trains[number],
                scheduled=scheduled,
                expected=expected,
                platform=plat,
                status=status,
            )

        for agent, severity, logged_at, message in AGENT_LOGS:
            AgentLog.objects.create(
                agent=agent,
                severity=severity,
                logged_at=logged_at,
                message=message,
            )

        self.stdout.write("Database seeded:")
        self.stdout.write(f"  trains     {Train.objects.count()}")
        self.stdout.write(f"  bookings   {Booking.objects.count()}")
        self.stdout.write(f"  platforms  {Platform.objects.count()}")
        self.stdout.write(f"  arrivals   {Arrival.objects.count()}")
        self.stdout.write(f"  agent logs {AgentLog.objects.count()}")
