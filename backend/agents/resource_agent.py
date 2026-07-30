"""Resource Agent — keeps platforms from overfilling.

Observes crowding, reasons against the same thresholds the dashboard meters
use, and tells the station master to open extra space before it is too late.
"""

from models import Platform, db

from .base import BaseAgent

# These match the meter colours on the Station Master Panel, so what staff see
# and what the agent acts on are never out of step.
BUSY_PERCENT = 70
CRITICAL_PERCENT = 90


class ResourceAgent(BaseAgent):
    name = "Resource Agent"

    def observe(self):
        """Occupancy on every platform."""
        readings = []
        for platform in Platform.query.all():
            percent = round((platform.occupancy / platform.capacity) * 100)
            readings.append({"platform": platform, "percent": percent})
        return readings

    def reason(self, observation):
        """Decide which platforms need staff moved to them.

        Only changes are worth announcing. A platform that was already reported
        critical and still is does not need saying twice; one that has eased off
        does, so the station master knows the staff can go back.
        """
        decisions = []
        for reading in observation:
            platform = reading["platform"]
            percent = reading["percent"]

            if percent >= CRITICAL_PERCENT:
                level, staff = "critical", 2
            elif percent >= BUSY_PERCENT:
                level, staff = "busy", 1
            else:
                level, staff = "clear", 0

            if level == platform.last_alert_level:
                continue

            decisions.append({**reading, "level": level, "staff": staff})
        return decisions

    def act(self, decision):
        """Raise an alert for each platform under pressure."""
        alerts = []

        for item in decision:
            platform = item["platform"]
            percent = item["percent"]
            inbound = platform.waiting_for or "no assigned train"

            if item["level"] == "critical":
                message = (
                    f"Platform {platform.number} is at {percent}% capacity with "
                    f"{inbound} still inbound. Open an additional waiting room and "
                    f"assign {item['staff']} crowd-control staff."
                )
                severity = "high"
            elif item["level"] == "busy":
                message = (
                    f"Platform {platform.number} is filling up ({percent}%). "
                    f"Assign {item['staff']} staff member to manage boarding for "
                    f"{inbound}."
                )
                severity = "medium"
            else:
                message = (
                    f"Platform {platform.number} has eased to {percent}%. "
                    "Crowd-control staff can be reassigned."
                )
                severity = "info"

            self.log(message, severity=severity)
            platform.last_alert_level = item["level"]
            alerts.append(
                {
                    "platform": platform.number,
                    "percent": percent,
                    "level": item["level"],
                }
            )

        db.session.commit()
        return {"examined": len(decision), "alerts": alerts}
