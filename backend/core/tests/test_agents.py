"""The Observe-Reason-Act loop, and what stops it acting twice.

Agents run on a timer. Nothing outside them decides how often, so every
agent has to be safe to run again on unchanged data - otherwise a cycle
that fires every five minutes would trim the same halts forever and text
the same passenger all afternoon. That property is what most of this file
is about, and each of the three tests named "again" was written against a
bug this project actually shipped.

The Risk Agent needs a trained model on disk, which is not in version
control (ml/*.pkl is ignored - it is a build product of
`python ml/train_model.py`). Tests that need it are skipped rather than
failed when it is absent, so a fresh clone still runs green.
"""

import unittest
from unittest import mock

from django.test import TestCase

from core.agents import AGENT_ORDER, run_cycle
from core.agents.base import BaseAgent
from core.agents.manager_agent import ManagerAgent, normalize_bd_phone
from core.agents.resource_agent import ResourceAgent
from core.agents.risk_agent import MODEL_PATH
from core.agents.scheduler_agent import (
    MAX_RECOVERY_SHARE,
    SchedulerAgent,
    add_minutes,
)
from core.models import AgentLog, Booking

from .builders import make_booking, make_passenger_account, make_platform, make_station, make_train

needs_model = unittest.skipUnless(
    MODEL_PATH.exists(), f"{MODEL_PATH.name} not built - run python ml/train_model.py"
)


class ObserveReasonActTests(TestCase):
    """The architecture claim: no agent acts without first observing."""

    def test_run_calls_the_three_steps_in_order(self):
        calls = []

        class Recorder(BaseAgent):
            name = "Recorder"

            def observe(self):
                calls.append("observe")
                return "facts"

            def reason(self, observation):
                calls.append(("reason", observation))
                return "decision"

            def act(self, decision):
                calls.append(("act", decision))
                return {"done": True}

        result = Recorder().run()

        self.assertEqual(calls[0], "observe")
        # Each step is handed exactly what the one before it returned, which
        # is what makes the pipeline a pipeline rather than three functions.
        self.assertEqual(calls[1], ("reason", "facts"))
        self.assertEqual(calls[2], ("act", "decision"))
        self.assertEqual(result, {"agent": "Recorder", "done": True})

    def test_every_agent_implements_all_three_steps(self):
        for agent_class in AGENT_ORDER:
            with self.subTest(agent=agent_class.name):
                for step in ("observe", "reason", "act"):
                    self.assertNotEqual(
                        getattr(agent_class, step),
                        getattr(BaseAgent, step),
                        f"{agent_class.name} never overrode {step}()",
                    )

    def test_acting_writes_to_the_audit_trail(self):
        station = make_station()
        make_platform(station, number="6", occupancy=585, capacity=650)

        self.assertEqual(AgentLog.objects.count(), 0)
        ResourceAgent().run()
        self.assertEqual(AgentLog.objects.filter(agent="Resource Agent").count(), 1)


class AddMinutesTests(TestCase):
    """Timetable arithmetic on HH:MM strings, including past midnight."""

    def test_shifts_forward_and_backward(self):
        self.assertEqual(add_minutes("07:00", 35), "07:35")
        self.assertEqual(add_minutes("19:20", -12), "19:08")

    def test_wraps_around_midnight_in_both_directions(self):
        self.assertEqual(add_minutes("23:50", 20), "00:10")
        self.assertEqual(add_minutes("00:05", -10), "23:55")


class SchedulerAgentTests(TestCase):
    def setUp(self):
        _, self.passenger = make_passenger_account("+8801700000000", nid="1010101010")
        # 10 halts: 8 are trimmable, at 1.5 min each, so 12 minutes are
        # physically available to recover.
        self.train = make_train("709", "Parabat Express", halts=10)

    def delayed_booking(self, minutes):
        return make_booking(
            self.train,
            self.passenger,
            status="delayed",
            delay_minutes=minutes,
            scheduled_departure="18:45",
            expected_departure=add_minutes("18:45", minutes),
        )

    def test_recovers_time_by_trimming_minor_halts(self):
        booking = self.delayed_booking(35)

        SchedulerAgent().run()
        booking.refresh_from_db()

        self.assertEqual(booking.recovered_minutes, 12)
        self.assertEqual(booking.expected_departure, "19:08")
        # The original slip is left alone; only the shortfall shrinks.
        self.assertEqual(booking.delay_minutes, 35)
        self.assertEqual(booking.current_delay, 23)

    def test_never_recovers_more_than_the_agreed_share_of_the_delay(self):
        """A believable timetable matters more than a flattering one.

        The train could physically save 12 minutes, but on a 10-minute delay
        the cap allows 4 - past that the printed time stops being credible.
        """
        booking = self.delayed_booking(10)

        SchedulerAgent().run()
        booking.refresh_from_db()

        self.assertEqual(booking.recovered_minutes, int(10 * MAX_RECOVERY_SHARE))
        self.assertLessEqual(booking.recovered_minutes, booking.delay_minutes)

    def test_running_again_stops_at_the_cap_instead_of_trimming_forever(self):
        """The bug: the budget was sized against the *remaining* delay, so
        every cycle found more to save and the delay melted away to nothing.

        Note this settles over two cycles rather than one: a cycle can only
        trim the halts it has (12 minutes' worth), and the cap on a 35-minute
        delay is 14, so the second cycle takes the last 2 and every cycle
        after that finds nothing left to take.
        """
        booking = self.delayed_booking(35)
        cap = int(35 * MAX_RECOVERY_SHARE)

        for _ in range(6):
            SchedulerAgent().run()
        booking.refresh_from_db()

        self.assertEqual(booking.recovered_minutes, cap)
        self.assertEqual(booking.expected_departure, "19:06")
        # The journey is still reported late, which is the honest outcome -
        # the runaway version made a 35-minute delay disappear entirely.
        self.assertEqual(booking.current_delay, 35 - cap)

    def test_a_settled_journey_is_left_untouched_by_further_cycles(self):
        booking = self.delayed_booking(35)
        for _ in range(2):
            SchedulerAgent().run()
        booking.refresh_from_db()
        settled = (booking.recovered_minutes, booking.expected_departure)

        result = SchedulerAgent().run()
        booking.refresh_from_db()

        self.assertEqual(result["adjusted"], [])
        self.assertEqual((booking.recovered_minutes, booking.expected_departure), settled)

    def test_leaves_on_time_journeys_alone(self):
        booking = make_booking(self.train, self.passenger)

        result = SchedulerAgent().run()
        booking.refresh_from_db()

        self.assertEqual(result["adjusted"], [])
        self.assertEqual(booking.expected_departure, "07:00")

    def test_a_cancelled_booking_is_left_alone_even_if_delayed(self):
        """Cancelling is the passenger's own action, not a delay state - a
        cancelled ticket should never come back to life with a recovered
        departure time."""
        booking = self.delayed_booking(35)
        booking.booking_status = "cancelled"
        booking.save()

        result = SchedulerAgent().run()
        booking.refresh_from_db()

        self.assertEqual(result["adjusted"], [])
        self.assertEqual(booking.recovered_minutes, 0)


class ManagerAgentTests(TestCase):
    def setUp(self):
        _, self.passenger = make_passenger_account("+8801700000000", nid="1010101010")
        self.train = make_train("709", "Parabat Express", halts=10)
        self.booking = make_booking(
            self.train,
            self.passenger,
            status="delayed",
            delay_minutes=35,
            scheduled_departure="18:45",
            expected_departure="19:20",
        )

    def test_texts_a_passenger_holding_no_time_at_all(self):
        result = ManagerAgent().run()
        self.booking.refresh_from_db()

        self.assertEqual(len(result["called"]), 1)
        self.assertEqual(self.booking.notified_departure, "19:20")
        self.assertIn("35 minute delay", self.booking.agent_note)

    def test_does_not_text_again_when_nothing_changed(self):
        """The bug: the agent only checked *that* a call went out, never
        whether the time it announced was still the current one."""
        ManagerAgent().run()
        second = ManagerAgent().run()

        self.assertEqual(second["examined"], 0)
        self.assertEqual(second["called"], [])

    def test_texts_again_when_the_scheduler_moves_the_departure(self):
        """The other half of the same rule - silence must not be permanent."""
        ManagerAgent().run()

        # Reload first: the agent wrote notified_departure, and saving a stale
        # copy of this row would blank it out and quietly defeat the test.
        self.booking.refresh_from_db()

        # The Scheduler claws back 12 minutes; the passenger now holds a time
        # that is no longer true.
        self.booking.expected_departure = "19:08"
        self.booking.recovered_minutes = 12
        self.booking.save()

        result = ManagerAgent().run()
        self.booking.refresh_from_db()

        self.assertEqual(len(result["called"]), 1)
        self.assertEqual(self.booking.notified_departure, "19:08")
        # And it reads as a correction, not as first news.
        self.assertIn("updated departure time", self.booking.agent_note)

    def test_a_failed_send_leaves_the_booking_ready_for_a_retry(self):
        """Marking a passenger as told when nothing was sent is the worst
        possible failure here - they would never be told at all."""
        with mock.patch(
            "core.agents.manager_agent.send_sms", return_value=(False, "network down")
        ):
            result = ManagerAgent().run()

        self.booking.refresh_from_db()
        self.assertEqual(result["called"], [])
        self.assertIsNone(self.booking.notified_departure)

        # The next cycle, with the network back, still finds it.
        self.assertEqual(len(ManagerAgent().run()["called"]), 1)

    def test_does_not_text_a_cancelled_booking(self):
        self.booking.booking_status = "cancelled"
        self.booking.save()

        result = ManagerAgent().run()

        self.assertEqual(result["called"], [])


class PhoneNumberTests(TestCase):
    """The shapes a Bangladeshi number is actually stored in."""

    def test_normalizes_every_accepted_form_to_one(self):
        for raw in ("+8801700000000", "8801700000000", "880 1700-000000", "01700000000"):
            with self.subTest(raw=raw):
                self.assertEqual(normalize_bd_phone(raw), "8801700000000")

    def test_handles_a_local_number_with_no_leading_zero(self):
        self.assertEqual(normalize_bd_phone("1700000000"), "8801700000000")


class ResourceAgentTests(TestCase):
    def setUp(self):
        self.station = make_station()

    def test_raises_a_critical_alert_on_a_platform_over_ninety_percent(self):
        make_platform(self.station, number="6", occupancy=585, capacity=650)

        result = ResourceAgent().run()

        self.assertEqual(len(result["alerts"]), 1)
        self.assertEqual(result["alerts"][0]["level"], "critical")
        self.assertEqual(AgentLog.objects.filter(severity="high").count(), 1)

    def test_does_not_repeat_an_alert_for_a_platform_that_has_not_changed(self):
        """The bug: a crowded platform re-logged the same alert every cycle,
        burying everything else in the station master's feed."""
        make_platform(self.station, number="6", occupancy=585, capacity=650)

        ResourceAgent().run()
        for _ in range(4):
            ResourceAgent().run()

        self.assertEqual(AgentLog.objects.count(), 1)

    def test_says_so_when_a_platform_eases_off(self):
        """Silence would leave staff standing at a platform that emptied."""
        platform = make_platform(self.station, number="6", occupancy=585, capacity=650)
        ResourceAgent().run()

        # Reload before touching it: the agent recorded the alert level on
        # this row, and writing back a stale copy would erase it.
        platform.refresh_from_db()
        platform.occupancy = 120
        platform.save()
        result = ResourceAgent().run()

        self.assertEqual(result["alerts"][0]["level"], "clear")
        self.assertEqual(AgentLog.objects.count(), 2)

    def test_a_quiet_platform_raises_nothing_at_all(self):
        make_platform(self.station, number="5", occupancy=95, capacity=500)

        ResourceAgent().run()

        self.assertEqual(AgentLog.objects.count(), 0)


@needs_model
class FullCycleTests(TestCase):
    """All five agents together, which is how they actually run."""

    def setUp(self):
        _, self.passenger = make_passenger_account("+8801700000000", nid="1010101010")
        self.train = make_train("709", "Parabat Express", halts=10)
        self.booking = make_booking(
            self.train,
            self.passenger,
            status="delayed",
            delay_minutes=35,
            scheduled_departure="18:45",
            expected_departure="19:20",
        )
        station = make_station()
        make_platform(station, number="6", occupancy=585, capacity=650)

    def test_one_cycle_recovers_time_and_tells_the_passenger_the_new_one(self):
        """Order matters: the Manager must announce the time the Scheduler
        settled on, not the one it was about to change."""
        run_cycle()
        self.booking.refresh_from_db()

        self.assertEqual(self.booking.expected_departure, "19:08")
        self.assertEqual(self.booking.notified_departure, "19:08")

    def test_the_cycle_converges_and_then_stays_quiet(self):
        """The property that makes running this on a five-minute timer safe.

        Not "the second cycle is silent": the Scheduler needs two passes to
        reach its recovery cap, and the Manager is right to text again about
        the time that changed on the way. What matters is that the system
        settles at all, and then stops talking.
        """
        counts = []
        for _ in range(6):
            run_cycle()
            counts.append(AgentLog.objects.count())

        self.assertGreater(counts[0], 0, "the first cycle should have done something")
        # Settled by the third pass, and every pass after it added nothing.
        self.assertEqual(counts[2:], [counts[2]] * 4, f"still acting: {counts}")

    def test_every_agent_reports_back(self):
        results = run_cycle()

        self.assertEqual(
            [r["agent"] for r in results], [a.name for a in AGENT_ORDER]
        )

    def test_a_new_delay_wakes_the_agents_up_again(self):
        """Converged must not mean deaf."""
        for _ in range(3):
            run_cycle()
        quiet = AgentLog.objects.count()

        second_train = make_train("701", "Subarna Express", halts=10)
        make_booking(
            second_train,
            self.passenger,
            status="delayed",
            delay_minutes=40,
            scheduled_departure="07:00",
            expected_departure="07:40",
        )
        run_cycle()

        self.assertGreater(AgentLog.objects.count(), quiet)
        self.assertEqual(Booking.objects.filter(recovered_minutes__gt=0).count(), 2)
