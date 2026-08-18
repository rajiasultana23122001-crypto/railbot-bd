"""The booking endpoints coverage missed.

test_bookings.py already covers the ordinary path: search, book, appear on
the dashboard, run out of seats, cancel, and scoping to your own account.
This file is the paths that weren't reached from there - not because they
were skipped on purpose, but because nobody wrote to them yet. Coverage's
line numbers are how these were found; every test below is named for the
gap it closes, not for the tool that found it.
"""

import json

from django.test import TestCase
from rest_framework.authtoken.models import Token

from core.models import Booking, Passenger, Station

from .builders import make_booked_route, make_passenger_account, make_train_stop


class AuthedClient(TestCase):
    """Shared setup: one passenger, one bookable route, one bearer token."""

    def setUp(self):
        self.train, self.origin, self.destination = make_booked_route()
        self.profile, _ = make_passenger_account("+8801700000000", nid="1010101010")
        self.token, _ = Token.objects.get_or_create(user=self.profile.user)
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {self.token.key}"}

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


class SeatMapTests(AuthedClient):
    """GET /api/trains/<id>/seats - untested before this file. Line 290-308."""

    def seats(self, train_id=None, **params):
        params.setdefault("class", "SHOVAN")
        params.setdefault("date", "1 Aug 2026")
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return self.client.get(
            f"/api/trains/{train_id or self.train.id}/seats?{query}", **self.auth
        )

    def test_an_empty_train_reports_every_seat_free(self):
        response = self.seats()
        self.assertEqual(response.status_code, 200)

        body = response.json()
        self.assertEqual(body["totalSeats"], 2)  # SHOVAN capacity, see make_train
        self.assertEqual(len(body["availableSeats"]), 2)

    def test_a_booked_seat_disappears_from_the_map(self):
        self.book()

        available = self.seats().json()["availableSeats"]
        self.assertEqual(len(available), 1)

    def test_an_unknown_train_id(self):
        response = self.seats(train_id=999999)
        self.assertEqual(response.status_code, 404)

    def test_a_class_the_train_does_not_sell(self):
        response = self.seats(**{"class": "AC_B"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("SHOVAN", str(self.train.seat_classes))  # sanity: AC_B really isn't sold
        self.assertNotIn("AC_B", self.train.seat_classes)

    def test_a_missing_date(self):
        response = self.client.get(
            f"/api/trains/{self.train.id}/seats?class=SHOVAN", **self.auth
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("date", response.json()["error"].lower())


class ExplicitSeatSelectionTests(AuthedClient):
    """POST /api/bookings with seatNumbers - the race-condition guarantee
    the SRS calls out (REQ-135/136) had no test at all. Lines 361-368."""

    def seat_codes(self):
        from core.services.booking import available_seats

        _, available = available_seats(self.train, "SHOVAN", "1 Aug 2026")
        return available

    def test_choosing_a_specific_free_seat_is_honoured(self):
        chosen = self.seat_codes()[:1]
        response = self.book(seatNumbers=chosen)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["booking"]["seatNumbers"], chosen)

    def test_choosing_a_seat_someone_else_just_took_is_refused(self):
        """The exact scenario REQ-136 describes: the seat map was drawn,
        then someone else took the seat, then this request arrives."""
        taken = self.seat_codes()[:1]
        self.book(seatNumbers=taken)  # someone else gets there first

        response = self.book(seatNumbers=taken)

        self.assertEqual(response.status_code, 409)
        self.assertIn("no longer available", response.json()["error"])

    def test_the_refused_request_books_nothing(self):
        taken = self.seat_codes()[:1]
        self.book(seatNumbers=taken)
        before = Booking.objects.count()

        self.book(seatNumbers=taken)

        self.assertEqual(Booking.objects.count(), before)

    def test_asking_for_the_same_seat_twice_in_one_request_is_refused(self):
        """Two passengers, one seat number repeated - not a race with anyone
        else, just a self-contradictory request."""
        seat = self.seat_codes()[0]
        response = self.book(
            seatNumbers=[seat, seat],
            passengers=[{"name": "A"}, {"name": "B"}],
        )
        self.assertEqual(response.status_code, 409)

    def test_a_seat_number_that_does_not_exist_on_this_train_is_refused(self):
        response = self.book(seatNumbers=["SHOVAN-99"])
        self.assertEqual(response.status_code, 409)


class BookingDetailTests(AuthedClient):
    """GET /api/bookings/<pnr> - only the 'someone else's PNR' branch had a
    test. Retrieving your own valid ticket never ran. Lines 451-453."""

    def test_your_own_ticket_comes_back_with_its_passengers(self):
        pnr = self.book(
            passengers=[{"name": "Rumi", "age": 22}, {"name": "Rajia", "age": 24}]
        ).json()["booking"]["pnr"]

        response = self.client.get(f"/api/bookings/{pnr}", **self.auth)

        self.assertEqual(response.status_code, 200)
        body = response.json()["booking"]
        self.assertEqual(body["pnr"], pnr)
        names = {p["name"] for p in body["passengers"]}
        self.assertEqual(names, {"Rumi", "Rajia"})

    def test_a_pnr_that_has_never_existed(self):
        response = self.client.get("/api/bookings/NOSUCHPNR", **self.auth)
        self.assertEqual(response.status_code, 404)


class CancelBookingTests(AuthedClient):
    """POST /api/bookings/<id>/cancel - the double-cancel 409 branch had no
    test; only a successful first cancel was covered. Line 466."""

    def test_cancelling_twice_is_refused_the_second_time(self):
        booking_id = self.book().json()["booking"]["bookingId"]
        self.client.post(f"/api/bookings/{booking_id}/cancel", **self.auth)

        second = self.client.post(f"/api/bookings/{booking_id}/cancel", **self.auth)

        self.assertEqual(second.status_code, 409)
        self.assertIn("already cancelled", second.json()["error"])

    def test_an_unknown_booking_id(self):
        response = self.client.post("/api/bookings/999999/cancel", **self.auth)
        self.assertEqual(response.status_code, 404)


class StationsListTests(AuthedClient):
    """GET /api/stations - the From/To picker's data source. No test at
    all before this. Lines 222-229."""

    def test_lists_every_station_by_name(self):
        Station.objects.create(name="Sylhet", code="SYL", division="Sylhet")

        response = self.client.get("/api/stations", **self.auth)

        self.assertEqual(response.status_code, 200)
        names = [s["name"] for s in response.json()["stations"]]
        self.assertEqual(names, sorted(names))  # ordered by name
        self.assertIn("Sylhet", names)


class TrainSearchValidationTests(AuthedClient):
    """GET /api/trains/search - both rejection branches, and the loop that
    skips a train not on the searched route, had no test. Lines 241-244, 249-250."""

    def test_a_missing_parameter_is_rejected(self):
        response = self.client.get("/api/trains/search?from=DHKA&to=CTG", **self.auth)
        self.assertEqual(response.status_code, 400)

    def test_searching_a_station_against_itself_is_rejected(self):
        response = self.client.get(
            "/api/trains/search?from=DHKA&to=DHKA&date=1 Aug 2026", **self.auth
        )
        self.assertEqual(response.status_code, 400)

    def test_a_train_not_on_the_searched_route_is_left_out(self):
        """The one existing search test's fixture has a single train, so the
        branch that skips a non-matching one never ran. Add a second train
        that shares no stations with the search and confirm it's absent."""
        make_train_stop(
            self.train, Station.objects.create(name="Sylhet", code="SYL"),
            sequence=2, distance_km=999,
        )
        from .builders import make_train

        other = make_train(number="999", name="Unrelated Express")
        # No TrainStop rows for `other` at DHKA or CTG - it must be excluded.

        response = self.client.get(
            "/api/trains/search?from=DHKA&to=CTG&date=1 Aug 2026", **self.auth
        )
        numbers = [t["number"] for t in response.json()["trains"]]
        self.assertNotIn(other.number, numbers)
        self.assertIn(self.train.number, numbers)


class FirstBookingCreatesAPassengerTests(TestCase):
    """_passenger_for()'s fallback has two branches: reuse an unclaimed
    Passenger row left over from somewhere else, or - if there truly isn't
    one - create a fresh one. Every fixture in the rest of the suite goes
    through make_passenger_account(), which always creates a Passenger row
    (linked or not), so the true creation branch was never reached. This
    builds a Profile with no Passenger anywhere behind it to reach it.
    Lines 210-215."""

    def test_a_passengers_first_ever_booking_creates_their_passenger_row(self):
        from django.contrib.auth.models import User

        from core.models import Profile
        from .builders import PASSWORD

        train, origin, destination = make_booked_route()

        user = User.objects.create_user(
            username="+8801900000000", password=PASSWORD
        )
        profile = Profile.objects.create(
            user=user,
            role=Profile.ROLE_PASSENGER,
            phone_number="+8801900000000",
            nid_number="3030303030",
            is_phone_verified=True,
            passenger=None,
        )
        token, _ = Token.objects.get_or_create(user=profile.user)

        self.assertEqual(
            Passenger.objects.filter(phone="+8801900000000").count(), 0
        )

        response = self.client.post(
            "/api/bookings",
            data=json.dumps(
                {
                    "trainId": train.id,
                    "date": "1 Aug 2026",
                    "from": "DHKA",
                    "to": "CTG",
                    "seatClass": "SHOVAN",
                    "passengers": [{"name": "First Timer"}],
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token.key}",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            Passenger.objects.filter(phone="+8801900000000").count(), 1
        )
