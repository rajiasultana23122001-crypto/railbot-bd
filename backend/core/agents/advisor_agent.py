"""Advisor Agent - reads the audit trail and looks for patterns.

The other four agents each handle one incident at a time. This one steps back
over the whole log and reports what keeps recurring, which is where timetable
changes come from rather than same-day firefighting.
"""

from collections import Counter

from core.models import AgentLog, Booking, Platform

from .base import BaseAgent

# A platform that trips the crowding threshold this often is a structural
# problem, not a bad afternoon.
REPEAT_ALERT_THRESHOLD = 2


class AdvisorAgent(BaseAgent):
    name = "Advisor Agent"

    def observe(self):
        """The full audit trail, plus the current state it describes."""
        return {
            "logs": list(AgentLog.objects.all()),
            "bookings": list(Booking.objects.select_related("train")),
            "platforms": list(Platform.objects.all()),
        }

    def reason(self, observation):
        """Turn the log into a small number of concrete suggestions."""
        logs = observation["logs"]
        suggestions = []

        # Which agents are doing the most work says where the pressure is.
        by_agent = Counter(log.agent for log in logs)
        high_severity = sum(1 for log in logs if log.severity == "high")

        # Platforms named repeatedly in crowding alerts.
        crowded = Counter()
        for platform in observation["platforms"]:
            mentions = sum(
                1
                for log in logs
                if log.agent == "Resource Agent"
                and f"Platform {platform.number}" in log.message
            )
            if mentions >= REPEAT_ALERT_THRESHOLD:
                crowded[platform.number] = mentions

        for number, mentions in crowded.most_common():
            suggestions.append(
                f"Platform {number} triggered {mentions} crowding alerts. Consider "
                "moving one departure to a quieter platform or staggering its "
                "boarding window."
            )

        # Routes that keep slipping are timetable problems, not daily bad luck.
        delayed_routes = Counter(
            b.train.name for b in observation["bookings"] if b.status == "delayed"
        )
        for train, count in delayed_routes.most_common(2):
            suggestions.append(
                f"{train} is running late again. Review its scheduled halt times; "
                "the current allowance looks too tight for this route."
            )

        if high_severity >= 2:
            suggestions.append(
                f"{high_severity} high-severity alerts stand in the log. Station "
                "capacity is the binding constraint today, not train availability."
            )

        return {
            "suggestions": suggestions,
            "byAgent": dict(by_agent),
            "totalDecisions": len(logs),
        }

    def act(self, decision):
        """Record any suggestion that is not already standing in the log.

        Re-running the cycle should not fill the feed with duplicates of advice
        the station master has already been given.
        """
        already_said = set(
            AgentLog.objects.filter(agent=self.name).values_list("message", flat=True)
        )

        added = []
        for suggestion in decision["suggestions"]:
            if suggestion not in already_said:
                self.log(suggestion, severity="info")
                added.append(suggestion)

        return {
            "totalDecisions": decision["totalDecisions"],
            "byAgent": decision["byAgent"],
            "suggestions": decision["suggestions"],
            "newlyLogged": len(added),
        }
