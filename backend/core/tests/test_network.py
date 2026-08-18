"""The computation inside core/data/network.py - 31% covered before this
file, because every test that touches the network goes through the models
built from it, never the functions themselves. Distance math, time
formatting, and per-stop schedule derivation are pure functions with no
Django dependency, which makes them cheap to test directly rather than
only indirectly through whatever `manage.py seed` happens to produce.
"""

from django.test import SimpleTestCase

from core.data.network import (
    STATIONS,
    _fmt_minutes,
    _haversine_km,
    build_stops,
    seat_classes_for,
)


class HaversineTests(SimpleTestCase):
    """Great-circle distance between two STATIONS entries."""

    def test_a_station_is_zero_km_from_itself(self):
        self.assertEqual(_haversine_km("Dhaka (Kamalapur)", "Dhaka (Kamalapur)"), 0)

    def test_distance_does_not_depend_on_direction(self):
        a_to_b = _haversine_km("Dhaka (Kamalapur)", "Chattogram")
        b_to_a = _haversine_km("Chattogram", "Dhaka (Kamalapur)")
        self.assertAlmostEqual(a_to_b, b_to_a, places=6)

    def test_a_known_pair_is_in_the_right_ballpark(self):
        """Dhaka to Chattogram is roughly 240 km as the crow flies - the
        train route is 320 km because it isn't straight. This just confirms
        the coordinates and the formula agree with known geography, not the
        exact figure."""
        km = _haversine_km("Dhaka (Kamalapur)", "Chattogram")
        self.assertGreater(km, 200)
        self.assertLess(km, 280)

    def test_every_station_used_by_a_train_has_coordinates(self):
        """A route naming a station STATIONS doesn't have would fail with a
        KeyError the moment build_stops ran for it - at seed time, not at
        review time. Catch that here instead."""
        from core.data.network import TRAINS

        for _, _, route, _, _ in TRAINS:
            for name in route:
                with self.subTest(station=name):
                    self.assertIn(name, STATIONS)


class FormatMinutesTests(SimpleTestCase):
    """Minutes-of-day, wrapped, as HH:MM."""

    def test_midnight(self):
        self.assertEqual(_fmt_minutes(0), "00:00")

    def test_an_ordinary_time(self):
        self.assertEqual(_fmt_minutes(9 * 60 + 5), "09:05")

    def test_wraps_past_midnight_into_the_next_day(self):
        """The one figure worth pinning down: a train whose running time
        pushes it past 24:00 must land back at 00:xx, not read as 24:xx or
        go negative."""
        self.assertEqual(_fmt_minutes(24 * 60 + 30), "00:30")

    def test_wraps_a_second_time_round(self):
        self.assertEqual(_fmt_minutes(48 * 60 + 15), "00:15")

    def test_the_last_minute_of_a_day(self):
        self.assertEqual(_fmt_minutes(24 * 60 - 1), "23:59")


class SeatClassesForTests(SimpleTestCase):
    """Which seat classes a train sells, by its train number."""

    def test_a_no_ac_train_sells_no_premium_classes(self):
        classes = seat_classes_for("737")
        self.assertNotIn("AC_B", classes)
        self.assertIn("SHOVAN", classes)

    def test_an_ordinary_train_sells_the_standard_set(self):
        classes = seat_classes_for("701")
        self.assertIn("AC_B", classes)
        self.assertIn("SHOVAN", classes)

    def test_an_unknown_number_still_returns_something_bookable(self):
        """A train number the seed data has never used - the fallback path,
        so a new train added later doesn't come back with no seat classes
        at all."""
        self.assertTrue(len(seat_classes_for("000000")) > 0)


class BuildStopsTests(SimpleTestCase):
    """Per-stop schedule derivation - the function every train's timetable
    actually comes from."""

    ROUTE = ["Dhaka (Kamalapur)", "Biman Bandar", "Feni", "Chattogram"]

    def test_the_first_stop_has_no_arrival(self):
        stops = build_stops(self.ROUTE, 320, "701")
        self.assertIsNone(stops[0][2])  # arrival

    def test_the_last_stop_has_no_departure(self):
        stops = build_stops(self.ROUTE, 320, "701")
        self.assertIsNone(stops[-1][3])  # departure

    def test_cumulative_distance_reaches_the_trains_own_total(self):
        """Distances are haversine, scaled to match distance_km exactly -
        the whole reason to scale rather than use raw haversine values."""
        stops = build_stops(self.ROUTE, 320, "701")
        self.assertAlmostEqual(stops[-1][1], 320, places=1)

    def test_cumulative_distance_only_increases(self):
        stops = build_stops(self.ROUTE, 320, "701")
        distances = [s[1] for s in stops]
        self.assertEqual(distances, sorted(distances))

    def test_the_same_train_number_produces_the_same_schedule_twice(self):
        """Seeding is meant to be repeatable - re-running it must not hand
        out a different timetable each time."""
        first = build_stops(self.ROUTE, 320, "701")
        second = build_stops(self.ROUTE, 320, "701")
        self.assertEqual(first, second)

    def test_two_different_train_numbers_are_not_forced_onto_one_schedule(self):
        a = build_stops(self.ROUTE, 320, "701")
        b = build_stops(self.ROUTE, 320, "759")
        self.assertNotEqual([s[3] for s in a], [s[3] for s in b])

    def test_every_intermediate_stop_has_both_an_arrival_and_a_departure(self):
        stops = build_stops(self.ROUTE, 320, "701")
        for station, _, arrival, departure in stops[1:-1]:
            with self.subTest(station=station):
                self.assertIsNotNone(arrival)
                self.assertIsNotNone(departure)

    def test_a_train_whose_schedule_crosses_midnight_still_produces_hhmm(self):
        """A late-departing train (high minutes-of-day seed) running a long
        route can cross 24:00 partway through. Every stop must still come
        back as a valid HH:MM, not a raw minute count over 1440."""
        long_route = [
            "Dhaka (Kamalapur)", "Biman Bandar", "Tangail", "Santahar",
            "Parbatipur", "Dinajpur", "Panchagarh",
        ]
        stops = build_stops(long_route, 480, "793")
        for station, _, arrival, departure in stops:
            for value in (arrival, departure):
                if value is None:
                    continue
                with self.subTest(station=station, value=value):
                    hours, minutes = value.split(":")
                    self.assertTrue(0 <= int(hours) <= 23)
                    self.assertTrue(0 <= int(minutes) <= 59)
