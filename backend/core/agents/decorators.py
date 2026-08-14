"""Decorator - add behaviour to an agent without editing the agent.

Timing a cycle, or tracing which agent is slow, is the kind of thing that
gets added by putting a stopwatch inside each agent's run(). Do that five
times and the measurement code is spread across five files that have nothing
else in common, and taking it out again means editing all five.

A decorator wraps an agent instead. It presents the same interface the cycle
calls - run(), name, log() - so nothing downstream can tell the difference,
and it does its own work either side of delegating. Because a decorator is
itself agent-shaped, decorators stack:

    agent = TimingAgent(TracingAgent(RiskAgent()))

The Risk Agent is not aware of either, and neither decorator knows what it
is wrapping.
"""

import logging
import time

logger = logging.getLogger("core.agents")


class AgentDecorator:
    """Base for anything that wraps an agent.

    Forwards everything by default, so a subclass overrides only the one
    method it wants to change. name is forwarded rather than replaced
    deliberately: a wrapped Risk Agent must still log as "Risk Agent", or the
    audit trail starts naming the decorator instead of the agent that acted.
    """

    def __init__(self, agent):
        self._agent = agent

    @property
    def name(self):
        return self._agent.name

    @property
    def wrapped(self):
        """The agent underneath, unwrapping any decorators in between."""
        inner = self._agent
        while isinstance(inner, AgentDecorator):
            inner = inner._agent
        return inner

    def observe(self):
        return self._agent.observe()

    def reason(self, observation):
        return self._agent.reason(observation)

    def act(self, decision):
        return self._agent.act(decision)

    def log(self, message, severity="info"):
        return self._agent.log(message, severity)

    def run(self):
        return self._agent.run()


class TimingAgent(AgentDecorator):
    """Records how long an agent took.

    The duration lands in the result dictionary the cycle already returns, so
    it reaches the dashboard without any endpoint changing shape. It is
    recorded on failure too - an agent that is slow because it is timing out
    against an external service is exactly the case worth seeing, and that
    path ends in an exception rather than a return.
    """

    def run(self):
        started = time.perf_counter()
        try:
            result = self._agent.run()
        except Exception:
            elapsed = (time.perf_counter() - started) * 1000
            logger.warning("%s failed after %.0f ms", self.name, elapsed)
            raise
        elapsed = (time.perf_counter() - started) * 1000
        result["elapsedMs"] = round(elapsed, 1)
        return result


class TracingAgent(AgentDecorator):
    """Logs each phase of the loop as it happens.

    Useful when a cycle misbehaves and the question is which of observe,
    reason or act it got to. Goes to the application log rather than
    agent_logs: this is developer diagnostics, and filling the operator's
    audit trail with it would bury the alerts they actually need.
    """

    def run(self):
        logger.debug("%s: observe", self.name)
        observation = self._agent.observe()

        logger.debug("%s: reason", self.name)
        decision = self._agent.reason(observation)

        logger.debug("%s: act", self.name)
        result = self._agent.act(decision)

        return {"agent": self.name, **result}


def with_timing(agents):
    """Wrap each agent in a cycle with timing.

    Applied at the cycle level rather than inside run_cycle() so that timing
    stays optional - a caller that does not want the overhead builds the
    cycle without it.
    """
    return [TimingAgent(agent) for agent in agents]
