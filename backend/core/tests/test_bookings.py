"""The self-service booking flow: search a route, book it, see it, cancel it.

Booking used to be something only `manage.py seed` could do - these pin down
the path that replaced that: a passenger can search a real leg, book seats
against real availability, and the result is an ordinary row `/api/journeys`
already knew how to show. Scoping tests mirror test_journeys.py's own -
booking is passenger data, so the same "not another account's" rule applies.
"""

import json

from django.test import TestCase
from rest_framework.authtoken.models import Token

from core.models import Booking

from .builders import make_booked_route, make_passenger_account


class BookingFlowTests(TestCase):
    def setUp(self):
        self.train, self.origin, self.destination = make_booked_route()
        self.profile, _ = make_passenger_account("+8801700000000", nid="1010101010")
        self.token, _ = Token.objects.get_or_create(user=self.profile.user)
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {self.token.key}"}

    def search(self, **params):
        params.setdefault("from", "DHKA")
        params.setdefault("to", "CTG")
        params.setdefault("date", "1 Aug 2026")
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return self.client.get(f"/api/trains/search?{query}", **self.auth)

    def book(self, **overrides):
        payload = {
            "trainId": self.train.id,
            "date": "1 Aug 2026",
            "from": "DHKA",
            "to": "CTG",
            "seatClass": "SHOVAN",
            "passengers": [{"name": "Test Rider", "age": 30}],
        }
        payload.update(overrides)
        return self.client.post(
            "/api/bookings",
            data=json.dumps(payload),
            content_type="application/json",
            **self.auth,
        )

    def test_search_prices_the_leg_and_reports_availability(self):
        response = self.search()
        self.assertEqual(response.status_code, 200)

        trains = response.json()["trains"]
        self.assertEqual(len(trains), 1)
        shovan = next(c for c in trains[0]["seatClasses"] if c["code"] == "SHOVAN")
        self.assertEqual(shovan["totalSeats"], 2)
        self.assertEqual(shovan["availableSeats"], 2)
        # 0.60 taka/km (see SEAT_CLASSES) * 320 km.
        self.assertEqual(shovan["fare"], 192)

    def test_booking_appears_immediately_on_the_dashboard(self):
        response = self.book()
        self.assertEqual(response.status_code, 201)
        booking = response.json()["booking"]
        self.assertTrue(booking["pnr"])
        self.assertEqual(booking["bookingStatus"], "confirmed")

        journeys = self.client.get("/api/journeys", **self.auth).json()["journeys"]
        self.assertIn(booking["pnr"], [j["pnr"] for j in journeys])

    def test_booking_the_last_seat_then_the_next_shows_none_left(self):
        # SHOVAN has 2 seats (see make_train). Take both.
        self.book(passengers=[{"name": "A"}, {"name": "B"}])

        trains = self.search().json()["trains"]
        shovan = next(c for c in trains[0]["seatClasses"] if c["code"] == "SHOVAN")
        self.assertEqual(shovan["availableSeats"], 0)

        third = self.book(passengers=[{"name": "C"}])
        self.assertEqual(third.status_code, 409)

    def test_cancelling_frees_the_seat_back_up(self):
        booking_id = self.book(
            passengers=[{"name": "A"}, {"name": "B"}]
        ).json()["booking"]["bookingId"]

        self.client.post(f"/api/bookings/{booking_id}/cancel", **self.auth)

        trains = self.search().json()["trains"]
        shovan = next(c for c in trains[0]["seatClasses"] if c["code"] == "SHOVAN")
        self.assertEqual(shovan["availableSeats"], 2)

        booking = Booking.objects.get(id=booking_id)
        self.assertEqual(booking.booking_status, "cancelled")

    def test_a_passenger_cannot_fetch_or_cancel_another_passengers_ticket(self):
        pnr = self.book().json()["booking"]["pnr"]
        booking_id = Booking.objects.get(pnr=pnr).id

        other, _ = make_passenger_account("+8801800000000", nid="2020202020")
        other_token, _ = Token.objects.get_or_create(user=other.user)
        other_auth = {"HTTP_AUTHORIZATION": f"Bearer {other_token.key}"}

        self.assertEqual(
            self.client.get(f"/api/bookings/{pnr}", **other_auth).status_code, 404
        )
        self.assertEqual(
            self.client.post(f"/api/bookings/{booking_id}/cancel", **other_auth).status_code,
            404,
        )
        # Untouched by the failed attempt.
        self.assertEqual(
            Booking.objects.get(id=booking_id).booking_status, "confirmed"
        )
