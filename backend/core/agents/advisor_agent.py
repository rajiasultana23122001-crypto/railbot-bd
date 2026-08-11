"""Advisor Agent - reads the audit trail and looks for patterns.

The other four agents each handle one incident at a time. This one steps back
over the whole log and reports what keeps recurring, which is where timetable
changes come from rather than same-day firefighting.

It is also the only agent that uses a language model, and it uses one for
exactly one thing: turning figures the other four already produced into a
readable shift briefing. The recommendations themselves come from the rules
in reason() below, with or without a key - see core.services.gemini for why
the model is kept away from operational decisions.
"""

import re
from collections import Counter

from core.models import AgentLog, Booking, Platform
from core.services.gemini import write_briefing

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
           # Word boundary, not a substring test: "Platform 1" is a
            # substring of "Platform 10", so a plain `in` credits platform 1
            # with every alert raised about 10, 11 or 12.
            pattern = rf"Platform {re.escape(platform.number)}\b"
            mentions = sum(
                1
                for log in logs
                if log.agent == "Resource Agent"
                and re.search(pattern, log.message)
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

        at_risk = sum(
            1 for b in observation["bookings"] if b.status == "at-risk"
        )

        return {
            "suggestions": suggestions,
            "byAgent": dict(by_agent),
            "totalDecisions": len(logs),
            # Grounding for the written briefing in act(). Assembled here,
            # in the step that is allowed to think, so act() only has to
            # hand it over.
            "facts": {
                "total_decisions": len(logs),
                "high_severity": high_severity,
                "delayed": sum(delayed_routes.values()),
                "at_risk": at_risk,
                "by_agent": dict(by_agent),
                "suggestions": suggestions,
            },
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

        # Only brief when something actually happened. Two reasons, and the
        # second is the important one: a briefing about an unchanged shift is
        # noise, and a model's wording varies between calls, so writing one
        # every cycle would leave the audit trail growing forever and the
        # cycle never settling.
        briefing, briefing_source = None, None
        if added:
            briefing, briefing_source = write_briefing(decision["facts"])
            self.log(briefing, severity="info")

        return {
            "totalDecisions": decision["totalDecisions"],
            "byAgent": decision["byAgent"],
            "suggestions": decision["suggestions"],
            "newlyLogged": len(added),
            "briefing": briefing,
            # 'gemini' or 'template' - surfaced so the panel can say which,
            # rather than letting a fallback pass itself off as the model.
            "briefingSource": briefing_source,
        }
