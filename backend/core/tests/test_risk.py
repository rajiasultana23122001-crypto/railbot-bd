"""The Risk Agent - the one agent with no coverage until now.

It is the only agent whose decision comes from a trained model rather than
from a rule, which makes it the one where "what did it decide" and "why"
are hardest to read off the code. The model itself is not the subject here:
these tests stub predict_proba and check what the agent does with a
probability, so they run identically on a fresh clone with no .pkl built.

Two properties matter most, and both are about not crying wolf:

  * a warning is raised once, not on every cycle
  * a warning is withdrawn when the risk goes away, rather than standing
    forever because nothing was watching for the opposite case
"""

from unittest import mock

import numpy as np
from django.test import TestCase

from core.agents.risk_agent import RISK_THRESHOLD, RUSH_HOURS, RiskAgent
from core.models import AgentLog

from .builders import make_booking, make_passenger_account, make_train


def fixed_probability(value):
    """A stand-in model that returns the same probability for every row.

    Shaped like scikit-learn's predict_proba output - one [not-delayed,
    delayed] pair per row, as a numpy array - so the agent needs no
    knowledge that it is talking to a stub. It has to be an array rather
    than a list of lists: the agent slices the result with [:, 1], which
    is numpy syntax a plain list does not answer to.
    """

    class Stub:
        def predict_proba(self, frame):
            return np.array([[1 - value, value] for _ in range(len(frame))])

    return Stub()


class RiskAgentTests(TestCase):
    def setUp(self):
        _, self.passenger = make_passenger_account("+8801700000000", nid="1010101010")
        self.train = make_train("759", "Padma Express")
        self.booking = make_booking(
            self.train, self.passenger, scheduled_departure="23:00"
        )

    def run_with(self, probability):
        with mock.patch(
            "core.agents.risk_agent.load_model",
            return_value=fixed_probability(probability),
        ):
            return RiskAgent().run()

    def test_a_journey_over_the_threshold_is_flagged(self):
        result = self.run_with(0.85)
        self.booking.refresh_from_db()

        self.assertEqual(self.booking.status, "at-risk")
        self.assertIn("Padma Express", result["flagged"])
        self.assertIn("85%", self.booking.agent_note)

    def test_a_quiet_journey_is_left_alone(self):
        result = self.run_with(0.10)
        self.booking.refresh_from_db()

        self.assertEqual(self.booking.status, "on-time")
        self.assertEqual(result["flagged"], [])
        self.assertIsNone(self.booking.agent_note)

    def test_the_threshold_boundary(self):
        """0.60 flags, 0.59 does not. The threshold is a published number in
        this system - the note tells the passenger the percentage - so which
        side of it counts has to be pinned down."""
        for probability, expected in [
            (RISK_THRESHOLD - 0.01, "on-time"),
            (RISK_THRESHOLD, "at-risk"),
            (RISK_THRESHOLD + 0.01, "at-risk"),
        ]:
            with self.subTest(probability=probability):
                self.booking.status = "on-time"
                self.booking.agent_note = None
                self.booking.save()

                self.run_with(probability)
                self.booking.refresh_from_db()
                self.assertEqual(self.booking.status, expected)

    def test_a_standing_warning_is_not_raised_again(self):
        """Same rule as the Manager and Resource agents: on a timer, a
        condition that has not changed must not keep writing to the log."""
        self.run_with(0.85)
        before = AgentLog.objects.count()

        second = self.run_with(0.85)

        self.assertEqual(second["flagged"], [])
        self.assertEqual(AgentLog.objects.count(), before)

    def test_a_warning_is_withdrawn_when_the_risk_passes(self):
        """The half that is easy to forget. A forecast that clears has to
        take the warning with it, or the dashboard shows a permanent
        at-risk badge nobody can explain."""
        self.run_with(0.85)

        result = self.run_with(0.05)
        self.booking.refresh_from_db()

        self.assertEqual(self.booking.status, "on-time")
        self.assertIn("Padma Express", result["cleared"])
        self.assertIsNone(self.booking.agent_note)

    def test_a_journey_already_delayed_is_not_examined(self):
        """Predicting whether a train might be late is pointless once it
        demonstrably is - and overwriting the Manager Agent's note with a
        probability would replace real news with a guess."""
        self.booking.status = "delayed"
        self.booking.delay_minutes = 40
        self.booking.agent_note = "Manager Agent texted you about the 40 minute delay."
        self.booking.save()

        result = self.run_with(0.95)
        self.booking.refresh_from_db()

        self.assertEqual(result["examined"], 0)
        self.assertEqual(self.booking.status, "delayed")
        self.assertIn("Manager Agent", self.booking.agent_note)

    def test_nothing_to_examine_needs_no_model_at_all(self):
        """An empty database must not raise FileNotFoundError. reason()
        returns early before load_model() - a fresh install with no .pkl
        built should still answer /api/agents/run rather than 503."""
        self.booking.delete()

        with mock.patch("core.agents.risk_agent.load_model") as loader:
            result = RiskAgent().run()

        loader.assert_not_called()
        self.assertEqual(result["examined"], 0)


class RiskFeatureTests(TestCase):
    """The six features the model is handed, assembled from the booking."""

    def setUp(self):
        _, self.passenger = make_passenger_account("+8801700000000", nid="1010101010")

    def test_rush_hour_is_derived_from_the_departure_time(self):
        train = make_train("701", "Subarna Express", halts=8, distance=320)
        make_booking(train, self.passenger, scheduled_departure="18:45")

        observation = RiskAgent().observe()
        features = observation[0]["features"]

        self.assertEqual(features["is_rush_hour"], 1)
        self.assertIn(18, RUSH_HOURS)

    def test_an_off_peak_departure_is_not_rush_hour(self):
        train = make_train("705", "Ekota Express")
        make_booking(train, self.passenger, scheduled_departure="13:20")

        self.assertEqual(RiskAgent().observe()[0]["features"]["is_rush_hour"], 0)

    def test_route_facts_come_from_the_train_not_the_booking(self):
        train = make_train("725", "Padma Express", halts=11, distance=410)
        make_booking(train, self.passenger)

        features = RiskAgent().observe()[0]["features"]

        self.assertEqual(features["distance_km"], 410)
        self.assertEqual(features["scheduled_halts"], 11)

    def test_the_same_route_reports_the_same_weather_within_a_run(self):
        """Weather is seeded per destination on purpose. If it changed on
        every observation, two agents looking at one train would disagree
        and the dashboard would flicker between forecasts."""
        train = make_train("701", "Subarna Express")
        make_booking(train, self.passenger)

        first = RiskAgent().observe()[0]["features"]["weather"]
        second = RiskAgent().observe()[0]["features"]["weather"]

        self.assertEqual(first, second)
