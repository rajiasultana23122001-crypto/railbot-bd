"""The five RailBot agents and the cycle that runs them.

Order matters, and it follows how a delay actually propagates:

  1. Risk Agent      spots journeys about to slip
  2. Scheduler Agent recovers what time it can on those already late
  3. Manager Agent   tells passengers the times the Scheduler just settled
  4. Resource Agent  moves staff to the platforms filling up as a result
  5. Advisor Agent   reviews everything the other four just did

Running Manager before Scheduler would call passengers with times about to
change, so the sequence is part of the design rather than an accident.
"""

from .advisor_agent import AdvisorAgent
from .base import BaseAgent
from .factory import AgentFactory, UnknownAgentError
from .manager_agent import ManagerAgent
from .resource_agent import ResourceAgent
from .risk_agent import RiskAgent
from .scheduler_agent import SchedulerAgent

#: Kept as the class list it always was, for anything importing it, but the
#: registry inside AgentFactory is now what actually decides cycle order.
AGENT_ORDER = [
    RiskAgent,
    SchedulerAgent,
    ManagerAgent,
    ResourceAgent,
    AdvisorAgent,
]

__all__ = [
    "AdvisorAgent",
    "AgentFactory",
    "BaseAgent",
    "ManagerAgent",
    "ResourceAgent",
    "RiskAgent",
    "SchedulerAgent",
    "UnknownAgentError",
    "AGENT_ORDER",
    "run_cycle",
]


def run_cycle(agents=None):
    """Run one full Observe - Reason - Act pass across all five agents.

    Takes the agents to run so a caller can decorate them - with timing, for
    instance - or run a subset. Defaults to the full cycle in fixed order,
    built by the factory.
    """
    if agents is None:
        agents = AgentFactory.create_cycle()
    return [agent.run() for agent in agents]
