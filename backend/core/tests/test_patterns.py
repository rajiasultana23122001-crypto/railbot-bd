"""The design patterns, tested as behaviour rather than as structure.

A test that asserts a class exists proves nothing. What each pattern is for
is the ability to change one thing without touching another, so these tests
exercise that: swap a gateway without editing the agent, add an observer
without editing the base class, wrap an agent without it noticing.
"""

from unittest import mock

from django.test import TestCase

from core.agents import AgentFactory, run_cycle
from core.agents.base import BaseAgent
from core.agents.decorators import AgentDecorator, TimingAgent, with_timing
from core.agents.factory import UnknownAgentError
from core.agents.manager_agent import ManagerAgent
from core.agents.risk_agent import RiskAgent
from core.events import (
    AgentEvent,
    AgentEventBus,
    AgentObserver,
    AuditTrailObserver,
    HighSeverityObserver,
)
from core.facade import DelayReportError, RailBotFacade
from core.models import AgentLog, Booking
from core.services.gateways import (
    MessageGateway,
    SimulatedGateway,
    SmsNetBdAdapter,
    default_gateway,
)
from core.services.message_strategy import (
    CorrectionStrategy,
    FirstNoticeStrategy,
    strategy_for,
)

from .builders import (
    make_authority_account,
    make_booking,
    make_passenger_account,
    make_train,
)


# --------------------------------------------------------------------------
# Factory Method
# --------------------------------------------------------------------------
class AgentFactoryTests(TestCase):
    def test_an_agent_is_built_by_the_name_it_logs_under(self):
        """The registry key and the audit trail string are the same word, so
        an operator reading an alert and a developer calling the factory are
        not using two vocabularies."""
        agent = AgentFactory.create("Risk Agent")
        self.assertIsInstance(agent, RiskAgent)
        self.assertEqual(agent.name, "Risk Agent")

    def test_an_unknown_name_says_what_it_would_have_accepted(self):
        with self.assertRaises(UnknownAgentError) as caught:
            AgentFactory.create("Weather Agent")
        self.assertIn("Risk Agent", str(caught.exception))

    def test_the_cycle_is_built_in_the_order_a_delay_propagates(self):
        """Manager before Scheduler would text passengers times that are
        about to change, so this order is a requirement, not a preference."""
        names = [agent.name for agent in AgentFactory.create_cycle()]
        self.assertEqual(
            names,
            [
                "Risk Agent",
                "Scheduler Agent",
                "Manager Agent",
                "Resource Agent",
                "Advisor Agent",
            ],
        )

    def test_each_cycle_gets_fresh_agents(self):
        """Agents hold no state between runs. Building new ones each cycle
        means one cycle cannot be affected by what the last left behind."""
        first = AgentFactory.create_cycle()
        second = AgentFactory.create_cycle()
        for a, b in zip(first, second):
            self.assertIsNot(a, b)

    def test_a_class_that_is_not_an_agent_is_refused(self):
        class NotAnAgent:
            pass

        with self.assertRaises(TypeError):
            AgentFactory.register("Bogus Agent", NotAnAgent)


# --------------------------------------------------------------------------
# Adapter
# --------------------------------------------------------------------------
class GatewayAdapterTests(TestCase):
    def test_the_adapter_translates_the_number_shapes_actually_stored(self):
        cases = {
            "+8801700000000": "8801700000000",
            "880 1700-000000": "8801700000000",
            "01700000000": "8801700000000",
            "1700000000": "8801700000000",
        }
        for stored, expected in cases.items():
            with self.subTest(stored=stored):
                self.assertEqual(SmsNetBdAdapter.normalize(stored), expected)

    def test_a_gateway_reports_failure_rather_than_raising(self):
        """An exception here would escape run_cycle and take the Resource and
        Advisor agents down with it, over one unreachable provider."""
        import requests

        adapter = SmsNetBdAdapter(api_key="test-key")
        with mock.patch(
            "core.services.gateways.requests.get",
            side_effect=requests.RequestException("network down"),
        ):
            delivered, detail = adapter.send("+8801700000000", "hello")

        self.assertFalse(delivered)
        self.assertIn("failed", detail)

    def test_the_simulated_gateway_reports_delivered(self):
        """So the rest of the cycle behaves exactly as it would in
        production. A simulation that reported failure would exercise the
        retry path forever and tell you nothing about the normal one."""
        delivered, detail = SimulatedGateway().send("+8801700000000", "hello")
        self.assertTrue(delivered)
        self.assertIn("simulated", detail)

    def test_the_default_is_simulation_when_nothing_is_configured(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertIsInstance(default_gateway(), SimulatedGateway)

    def test_a_new_provider_needs_no_change_to_the_agent(self):
        """The point of the pattern. This test defines a gateway the codebase
        has never seen and hands it to the agent's send path."""
        sent = []

        class FirebaseStub(MessageGateway):
            name = "firebase"

            def is_configured(self):
                return True

            def send(self, phone, message):
                sent.append((phone, message))
                return True, "push delivered"

        from core.agents.manager_agent import send_sms

        delivered, detail = send_sms("+8801700000000", "hi", gateway=FirebaseStub())

        self.assertTrue(delivered)
        self.assertEqual(detail, "push delivered")
        self.assertEqual(len(sent), 1)


# --------------------------------------------------------------------------
# Strategy
# --------------------------------------------------------------------------
class NotificationStrategyTests(TestCase):
    def setUp(self):
        _, self.passenger = make_passenger_account("+8801700000000", nid="1010101010")
        self.train = make_train("701", "Subarna Express")
        self.booking = make_booking(
            self.train,
            self.passenger,
            status="delayed",
            delay_minutes=40,
            expected_departure="07:40",
        )

    def test_a_passenger_who_knows_nothing_gets_first_news(self):
        self.assertIsInstance(strategy_for(self.booking), FirstNoticeStrategy)

    def test_a_passenger_holding_a_stale_time_gets_a_correction(self):
        """Worded as a correction rather than as news, because a second
        message that reads like a first one leaves the passenger to work out
        which of the two times is current."""
        self.booking.notified_departure = "07:20"
        self.assertIsInstance(strategy_for(self.booking), CorrectionStrategy)

    def test_the_two_strategies_word_the_same_delay_differently(self):
        first = FirstNoticeStrategy().compose_sms(self.booking)
        correction = CorrectionStrategy().compose_sms(self.booking)

        self.assertNotEqual(first, correction)
        self.assertIn("updated", correction.lower())
        # Both still carry the facts a passenger needs.
        for text in (first, correction):
            self.assertIn("07:40", text)
            self.assertIn("Subarna Express", text)

    def test_a_third_kind_of_notice_is_a_new_class_not_a_new_branch(self):
        """The reason this is Strategy rather than a boolean flag."""
        from core.services.message_strategy import NotificationStrategy

        class CancellationStrategy(NotificationStrategy):
            log_label = "Cancellation"

            def compose_sms(self, booking):
                return f"RailBot: {booking.train.name} is cancelled."

            def compose_note(self, booking):
                return "Manager Agent told you this service is cancelled."

        text = CancellationStrategy().compose_sms(self.booking)
        self.assertIn("cancelled", text)


# --------------------------------------------------------------------------
# Observer
# --------------------------------------------------------------------------
class AgentEventBusTests(TestCase):
    def setUp(self):
        self.bus = AgentEventBus()

    def test_an_observer_hears_what_was_published(self):
        heard = []

        class Recorder(AgentObserver):
            def notify(self, event):
                heard.append(event)

        self.bus.subscribe(Recorder())
        self.bus.publish(AgentEvent("Risk Agent", "flagged a journey"))

        self.assertEqual(len(heard), 1)
        self.assertEqual(heard[0].agent, "Risk Agent")

    def test_a_listener_that_raises_does_not_reach_the_publisher(self):
        """The isolation that justifies the bus. A paging integration
        breaking is not a reason to lose the agent that was reporting."""
        reached = []

        class Broken(AgentObserver):
            def notify(self, event):
                raise RuntimeError("pager is down")

        class Working(AgentObserver):
            def notify(self, event):
                reached.append(event)

        self.bus.subscribe(Broken())
        self.bus.subscribe(Working())

        with self.assertLogs("core.events", level="ERROR"):
            self.bus.publish(AgentEvent("Manager Agent", "sent a text"))

        self.assertEqual(len(reached), 1)

    def test_subscribing_the_same_kind_twice_is_ignored(self):
        """ready() can run more than once per process, and a duplicate audit
        observer would write every log line twice."""
        self.bus.subscribe(AuditTrailObserver())
        self.bus.subscribe(AuditTrailObserver())

        before = AgentLog.objects.count()
        self.bus.publish(AgentEvent("Risk Agent", "flagged a journey"))

        self.assertEqual(AgentLog.objects.count(), before + 1)

    def test_only_high_severity_reaches_the_operator_observer(self):
        self.bus.subscribe(HighSeverityObserver())

        with self.assertLogs("core.events", level="WARNING"):
            self.bus.publish(AgentEvent("Manager Agent", "send failed", "high"))

        # An info event produces no warning at all, so assertLogs would fail
        # if one were emitted.
        with self.assertRaises(AssertionError):
            with self.assertLogs("core.events", level="WARNING"):
                self.bus.publish(AgentEvent("Risk Agent", "all quiet", "info"))


class AgentLoggingThroughTheBusTests(TestCase):
    """The audit trail still behaves exactly as it did before the bus."""

    def test_an_agent_log_call_still_writes_a_row_and_returns_it(self):
        class Stub(BaseAgent):
            name = "Test Agent"

        row = Stub().log("something happened", severity="medium")

        self.assertIsNotNone(row)
        self.assertEqual(row.agent, "Test Agent")
        self.assertEqual(row.severity, "medium")
        self.assertEqual(AgentLog.objects.count(), 1)


# --------------------------------------------------------------------------
# Decorator
# --------------------------------------------------------------------------
class AgentDecoratorTests(TestCase):
    def setUp(self):
        _, passenger = make_passenger_account("+8801700000000", nid="1010101010")
        train = make_train("701", "Subarna Express")
        make_booking(train, passenger, status="delayed", delay_minutes=30)

    def test_a_wrapped_agent_still_logs_under_its_own_name(self):
        """Forwarding name rather than replacing it. Otherwise the audit
        trail starts naming the decorator instead of the agent that acted."""
        wrapped = TimingAgent(ManagerAgent())
        self.assertEqual(wrapped.name, "Manager Agent")

    def test_timing_adds_a_duration_without_the_agent_knowing(self):
        result = TimingAgent(ManagerAgent()).run()

        self.assertIn("elapsedMs", result)
        self.assertGreaterEqual(result["elapsedMs"], 0)
        # The agent's own result is untouched.
        self.assertIn("called", result)

    def test_decorators_stack(self):
        from core.agents.decorators import TracingAgent

        stacked = TimingAgent(TracingAgent(ManagerAgent()))
        result = stacked.run()

        self.assertEqual(result["agent"], "Manager Agent")
        self.assertIn("elapsedMs", result)

    def test_the_agent_underneath_can_be_recovered(self):
        from core.agents.decorators import TracingAgent

        agent = ManagerAgent()
        self.assertIs(TimingAgent(TracingAgent(agent)).wrapped, agent)

    def test_a_decorated_cycle_runs_like_an_undecorated_one(self):
        results = run_cycle(with_timing(AgentFactory.create_cycle()))

        self.assertEqual(len(results), 5)
        self.assertTrue(all("elapsedMs" in r for r in results))

    def test_a_decorator_records_the_time_even_when_the_agent_fails(self):
        """An agent that is slow because it is timing out is exactly the case
        worth seeing, and that path ends in an exception, not a return."""

        class Exploding(BaseAgent):
            name = "Exploding Agent"

            def observe(self):
                raise RuntimeError("boom")

        with self.assertLogs("core.agents", level="WARNING"):
            with self.assertRaises(RuntimeError):
                TimingAgent(Exploding()).run()

    def test_the_base_decorator_forwards_everything_it_does_not_change(self):
        agent = ManagerAgent()
        passthrough = AgentDecorator(agent)

        self.assertEqual(passthrough.observe(), agent.observe())


# --------------------------------------------------------------------------
# Facade
# --------------------------------------------------------------------------
class RailBotFacadeTests(TestCase):
    def setUp(self):
        self.authority = make_authority_account("+8801900000000")
        _, self.rumi = make_passenger_account("+8801700000000", nid="1010101010")
        _, self.rajia = make_passenger_account("+8801800000000", nid="2020202020")

        self.train = make_train("701", "Subarna Express")
        self.rumi_booking = make_booking(self.train, self.rumi, scheduled_departure="07:00")
        self.rajia_booking = make_booking(self.train, self.rajia, scheduled_departure="07:00")

    def test_one_call_does_the_whole_sequence(self):
        result = RailBotFacade.report_delay("701", 60)

        self.assertEqual(result["reported"]["minutes"], 60)
        self.assertEqual(result["reported"]["passengersAffected"], 2)
        self.assertEqual(len(result["results"]), 5)

    def test_the_reported_delay_is_the_one_that_was_entered(self):
        """The Scheduler runs inside this call and pulls the departure
        earlier. What comes back under 'reported' must still be what was
        typed, or the confirmation contradicts the form."""
        result = RailBotFacade.report_delay("701", 60)

        self.assertEqual(result["reported"]["minutes"], 60)
        self.assertEqual(result["reported"]["departureAfterDelay"], "08:00")
        self.assertIn("settledDeparture", result)

    def test_every_passenger_on_the_train_is_covered(self):
        RailBotFacade.report_delay("701", 60)

        self.rumi_booking.refresh_from_db()
        self.rajia_booking.refresh_from_db()
        self.assertEqual(self.rumi_booking.status, "delayed")
        self.assertEqual(self.rajia_booking.status, "delayed")

    def test_validation_can_be_asked_for_without_applying_anything(self):
        train_no, minutes = RailBotFacade.validate_delay_report(" 701 ", "45")

        self.assertEqual((train_no, minutes), ("701", 45))
        self.rumi_booking.refresh_from_db()
        self.assertEqual(self.rumi_booking.status, "on-time")

    def test_each_rejection_carries_its_own_message_and_status(self):
        cases = [
            ((None, 30), 400, "Pick a train"),
            (("701", True), 400, "whole number"),
            (("701", "soon"), 400, "whole number"),
            (("701", 0), 400, "between 1 and 300"),
            (("701", 301), 400, "between 1 and 300"),
            (("701", -5), 400, "between 1 and 300"),
        ]
        for (train_no, minutes), status, fragment in cases:
            with self.subTest(train_no=train_no, minutes=minutes):
                with self.assertRaises(DelayReportError) as caught:
                    RailBotFacade.validate_delay_report(train_no, minutes)
                self.assertEqual(caught.exception.status, status)
                self.assertIn(fragment, caught.exception.message)

    def test_a_train_nobody_has_booked_is_a_404(self):
        with self.assertRaises(DelayReportError) as caught:
            RailBotFacade.report_delay("999", 30)

        self.assertEqual(caught.exception.status, 404)
        self.assertIn("999", caught.exception.message)

    def test_a_rejected_report_changes_nothing(self):
        with self.assertRaises(DelayReportError):
            RailBotFacade.report_delay("701", 900)

        self.rumi_booking.refresh_from_db()
        self.assertEqual(self.rumi_booking.status, "on-time")
        self.assertEqual(self.rumi_booking.delay_minutes, 0)

    def test_a_cycle_can_be_run_on_its_own(self):
        """The bookings here are still on-time, so the Risk Agent would
        reach for the trained model. It is stubbed rather than skipped, so
        this test runs on a fresh clone with no .pkl built."""

        class StubModel:
            def predict_proba(self, frame):
                import numpy as np

                return np.array([[0.9, 0.1] for _ in range(len(frame))])

        with mock.patch(
            "core.agents.risk_agent.load_model", return_value=StubModel()
        ):
            result = RailBotFacade.run_agent_cycle()

        self.assertEqual(len(result["results"]), 5)
        self.assertIn("ranAt", result)
