"""Create the database and fill it with sample data.

Run this once before starting the API:

    venv\\Scripts\\python seed.py

It drops and rebuilds every table, so it is safe to re-run whenever the sample
data changes. The figures match what the dashboards were showing from their
local sample files.
"""

from app import app
from models import AgentLog, Arrival, Booking, Passenger, Platform, Station, Train, db

TRAINS = [
    # name, number, origin, destination
    ("Subarna Express", "702", "Dhaka (Kamalapur)", "Chattogram"),
    ("Parabat Express", "709", "Dhaka (Kamalapur)", "Sylhet"),
    ("Padma Express", "759", "Dhaka (Kamalapur)", "Rajshahi"),
    ("Ekota Express", "765", "Dhaka (Kamalapur)", "Dinajpur"),
    ("Mohanagar Provati", "704", "Chattogram", "Dhaka (Kamalapur)"),
    ("Parabat Express (up)", "710", "Sylhet", "Dhaka (Kamalapur)"),
    ("Ekota Express (up)", "766", "Dinajpur", "Dhaka (Kamalapur)"),
    ("Padma Express (up)", "760", "Rajshahi", "Dhaka (Kamalapur)"),
    ("Chitra Express", "764", "Khulna", "Dhaka (Kamalapur)"),
]

BOOKINGS = [
    # train number, date, scheduled, expected, platform, coach, status, delay, note
    ("702", "1 Aug 2026", "07:00", "07:00", "4", "SNIGDHA / C1-24", "on-time", 0, None),
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
        "Scheduler Agent trimmed halts at Bhairab Bazar and Shaistaganj to recover 12 minutes.",
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
    ("765", "3 Aug 2026", "10:10", "10:10", "3", "SHOVAN / F1-45", "on-time", 0, None),
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
    ("766", "15:10", "15:10", "3", "on-time"),
    ("760", "15:40", "15:40", "6", "at-risk"),
    ("764", "16:05", "16:05", "4", "on-time"),
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


def seed():
    with app.app_context():
        db.drop_all()
        db.create_all()

        trains = {}
        for name, number, origin, destination in TRAINS:
            train = Train(
                name=name, number=number, origin=origin, destination=destination
            )
            db.session.add(train)
            trains[number] = train
        db.session.flush()  # assigns ids without committing yet

        passenger = Passenger(name="Istiak Ahammed Rumi", phone="+8801700000000")
        db.session.add(passenger)
        db.session.flush()

        for number, date, sched, exp, plat, coach, status, delay, note in BOOKINGS:
            db.session.add(
                Booking(
                    train_id=trains[number].id,
                    passenger_id=passenger.id,
                    travel_date=date,
                    scheduled_departure=sched,
                    expected_departure=exp,
                    platform=plat,
                    coach=coach,
                    status=status,
                    delay_minutes=delay,
                    agent_note=note,
                )
            )

        station = Station(
            name="Dhaka (Kamalapur)",
            code="DHKA",
            passengers_on_site=3180,
            capacity=3500,
        )
        db.session.add(station)
        db.session.flush()

        for number, occupancy, capacity, waiting_for in PLATFORMS:
            db.session.add(
                Platform(
                    station_id=station.id,
                    number=number,
                    occupancy=occupancy,
                    capacity=capacity,
                    waiting_for=waiting_for,
                )
            )

        for number, scheduled, expected, plat, status in ARRIVALS:
            db.session.add(
                Arrival(
                    station_id=station.id,
                    train_id=trains[number].id,
                    scheduled=scheduled,
                    expected=expected,
                    platform=plat,
                    status=status,
                )
            )

        for agent, severity, logged_at, message in AGENT_LOGS:
            db.session.add(
                AgentLog(
                    agent=agent,
                    severity=severity,
                    logged_at=logged_at,
                    message=message,
                )
            )

        db.session.commit()

        print("Database seeded:")
        print(f"  trains     {Train.query.count()}")
        print(f"  bookings   {Booking.query.count()}")
        print(f"  platforms  {Platform.query.count()}")
        print(f"  arrivals   {Arrival.query.count()}")
        print(f"  agent logs {AgentLog.query.count()}")


if __name__ == "__main__":
    seed()
