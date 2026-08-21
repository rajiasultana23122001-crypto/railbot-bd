"""How seat availability is counted, and how much it costs to count.

Free seats are never stored - every route search, seat map and booking
attempt recounts them off the confirmed bookings for a train/date/class.
That makes this the hottest read in the app, so these tests defend two
separate things: that the count is right, and that it does not go back to
the database once per seat class or once per train. The query-count tests
are here because an N+1 reintroduced by a later refactor still passes
every correctness test in the suite.
"""

import json

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from rest_framework.authtoken.models import Token

from core.models import Booking, Station, Train, TrainStop
from core.services.booking import availability_by_class, available_seats, ordered_stops

from .builders import (
    make_booked_route,
    make_booking,
    make_passenger_account,
    make_train,
    make_train_stop,
)

DATE = "1 Aug 2026"


class AvailabilityCountTests(TestCase):
    """make_booked_route sells 2 SHOVAN and 2 SNIGDHA seats."""

    def setUp(self):
        self.train, _, _ = make_booked_route()
        self.profile, self.passenger = make_passenger_account("+8801700000000")

    def hold(self, seat_class, seats, status="confirmed", date=DATE):
        return make_booking(
            self.train,
            self.passenger,
            travel_date=date,
            seat_class=seat_class,
            seat_numbers=seats,
            booking_status=status,
        )

    def test_it_answers_for_every_class_asked_about(self):
        availability = availability_by_class(self.train, ["SHOVAN", "SNIGDHA"], DATE)

        self.assertEqual(
            availability,
            {
                "SHOVAN": (2, ["SHOVAN-1", "SHOVAN-2"]),
                "SNIGDHA": (2, ["SNIGDHA-1", "SNIGDHA-2"]),
            },
        )

    def test_a_seat_held_in_one_class_leaves_the_other_class_alone(self):
        """The bug a per-class loop cannot have but a single bucketed query
        can: bookings coming back in one result set and being counted
        against the wrong class."""
        self.hold("SHOVAN", ["SHOVAN-1"])

        availability = availability_by_class(self.train, ["SHOVAN", "SNIGDHA"], DATE)

        self.assertEqual(availability["SHOVAN"], (2, ["SHOVAN-2"]))
        self.assertEqual(availability["SNIGDHA"], (2, ["SNIGDHA-1", "SNIGDHA-2"]))

    def test_a_cancelled_booking_gives_its_seat_back(self):
        self.hold("SHOVAN", ["SHOVAN-1"], status="cancelled")

        self.assertEqual(
            availability_by_class(self.train, ["SHOVAN"], DATE)["SHOVAN"],
            (2, ["SHOVAN-1", "SHOVAN-2"]),
        )

    def test_a_seat_held_on_another_date_does_not_count(self):
        self.hold("SHOVAN", ["SHOVAN-1"], date="2 Aug 2026")

        self.assertEqual(
            availability_by_class(self.train, ["SHOVAN"], DATE)["SHOVAN"],
            (2, ["SHOVAN-1", "SHOVAN-2"]),
        )

    def test_a_class_the_train_does_not_sell_has_no_seats_rather_than_erroring(self):
        self.assertEqual(
            availability_by_class(self.train, ["AC_B"], DATE)["AC_B"], (0, [])
        )

    def test_available_seats_agrees_with_the_bucketed_answer(self):
        """available_seats is now the one-class case of availability_by_class.
        If the two ever disagree, the seat map and the search result are
        showing a passenger different things about the same train."""
        self.hold("SNIGDHA", ["SNIGDHA-2"])

        self.assertEqual(
            available_seats(self.train, "SNIGDHA", DATE),
            availability_by_class(self.train, ["SNIGDHA"], DATE)["SNIGDHA"],
        )

    def test_one_query_covers_every_class_asked_about(self):
        with self.assertNumQueries(1):
            availability_by_class(self.train, ["SHOVAN", "SNIGDHA"], DATE)


class OrderedStopsTests(TestCase):
    def setUp(self):
        self.train, _, _ = make_booked_route()

    def test_a_prefetched_train_needs_no_further_queries(self):
        train = Train.objects.prefetch_related("stops__station").get(pk=self.train.pk)

        with self.assertNumQueries(0):
            stops = ordered_stops(train)
            self.assertEqual([stop.station.code for stop in stops], ["DHKA", "CTG"])

    def test_a_train_nobody_prefetched_still_works(self):
        stops = ordered_stops(self.train)

        self.assertEqual([stop.sequence for stop in stops], [0, 1])


class SearchQueryCountTests(TestCase):
    """GET /api/trains/search over a whole timetable, not one train.

    What matters is the growth: every train here sells two classes, so
    before availability_by_class the cost rose by one query per class per
    train. Asserting the *difference* between a one-train and a three-train
    timetable keeps the test honest about what it is defending, without
    pinning the fixed overhead (auth, the train list) that has nothing to
    do with this.
    """

    def setUp(self):
        self.profile, _ = make_passenger_account("+8801700000000")
        token, _ = Token.objects.get_or_create(user=self.profile.user)
        self.auth = {"HTTP_AUTHORIZATION": f"Bearer {token.key}"}

    def build_timetable(self, train_count):
        train, origin, destination = make_booked_route()
        for index in range(1, train_count):
            extra = make_train(number=f"70{index + 1}", name=f"Express {index + 1}")
            make_train_stop(extra, origin, sequence=0, distance_km=0, departure="09:00")
            make_train_stop(
                extra, destination, sequence=1, distance_km=320, arrival="14:00"
            )

    def search_query_count(self, train_count):
        self.build_timetable(train_count)

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(
                f"/api/trains/search?from=DHKA&to=CTG&date={DATE}", **self.auth
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(json.loads(response.content)["trains"]), train_count)
        return len(queries.captured_queries)

    def test_each_extra_train_costs_one_query_not_one_per_seat_class(self):
        one_train = self.search_query_count(1)

        Booking.objects.all().delete()
        TrainStop.objects.all().delete()
        Train.objects.all().delete()
        Station.objects.all().delete()

        three_trains = self.search_query_count(3)

        self.assertEqual(three_trains - one_train, 2)
