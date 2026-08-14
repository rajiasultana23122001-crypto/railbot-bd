"""Factory Method - one place that knows how to build an agent.

Before this, run_cycle() held a list of classes and called each one. That
works while every agent is constructed the same way and the list is fixed
at import time, and it stops working the moment either is untrue: an agent
that needs a configured dependency, or a cycle that runs a subset chosen at
runtime, has nowhere to put that knowledge except inside run_cycle().

The factory gives it somewhere. Callers ask for an agent by name and get
one back; how it is built is the factory's business. The registry also
gives the system a single answer to "which agents exist", which the
decorators and the facade both lean on.

    AgentFactory.create("Risk Agent")      -> RiskAgent()
    AgentFactory.create_cycle()            -> all five, in the fixed order
"""

from .advisor_agent import AdvisorAgent
from .base import BaseAgent
from .manager_agent import ManagerAgent
from .resource_agent import ResourceAgent
from .risk_agent import RiskAgent
from .scheduler_agent import SchedulerAgent


class UnknownAgentError(ValueError):
    """Asked for an agent this factory cannot build."""


class AgentFactory:
    """Builds agents by name.

    The order of _REGISTRY is the cycle order, and it is deliberate rather
    than alphabetical: Risk spots journeys about to slip, Scheduler recovers
    what time it can, Manager tells passengers the times Scheduler settled,
    Resource moves staff to the platforms filling up as a result, and
    Advisor reviews all four. Manager before Scheduler would text people
    times that are about to change.
    """

    _REGISTRY = {
        "Risk Agent": RiskAgent,
        "Scheduler Agent": SchedulerAgent,
        "Manager Agent": ManagerAgent,
        "Resource Agent": ResourceAgent,
        "Advisor Agent": AdvisorAgent,
    }

    @classmethod
    def create(cls, name):
        """One agent, by the name it logs under.

        Named by log name rather than class name on purpose: that string is
        what appears in agent_logs and on the dashboard, so an operator
        reading an alert and a developer calling the factory are using the
        same vocabulary.
        """
        try:
            agent_class = cls._REGISTRY[name]
        except KeyError:
            known = ", ".join(cls._REGISTRY)
            raise UnknownAgentError(f"No agent named {name!r}. Known: {known}.")
        return agent_class()

    @classmethod
    def create_cycle(cls):
        """Every agent, in cycle order, freshly built.

        Fresh instances each cycle rather than long-lived ones: an agent
        holds no state between runs, and building them here means a cycle
        cannot be affected by what the previous cycle left behind.
        """
        return [cls.create(name) for name in cls._REGISTRY]

    @classmethod
    def available(cls):
        """The names create() will accept, in cycle order."""
        return list(cls._REGISTRY)

    @classmethod
    def register(cls, name, agent_class):
        """Add an agent to the registry.

        Exists for the sixth agent, whenever it arrives, and for tests that
        need a stub in the cycle. Rejects anything that is not a BaseAgent,
        since the whole cycle assumes run() behaves as BaseAgent defines it.
        """
        if not issubclass(agent_class, BaseAgent):
            raise TypeError(f"{agent_class.__name__} does not derive from BaseAgent.")
        cls._REGISTRY[name] = agent_class
