"""Observer - agents announce what they did; interested parties listen.

Every agent used to write to agent_logs by calling log(), which meant the
audit trail was the one and only thing that could ever know an agent had
acted. Anything else that wanted to react - paging an operator on a
high-severity alert, gathering counts for the Advisor, pushing to a live
dashboard when Week 10 arrives - had to be threaded into the agents
themselves, one call at a time, in five places.

An agent now publishes an event and does not care who is listening. The
audit trail is simply the first observer to subscribe. Adding the second one
does not touch any agent.

Registration happens once at startup, in CoreConfig.ready(). Observers must
not raise: a listener that fails takes down the agent that published, and a
paging integration breaking is not a reason to lose the Scheduler.
"""

import logging

logger = logging.getLogger("core.events")


class AgentEvent:
    """One thing an agent did.

    Carries what the audit trail needs plus the severity, so an observer can
    decide whether it cares without parsing the message text.
    """

    def __init__(self, agent, message, severity="info"):
        self.agent = agent
        self.message = message
        self.severity = severity

    def __repr__(self):
        return f"<AgentEvent {self.agent}: {self.severity}>"


class AgentObserver:
    """Something that reacts when an agent acts."""

    def notify(self, event):
        raise NotImplementedError


class AuditTrailObserver(AgentObserver):
    """Writes each event to agent_logs.

    This is the observer that used to be the body of BaseAgent.log(). It
    returns the row it created, because log() still hands that back to
    callers that want it.
    """

    def notify(self, event):
        # Imported here rather than at module scope: this module is imported
        # from CoreConfig.ready(), where the app registry is still loading
        # and models are not yet safe to import.
        from core.models import AgentLog
        from core.agents.base import clock

        return AgentLog.objects.create(
            agent=event.agent,
            severity=event.severity,
            message=event.message,
            logged_at=clock(),
        )


class HighSeverityObserver(AgentObserver):
    """Puts high-severity events in front of an operator.

    Today that means the application log, which is where somebody watching a
    running server will actually see it - a high-severity row in agent_logs
    is only visible to whoever opens the dashboard. A failed SMS is the case
    that matters: the passenger has not been told and will not be until the
    next cycle, and nothing else raises its voice about that.

    Replacing the logger call with a page, an email, or a WebSocket push is a
    change to this class alone.
    """

    def notify(self, event):
        if event.severity != "high":
            return None
        logger.warning("[%s] %s", event.agent, event.message)
        return None


class AgentEventBus:
    """Where events are published and observers subscribe.

    Observers are notified in subscription order, and one that raises is
    logged and stepped over rather than allowed to reach the agent. That
    isolation is the whole reason the bus exists: an agent should not be able
    to fail because something was listening to it.
    """

    def __init__(self):
        self._observers = []

    def subscribe(self, observer):
        """Add an observer, ignoring one already subscribed.

        ready() can run more than once per process on some Django paths, and
        a duplicate AuditTrailObserver would write every log line twice.
        """
        if any(isinstance(o, type(observer)) for o in self._observers):
            return
        self._observers.append(observer)

    def unsubscribe(self, observer):
        if observer in self._observers:
            self._observers.remove(observer)

    def clear(self):
        """Drop every observer. For tests that need a known bus."""
        self._observers = []

    def publish(self, event):
        """Notify every observer. Returns the first non-None result.

        The return exists so BaseAgent.log() can still hand back the AgentLog
        row it used to create directly, which keeps log() a drop-in
        replacement for its old self.
        """
        first = None
        for observer in self._observers:
            try:
                result = observer.notify(event)
            except Exception:
                # Deliberately broad: this is the boundary that stops a
                # listener's failure from becoming the publisher's failure.
                logger.exception(
                    "%s raised while handling an event from %s",
                    type(observer).__name__,
                    event.agent,
                )
                continue
            if first is None and result is not None:
                first = result
        return first


#: The bus every agent publishes to. One per process.
agent_events = AgentEventBus()


def register_default_observers():
    """Subscribe the observers the system ships with. Called from ready()."""
    agent_events.subscribe(AuditTrailObserver())
    agent_events.subscribe(HighSeverityObserver())
