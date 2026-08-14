# Design patterns in RailBot BD

Seven patterns, each earning its place. Where a pattern was considered and
rejected, that is recorded too — a pattern applied where it does not fit is
a defect, not a feature.

Behaviour is unchanged. Every one of these is a refactor: the same delays
reach the same passengers by the same route.

---

## 1. Template Method — `core/agents/base.py`

`BaseAgent.run()` fixes the algorithm; subclasses supply the steps.

```python
def run(self):
    observation = self.observe()
    decision = self.reason(observation)
    result = self.act(decision)
    return {"agent": self.name, **result}
```

The three steps are abstract, the sequence is not. This is what makes the
architecture claim testable: no agent can act without first observing and
reasoning, because no agent controls the order.

*Present since the first version of the system, not added for this exercise.*

---

## 2. Singleton — `core/scheduler.py`, `core/agents/risk_agent.py`

Two, both in the module-level form Python favours over a `getInstance()`.

**The scheduler.** `_scheduler` holds the one `BackgroundScheduler` per
process; `start()` returns early if it is already set. Django's `ready()`
can run more than once on some deployment paths, and a second scheduler
would mean the agent cycle running in duplicate — passengers texted twice
about one delay.

**The risk model.** `_model` caches the deserialised classifier. Loading a
random forest off disk on every cycle would dominate the runtime of a
cycle that is otherwise a handful of queries.

*Trade-off:* the cached model means retraining needs a process restart to
take effect. Recorded in the SRS as TBD-5.

---

## 3. Factory Method — `core/agents/factory.py`

`AgentFactory.create(name)` builds one agent; `create_cycle()` builds all
five in order.

The cycle used to hold a list of classes and call each one, which works
while every agent is constructed identically and the list is fixed at
import time. The factory gives that knowledge a home for when either
stops being true, and gives the system one answer to "which agents exist" —
which the decorators and the facade both use.

Agents are keyed by the name they log under, so the string an operator
reads in an alert and the string a developer passes to the factory are the
same word.

---

## 4. Adapter — `core/services/gateways.py`

`MessageGateway` is the interface the Manager Agent is written against.
`SmsNetBdAdapter` translates it into a GET with query parameters and a
880-prefixed number; `SimulatedGateway` reports success without sending.

The agent has a passenger and something to tell them. How that reaches a
handset is not its business. When Week 11 adds Firebase push, that is a
new adapter — the agent does not change.

`send()` returns `(delivered, detail)` and never raises. A gateway that
raised would take down the whole cycle over one unreachable provider,
losing the Resource and Advisor agents queued behind it.

---

## 5. Strategy — `core/services/message_strategy.py`

`FirstNoticeStrategy` and `CorrectionStrategy` word the same delay
differently, for SMS and for the dashboard note.

Telling somebody their train is late and telling them the time you gave
them an hour ago has moved are different messages. This was an `is_update`
boolean threaded through `reason()` and `act()`, with two branches in
each — fine for two cases, worse with every case added. A third kind of
notice is now a class, not another arm of an `if`.

`strategy_for(booking)` picks from what the passenger currently holds:
`notified_departure` unset means first news, set means a correction.

---

## 6. Observer — `core/events.py`

Agents publish `AgentEvent`s to `agent_events`. `AuditTrailObserver`
writes them to `agent_logs`; `HighSeverityObserver` puts high-severity
events in front of an operator.

The audit trail used to be the only thing that could ever know an agent had
acted, because `log()` wrote to it directly. Anything else — paging, a
live dashboard in Week 10 — had to be threaded into five agents by hand.
Adding the second observer touched no agent at all.

Two details that matter:

- **Observers cannot break publishers.** A listener that raises is logged
  and stepped over. A paging integration failing is not a reason to lose
  the Scheduler.
- **`subscribe()` ignores a duplicate.** `ready()` runs more than once on
  some paths, and two audit observers would double every log line.

Registration happens in `CoreConfig.ready()`, *before* the `RUN_MAIN`
guard — the test runner never sets `RUN_MAIN`, and agents running with
nothing subscribed would act and leave no record.

---

## 7. Decorator — `core/agents/decorators.py`

`TimingAgent` and `TracingAgent` wrap any agent and present the same
interface, so nothing downstream can tell.

```python
agent = TimingAgent(TracingAgent(RiskAgent()))
```

Timing a cycle by putting a stopwatch inside each agent spreads
measurement code across five unrelated files and means removing it edits
all five. The decorator adds it from outside.

`name` is forwarded rather than replaced, deliberately: a wrapped Risk
Agent must still log as "Risk Agent", or the audit trail starts naming
the decorator instead of the agent that acted.

---

## 8. Facade — `core/facade.py`

`RailBotFacade.report_delay()` holds the whole sequence: validate, find
every booking on the train, mark each one, keep the arrivals board in
step, run five agents in order, and read the reported figures *before* the
Scheduler moves them.

That sequence lived inside a view, which meant the view knew the order of
operations — and so did anything else wanting to report a delay. A
management command, a test, or an operations feed had to know it too, or
go through HTTP to reach it.

The facade adds no rules. Everything in it already existed; it has a name
now, and one caller can no longer get the order wrong.

---

## Considered and rejected

**Abstract Factory.** Its purpose is swapping whole *families* of related
objects — a Windows widget set for a Mac one. RailBot has one family of
agents and one of gateways, and they vary independently. Introducing an
`AbstractRailBotFactory` producing an agent set *and* a gateway set would
be a class whose only job is to be pointed at. The Factory Method above
covers what is actually needed.

**Builder.** Its purpose is constructing objects with many optional parts,
usually step by step. RailBot's objects are Django models, built by the
ORM from keyword arguments; the nearest thing to a builder is
`core/tests/builders.py`, which is a set of test helpers rather than the
pattern. A `BookingBuilder` wrapping `Booking.objects.create()` would add
a layer and remove nothing.

Both would be visible as decoration to anyone reading the code, which is a
worse outcome than not having them.

---

## Tests

`core/tests/test_patterns.py` — 34 tests.

They test the *property* each pattern buys, not that a class exists.
`test_a_new_provider_needs_no_change_to_the_agent` defines a gateway the
codebase has never seen and hands it to the agent's send path.
`test_a_listener_that_raises_does_not_reach_the_publisher` breaks an
observer and checks the agent survives. A test asserting `AgentFactory`
exists would prove nothing.

```bash
python manage.py test core.tests.test_patterns
```
