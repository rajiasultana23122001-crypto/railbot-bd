"""The Advisor Agent's briefing, with and without a Gemini key.

Two things are being defended. First, that the model is optional: no key,
a bad key, a timeout or a blocked response all end at the same deterministic
paragraph, and the agent cycle behaves identically either way. Second, that
the model is never given authority - it phrases figures the other agents
produced, and nothing it returns is written back to a train, a platform or
a booking.
"""

import os
from unittest import mock

import requests
from django.test import TestCase

from core.agents.advisor_agent import AdvisorAgent
from core.models import AgentLog, Booking, Platform
from core.services import gemini

from .builders import make_booking, make_passenger_account, make_platform, make_station, make_train

FACTS = {
    "total_decisions": 9,
    "high_severity": 2,
    "delayed": 1,
    "at_risk": 1,
    "by_agent": {"Manager Agent": 3, "Resource Agent": 4},
    "suggestions": ["Platform 6 triggered 2 crowding alerts."],
}


def fake_response(text):
    """A Gemini reply shaped the way the REST API actually returns one."""
    response = mock.Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": text}]}}]
    }
    return response


class BriefingWithoutAKeyTests(TestCase):
    def setUp(self):
        # The suite must not depend on the developer's own environment.
        patcher = mock.patch.dict(os.environ, {}, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("GEMINI_API_KEY", None)

    def test_writes_a_briefing_from_the_figures_and_says_it_is_the_template(self):
        text, source = gemini.write_briefing(FACTS)

        self.assertEqual(source, "template")
        self.assertIn("1 journey(s) running late", text)
        self.assertIn("9 agent decisions", text)

    def test_the_same_figures_always_produce_the_same_paragraph(self):
        """Determinism is what lets the cycle settle - see the convergence test."""
        self.assertEqual(
            gemini.write_briefing(FACTS)[0], gemini.write_briefing(FACTS)[0]
        )

    def test_a_quiet_shift_reads_as_a_quiet_shift(self):
        quiet = {**FACTS, "delayed": 0, "at_risk": 0, "high_severity": 0, "suggestions": []}
        text, _ = gemini.write_briefing(quiet)

        self.assertIn("No journey is late or at risk", text)
        self.assertIn("Nothing needs a decision", text)

    def test_no_network_call_is_attempted_without_a_key(self):
        with mock.patch("core.services.gemini.requests.post") as post:
            gemini.write_briefing(FACTS)
        post.assert_not_called()


class BriefingWithAKeyTests(TestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_uses_the_models_words_when_the_call_succeeds(self):
        with mock.patch(
            "core.services.gemini.requests.post",
            return_value=fake_response("One train is late and platform 6 is filling."),
        ):
            text, source = gemini.write_briefing(FACTS)

        self.assertEqual(source, "gemini")
        self.assertEqual(text, "One train is late and platform 6 is filling.")

    def test_the_prompt_carries_the_figures_and_forbids_inventing_more(self):
        """The grounding is the safety property, so it is asserted, not assumed."""
        with mock.patch(
            "core.services.gemini.requests.post", return_value=fake_response("ok")
        ) as post:
            gemini.write_briefing(FACTS)

        prompt = post.call_args.kwargs["json"]["contents"][0]["parts"][0]["text"]
        self.assertIn("do not invent trains", prompt)
        self.assertIn("Journeys currently delayed: 1", prompt)
        self.assertIn("Platform 6 triggered 2 crowding alerts.", prompt)

    def test_a_network_failure_falls_back_instead_of_raising(self):
        with mock.patch(
            "core.services.gemini.requests.post",
            side_effect=requests.Timeout("took too long"),
        ):
            text, source = gemini.write_briefing(FACTS)

        self.assertEqual(source, "template")
        self.assertIn("agent decisions", text)

    def test_an_http_error_falls_back(self):
        failing = mock.Mock()
        failing.raise_for_status.side_effect = requests.HTTPError("401 Unauthorized")

        with mock.patch("core.services.gemini.requests.post", return_value=failing):
            _, source = gemini.write_briefing(FACTS)

        self.assertEqual(source, "template")

    def test_a_blocked_or_empty_answer_falls_back(self):
        """A safety-blocked reply arrives as a response with no candidates."""
        blocked = mock.Mock()
        blocked.raise_for_status.return_value = None
        blocked.json.return_value = {"promptFeedback": {"blockReason": "SAFETY"}}

        with mock.patch("core.services.gemini.requests.post", return_value=blocked):
            text, source = gemini.write_briefing(FACTS)

        self.assertEqual(source, "template")
        self.assertIn("agent decisions", text)


class AdvisorAgentBriefingTests(TestCase):
    """The agent's own behaviour, which must not depend on the key either."""

    def setUp(self):
        _, passenger = make_passenger_account("+8801700000000", nid="1010101010")
        train = make_train("709", "Parabat Express", halts=10)
        make_booking(
            train,
            passenger,
            status="delayed",
            delay_minutes=35,
            scheduled_departure="18:45",
            expected_departure="19:20",
        )
        station = make_station()
        make_platform(station, number="6", occupancy=585, capacity=650)

    def test_briefs_when_there_was_something_to_report(self):
        result = AdvisorAgent().run()

        self.assertGreater(result["newlyLogged"], 0)
        self.assertTrue(result["briefing"])
        self.assertEqual(result["briefingSource"], "template")
        # And it reached the audit trail the station master reads.
        self.assertTrue(
            AgentLog.objects.filter(
                agent="Advisor Agent", message=result["briefing"]
            ).exists()
        )

    def test_says_nothing_when_the_shift_has_not_changed(self):
        """Otherwise a varying paragraph every cycle would grow the log
        forever and the system would never settle."""
        AdvisorAgent().run()
        settled = AgentLog.objects.count()

        second = AdvisorAgent().run()

        self.assertEqual(second["newlyLogged"], 0)
        self.assertIsNone(second["briefing"])
        self.assertEqual(AgentLog.objects.count(), settled)

    def test_the_model_never_writes_to_operational_data(self):
        """The boundary the whole design rests on.

        Gemini returns something that reads like an instruction; nothing in
        the system acts on it. Trains, platforms and bookings are compared
        before and after, and only the log may differ.
        """
        booking_before = list(Booking.objects.values())
        platform_before = list(Platform.objects.values())

        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}), mock.patch(
            "core.services.gemini.requests.post",
            return_value=fake_response(
                "Move Parabat Express to platform 1 and cancel the delay notice."
            ),
        ):
            result = AdvisorAgent().run()

        self.assertEqual(result["briefingSource"], "gemini")
        self.assertEqual(list(Booking.objects.values()), booking_before)
        self.assertEqual(list(Platform.objects.values()), platform_before)
