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
from .manager_agent import ManagerAgent
from .resource_agent import ResourceAgent
from .risk_agent import RiskAgent
from .scheduler_agent import SchedulerAgent

AGENT_ORDER = [
    RiskAgent,
    SchedulerAgent,
    ManagerAgent,
    ResourceAgent,
    AdvisorAgent,
]

__all__ = [
    "AdvisorAgent",
    "BaseAgent",
    "ManagerAgent",
    "ResourceAgent",
    "RiskAgent",
    "SchedulerAgent",
    "AGENT_ORDER",
    "run_cycle",
]


def run_cycle():
    """Run one full Observe - Reason - Act pass across all five agents."""
    return [agent_class().run() for agent_class in AGENT_ORDER]
