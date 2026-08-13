"""The JSON contract the React dashboards are written against.

Every response in this project comes straight from a model's to_dict(), which
is what lets the API do no reshaping. The cost of that design is that a field
rename in models.py is a silent frontend break: Python is happy, the endpoint
returns 200, and a card on the dashboard just renders undefined.

These tests are the alarm for that. They assert key names, not values.
"""

from django.test import TestCase
from rest_framework.authtoken.models import Token

from core.models import AgentLog, Arrival, Booking, Platform

from .builders import (
    make_authority_account,
    make_booking,
    make_passenger_account,
    make_platform,
    make_station,
    make_train,
)


class BookingShapeTests(TestCase):
    """What the Passenger Dashboard reads off each journey card."""

    EXPECTED_KEYS = {
        "id",
        "bookingId",
        "train",
        "trainNo",
        "from",
        "to",
        "date",
        "scheduledDeparture",
        "expectedDeparture",
        "platform",
        "coach",
        "status",
        "delayMinutes",
        "agentNote",
        # Added for self-service booking: see Booking in models.py.
        "pnr",
        "bookingStatus",
        "seatClass",
        "seatNumbers",
        "passengerCount",
        "farePaid",
    }

    def setUp(self):
        _, self.passenger = make_passenger_account("+8801700000000", nid="1010101010")
        self.train = make_train("701", "Subarna Express")

    def test_a_journey_carries_exactly_the_keys_the_card_uses(self):
        booking = make_booking(self.train, self.passenger)
        self.assertEqual(set(booking.to_dict()), self.EXPECTED_KEYS)

    def test_delay_minutes_is_what_is_still_outstanding(self):
        """The card shows one number, and it has to be the delay the
        passenger will actually experience - the reported slip less whatever
        the Scheduler has clawed back, never the raw figure."""
        booking = make_booking(
            self.train,
            self.passenger,
            status="delayed",
            delay_minutes=60,
            recovered_minutes=24,
        )
        self.assertEqual(booking.to_dict()["delayMinutes"], 36)

    def test_recovery_beyond_the_delay_never_reads_as_early(self):
        """current_delay floors at zero. A negative delayMinutes would render
        as a train departing before it was due."""
        booking = make_booking(
            self.train,
            self.passenger,
            status="delayed",
            delay_minutes=20,
            recovered_minutes=35,
        )
        self.assertEqual(booking.to_dict()["delayMinutes"], 0)


class StationShapeTests(TestCase):
    """What the Station Master Panel reads off one /api/station call."""

    def setUp(self):
        self.authority = make_authority_account("+8801900000000")
        _, passenger = make_passenger_account("+8801700000000", nid="1010101010")

        self.station = make_station("DHKA")
        self.train = make_train("701", "Subarna Express")
        make_booking(self.train, passenger)
        make_platform(self.station, number="4", occupancy=470, capacity=600)

        Arrival.objects.create(
            station=self.station,
            train=self.train,
            scheduled="14:35",
            expected="14:35",
            platform="4",
            status="on-time",
        )
        AgentLog.objects.create(
            agent="Resource Agent",
            severity="high",
            message="Platform 4 is filling up.",
            logged_at="14:18",
        )

    def bearer(self):
        token, _ = Token.objects.get_or_create(user=self.authority.user)
        return f"Bearer {token.key}"

    def station_payload(self, code=None):
        response = self.client.get(
            f"/api/station/{code or self.station.code}",
            HTTP_AUTHORIZATION=self.bearer(),
        )
        return response

    def test_platform_meter_keys(self):
        payload = self.station_payload().json()
        self.assertEqual(
            set(payload["platforms"][0]), {"id", "occupancy", "capacity", "waitingFor"}
        )

    def test_arrival_row_keys_including_the_route_for_the_map(self):
        payload = self.station_payload().json()
        self.assertEqual(
            set(payload["arrivals"][0]),
            {
                "id",
                "train",
                "trainNo",
                "from",
                "scheduled",
                "expected",
                "platform",
                "status",
                "route",
            },
        )

    def test_agent_alert_keys(self):
        payload = self.station_payload().json()
        self.assertEqual(
            set(payload["agentAlerts"][0]),
            {"id", "time", "agent", "severity", "message"},
        )

    def test_a_lowercase_station_code_still_resolves(self):
        """The frontend builds this path from a route param. Codes are stored
        uppercase, and the view upper()s what it is given - so a link that
        happens to carry 'dhka' must not 404."""
        self.assertEqual(self.station_payload("dhka").status_code, 200)

    def test_an_unknown_station_says_which_code_it_could_not_find(self):
        response = self.station_payload("XXXX")
        self.assertEqual(response.status_code, 404)
        self.assertIn("XXXX", response.json()["error"])

    def test_the_log_reads_newest_first(self):
        """The panel prints this list top-down without sorting it."""
        AgentLog.objects.create(
            agent="Risk Agent", severity="medium", message="Later.", logged_at="15:00"
        )
        alerts = self.station_payload().json()["agentAlerts"]
        self.assertEqual(alerts[0]["message"], "Later.")


class TimetableShapeTests(TestCase):
    """The train browser, which is the only place fares are shown."""

    def setUp(self):
        self.passenger, _ = make_passenger_account("+8801700000000", nid="1010101010")
        self.train = make_train("701", "Subarna Express", distance=320)

    def timetable(self):
        token, _ = Token.objects.get_or_create(user=self.passenger.user)
        response = self.client.get(
            "/api/train-info", HTTP_AUTHORIZATION=f"Bearer {token.key}"
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["trains"][0]

    def test_train_keys(self):
        self.assertEqual(
            set(self.timetable()),
            {
                "name",
                "number",
                "origin",
                "destination",
                "distanceKm",
                "scheduledHalts",
                "route",
                "seatClasses",
            },
        )

    def test_a_fare_is_derived_from_distance_rather_than_stored(self):
        """Fares are a per-km rate times this train's own distance, so no
        fare can drift out of step with the route it belongs to. Doubling
        the distance has to double every fare on the train."""
        before = {s["code"]: s["fare"] for s in self.timetable()["seatClasses"]}

        self.train.distance_km = 640
        self.train.save()

        after = {s["code"]: s["fare"] for s in self.timetable()["seatClasses"]}

        self.assertEqual(set(before), set(after))
        for code, fare in before.items():
            self.assertEqual(after[code], fare * 2)

    def test_an_unknown_seat_class_is_dropped_rather_than_crashing(self):
        """seat_classes is free-form JSON. A typo in the seed data should
        cost that one class, not the whole timetable endpoint."""
        self.train.seat_classes = ["SNIGDHA", "NOT_A_REAL_CLASS"]
        self.train.save()

        codes = [s["code"] for s in self.timetable()["seatClasses"]]
        self.assertEqual(codes, ["SNIGDHA"])


class ResourceAgentEdgeTests(TestCase):
    """One arithmetic edge the Resource Agent does not currently guard."""

    def setUp(self):
        self.station = make_station("DHKA")

    def test_a_platform_with_no_stated_capacity_does_not_crash_the_cycle(self):
        """EXPECTED FAILURE - observe() computes occupancy / capacity with no
        guard, so a platform saved with capacity 0 raises ZeroDivisionError.
        That exception escapes run_cycle(), which means one bad row in the
        admin takes down every agent behind it, including the Manager Agent
        that was about to text delayed passengers.

        capacity has no default and no validator, so nothing stops a 0 being
        saved. Fix at whichever end you prefer - a MinValueValidator(1) on
        the field, or skipping non-positive capacities in observe() - but
        the cycle must survive it either way."""
        from core.agents.resource_agent import ResourceAgent

        Platform.objects.create(
            station=self.station, number="9", occupancy=40, capacity=0
        )

        result = ResourceAgent().run()
        self.assertIsInstance(result, dict)


class AdvisorPatternTests(TestCase):
    """How the Advisor decides a platform is a recurring problem."""

    def setUp(self):
        self.station = make_station("DHKA")

    def test_platform_one_is_not_credited_with_platform_tens_alerts(self):
        """EXPECTED FAILURE - the Advisor counts mentions with a substring
        test, `f"Platform {number}" in message`. "Platform 1" is a substring
        of "Platform 10", so at a station with ten or more platforms, every
        alert about 10, 11 or 12 is also counted against platform 1 - which
        then gets recommended for a timetable change it did not earn.

        Six platforms are seeded today, which is why nothing has gone wrong
        yet. Fix: match on a word boundary, or - better - stop parsing
        message text and give AgentLog a nullable platform reference."""
        from core.agents.advisor_agent import AdvisorAgent

        make_platform(self.station, number="1", occupancy=100, capacity=600)
        make_platform(self.station, number="10", occupancy=100, capacity=600)

        for _ in range(3):
            AgentLog.objects.create(
                agent="Resource Agent",
                severity="high",
                message="Platform 10 is at 95% capacity.",
                logged_at="14:00",
            )

        suggestions = AdvisorAgent().reason(AdvisorAgent().observe())["suggestions"]
        about_platform_one = [s for s in suggestions if s.startswith("Platform 1 ")]

        self.assertEqual(about_platform_one, [])
