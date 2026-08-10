"""Reporting a delay: what the endpoint accepts, and what it changes.

The agent behaviour that follows a delay is covered in test_agents.py. This
file is about the doorway into it - POST /api/delays - which is the only
place a human types a number into this system, and therefore the only place
a typo can reach the agents.

Two tests here fail against the current code. They are marked with an
EXPECTED FAILURE note and describe the bug they found rather than the
behaviour that exists, because a test written to match a bug is worse than
no test at all.
"""

import json

from django.test import TestCase
from rest_framework.authtoken.models import Token

from core.models import Arrival, Booking

from .builders import (
    make_authority_account,
    make_booking,
    make_passenger_account,
    make_station,
    make_train,
)


class ReportDelayValidationTests(TestCase):
    """Every way the form can be filled in wrong, and what comes back.

    Each branch returns its own message: a station master who mistyped a
    number should not have to guess which of four things went wrong.
    """

    def setUp(self):
        self.authority = make_authority_account("+8801900000000")
        _, passenger = make_passenger_account("+8801700000000", nid="1010101010")
        self.train = make_train("701", "Subarna Express")
        self.booking = make_booking(self.train, passenger, scheduled_departure="07:00")

    def report(self, payload, raw=None):
        token, _ = Token.objects.get_or_create(user=self.authority.user)
        return self.client.post(
            "/api/delays",
            data=raw if raw is not None else json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token.key}",
        )

    def test_a_valid_report_is_accepted_and_echoed_back(self):
        response = self.report({"trainNo": "701", "minutes": 60})
        self.assertEqual(response.status_code, 200)

        reported = response.json()["reported"]
        self.assertEqual(reported["minutes"], 60)
        self.assertEqual(reported["scheduledDeparture"], "07:00")
        # 07:00 + 60 min, before the Scheduler claws any of it back.
        self.assertEqual(reported["departureAfterDelay"], "08:00")

    def test_the_echoed_delay_is_the_one_that_was_typed(self):
        """The Scheduler runs inside this request and pulls the departure
        earlier. What comes back under 'reported' must still be what the
        station master entered, or the confirmation contradicts the form."""
        response = self.report({"trainNo": "701", "minutes": 60})
        body = response.json()

        self.assertEqual(body["reported"]["minutes"], 60)
        # And the settled time is reported separately rather than overwriting it.
        self.assertIn("settledDeparture", body)

    def test_no_train_selected(self):
        response = self.report({"minutes": 30})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Pick a train first.")

    def test_minutes_that_is_not_a_number(self):
        response = self.report({"trainNo": "701", "minutes": "soon"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("whole number", response.json()["error"])

    def test_minutes_missing_entirely(self):
        response = self.report({"trainNo": "701"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("whole number", response.json()["error"])

    def test_the_range_boundaries(self):
        """1 and 300 are inside; 0 and 301 are not. Off-by-one at either end
        would either accept a meaningless delay or refuse a real five-hour one."""
        for minutes, expected in [(0, 400), (1, 200), (300, 200), (301, 400)]:
            with self.subTest(minutes=minutes):
                response = self.report({"trainNo": "701", "minutes": minutes})
                self.assertEqual(response.status_code, expected)

    def test_a_negative_delay_is_refused(self):
        response = self.report({"trainNo": "701", "minutes": -20})
        self.assertEqual(response.status_code, 400)
        self.assertIn("between 1 and 300", response.json()["error"])

    def test_a_train_nobody_has_booked(self):
        response = self.report({"trainNo": "999", "minutes": 30})
        self.assertEqual(response.status_code, 404)
        self.assertIn("999", response.json()["error"])

    def test_a_body_that_is_not_json(self):
        response = self.report(None, raw="not json at all")
        self.assertEqual(response.status_code, 400)
        self.assertIn("JSON", response.json()["error"])

    def test_an_empty_body(self):
        response = self.report(None, raw="")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Pick a train first.")

    def test_a_rejected_report_changes_nothing(self):
        """A 400 must be inert. Half-applying an invalid delay would leave a
        booking marked late with no agent having decided anything about it."""
        self.report({"trainNo": "701", "minutes": 900})

        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, "on-time")
        self.assertEqual(self.booking.delay_minutes, 0)
        self.assertEqual(self.booking.expected_departure, "07:00")

    def test_a_boolean_is_not_a_number_of_minutes(self):
        """EXPECTED FAILURE - int(True) is 1, so `"minutes": true` is
        currently accepted as a one-minute delay. A checkbox posted into
        the wrong field should be refused, not silently believed."""
        response = self.report({"trainNo": "701", "minutes": True})
        self.assertEqual(response.status_code, 400)

    def test_a_null_train_reads_as_no_train_selected(self):
        """EXPECTED FAILURE - str(None) is the string "None", which gets as
        far as the database lookup and comes back as 404 "No booked journey
        on train None." The station master picked nothing; say so."""
        response = self.report({"trainNo": None, "minutes": 30})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"], "Pick a train first.")


class DelayReachesEveryPassengerTests(TestCase):
    """A delay is a fact about a train, not about one booking on it."""

    def setUp(self):
        self.authority = make_authority_account("+8801900000000")
        _, self.rumi = make_passenger_account(
            "+8801700000000", name="Istiak Ahammed Rumi", nid="1990123456789012"
        )
        _, self.rajia = make_passenger_account(
            "+8801800000000", name="Rajia Sultana", nid="1995987654321098"
        )

        # One train, two passengers aboard it - the ordinary case.
        self.train = make_train("701", "Subarna Express")
        self.rumi_booking = make_booking(self.train, self.rumi)
        self.rajia_booking = make_booking(self.train, self.rajia)

    def report(self, minutes=60):
        token, _ = Token.objects.get_or_create(user=self.authority.user)
        return self.client.post(
            "/api/delays",
            data=json.dumps({"trainNo": "701", "minutes": minutes}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token.key}",
        )

    def test_both_passengers_on_the_delayed_train_are_marked_delayed(self):
        """EXPECTED FAILURE - report_delay calls .first() on the queryset, so
        only one booking is updated. The second passenger's dashboard still
        reads on-time, and the Manager Agent never texts them, because it
        only looks at bookings whose status is 'delayed'.

        Fix: filter(...).update(...) over every booking on the train, or loop
        the queryset. Nothing else in the flow needs changing - the agents
        already handle any number of delayed bookings."""
        self.report(60)

        self.rumi_booking.refresh_from_db()
        self.rajia_booking.refresh_from_db()

        self.assertEqual(self.rumi_booking.status, "delayed")
        self.assertEqual(self.rajia_booking.status, "delayed")

    def test_both_passengers_are_told(self):
        """The consequence of the bug above, stated in the terms that matter:
        one of the two people on this train is never contacted."""
        self.report(60)

        notified = Booking.objects.filter(
            train=self.train, notified_departure__isnull=False
        ).count()
        self.assertEqual(notified, 2)


class ArrivalsBoardStaysCurrentTests(TestCase):
    """The Station Master Panel's arrivals board, after a delay is reported."""

    def setUp(self):
        self.authority = make_authority_account("+8801900000000")
        _, passenger = make_passenger_account("+8801700000000", nid="1010101010")

        self.station = make_station("DHKA")
        self.train = make_train("701", "Subarna Express")
        make_booking(self.train, passenger, scheduled_departure="07:00")

        self.arrival = Arrival.objects.create(
            station=self.station,
            train=self.train,
            scheduled="07:00",
            expected="07:00",
            status="on-time",
            platform="4",
        )

    def bearer(self):
        token, _ = Token.objects.get_or_create(user=self.authority.user)
        return f"Bearer {token.key}"

    def test_the_arrivals_board_reflects_a_reported_delay(self):
        """EXPECTED FAILURE - report_delay writes to Booking and never to
        Arrival, and no agent touches Arrival either. Report a delay on train
        701 and the passenger's dashboard says delayed while the operator's
        own arrivals board beside it still says on-time.

        This is the exact failure the architecture slide claims one call
        returning the whole station prevents: it makes the numbers arrive
        together, but they can still disagree if only one of them is updated.

        Fix: update the matching Arrival rows in report_delay, or - better -
        give the Scheduler Agent the job, since it is already the agent that
        owns expected departure times."""
        self.client.post(
            "/api/delays",
            data=json.dumps({"trainNo": "701", "minutes": 60}),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.bearer(),
        )

        self.arrival.refresh_from_db()
        self.assertEqual(self.arrival.status, "delayed")
        self.assertNotEqual(self.arrival.expected, "07:00")

    def test_the_station_payload_carries_platforms_arrivals_and_logs_together(self):
        """One request, one consistent picture - the property the panel is
        built on. This one passes; it is here so a future refactor that
        splits the endpoint up has to argue with a test first."""
        response = self.client.get(
            f"/api/station/{self.station.code}", HTTP_AUTHORIZATION=self.bearer()
        )
        self.assertEqual(response.status_code, 200)

        body = response.json()
        for key in ("station", "platforms", "arrivals", "agentAlerts"):
            self.assertIn(key, body)
