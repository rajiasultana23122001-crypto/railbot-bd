"""The autonomous agent loop every RailBot agent follows.

Each agent implements the same three steps:

    observe()  gather the facts it is responsible for watching
    reason()   decide what, if anything, should happen
    act()      change the system and record the decision

run() executes them in order. Keeping the cycle in one place is what makes the
architecture claim testable: no agent can act without first observing and
reasoning, and every action it takes lands in the audit trail.
"""

from datetime import datetime

from models import AgentLog, db


def clock():
    """Current time as HH:MM, the format the dashboards display."""
    return datetime.now().strftime("%H:%M")


class BaseAgent:
    """Shared behaviour for the five agents."""

    name = "Agent"

    def observe(self):
        """Return whatever this agent needs to look at."""
        raise NotImplementedError

    def reason(self, observation):
        """Turn an observation into a decision. No side effects here."""
        raise NotImplementedError

    def act(self, decision):
        """Apply the decision and return a summary of what changed."""
        raise NotImplementedError

    def run(self):
        """One full Observe - Reason - Act cycle."""
        observation = self.observe()
        decision = self.reason(observation)
        result = self.act(decision)
        return {"agent": self.name, **result}

    def log(self, message, severity="info"):
        """Write one line into the audit trail the Advisor Agent reads."""
        entry = AgentLog(
            agent=self.name,
            severity=severity,
            message=message,
            logged_at=clock(),
        )
        db.session.add(entry)
        return entry
