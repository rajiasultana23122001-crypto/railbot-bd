"""create_booking(), when every generated PNR already exists.

Calls the view directly with RequestFactory rather than through a URL, so
this test needs no knowledge of urls.py - only the view function's own
contract with the request it's given.
"""

import json
from unittest import mock

from django.test import RequestFactory, TestCase
from rest_framework.authtoken.models import Token

from core import views
from core.models import Booking

from .builders import make_booked_route, make_passenger_account


class BookingPnrCollisionTests(TestCase):
    """generate_pnr() is retried up to five times against a uniqueness
    check, but nothing happens when all five retries still collide - the
    loop simply ends, and Booking.objects.create() is called with the
    duplicate value anyway. That raises an IntegrityError the view does not
    catch, which reaches the caller as a bare 500 rather than the ordinary
    JSON error every other failure on this endpoint returns.

    Six calls to generate_pnr() happen in the worst case - one before the
    loop, one more on each of the five iterations that finds a collision -
    so the stub below, which always returns the same value, reproduces
    exactly that path regardless of how many times it's called.
    """

    def setUp(self):
        self.profile, self.passenger = make_passenger_account(
            "+8801700000000", nid="1010101010"
        )
        self.train, self.origin, self.destination = make_booked_route()

        # Occupies the one PNR the stub below will ever produce, so every
        # retry the view attempts collides with this row.
        Booking.objects.create(
            train=self.train,
            passenger=self.passenger,
            travel_date="2026-09-01",
            scheduled_departure="07:00",
            expected_departure="07:00",
            coach="SHOVAN / 1A",
            status="on-time",
            pnr="COLLIDE1",
            booking_status="confirmed",
            seat_class="SHOVAN",
            seat_numbers=["1A"],
            passenger_count=1,
            fare_paid=100,
        )

    def post_booking(self):
        token, _ = Token.objects.get_or_create(user=self.profile.user)
        payload = {
            "trainId": self.train.id,
            "date": "2026-09-01",
            "from": self.origin.code,
            "to": self.destination.code,
            "seatClass": "SHOVAN",
            "passengers": [{"name": "Test Rider"}],
        }
        request = RequestFactory().post(
            "/api/bookings",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token.key}",
        )
        return views.create_booking(request)

    def test_exhausting_every_retry_does_not_crash(self):
        """EXPECTED FAILURE against the current code - this is the bug.

        Once every PNR the generator can produce is already taken, five
        retries change nothing, and the endpoint must still answer with a
        JSON error rather than an unhandled exception."""
        with mock.patch("core.views.generate_pnr", return_value="COLLIDE1"):
            response = self.post_booking()

        self.assertEqual(response.status_code, 503)
        self.assertIn("try again", response.json()["error"].lower())

    def test_a_booking_is_never_created_with_a_duplicate_pnr(self):
        """Whatever the endpoint does when retries are exhausted, the one
        thing it must never do is create a second Booking sharing a PNR
        with an existing one - the PNR is how a passenger finds their
        ticket again, so two tickets under one PNR is worse than an error."""
        before = Booking.objects.filter(pnr="COLLIDE1").count()

        with mock.patch("core.views.generate_pnr", return_value="COLLIDE1"):
            self.post_booking()

        self.assertEqual(Booking.objects.filter(pnr="COLLIDE1").count(), before)
