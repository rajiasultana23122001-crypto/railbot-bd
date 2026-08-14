"""Strategy - how a delay is worded depends on what the passenger knows.

Telling somebody their train is late for the first time and telling them the
time you gave them an hour ago has moved are different messages. They are
also different notes on the dashboard. The Manager Agent had this as an
`is_update` flag threaded through reason() and act(), with two branches in
each - which works for two cases and gets steadily worse as cases are added.

Each wording is a strategy object here instead. The agent picks one by
asking what the passenger currently holds, and then composes without
branching. A third case - a cancellation, say, or a platform change - is a
new class, not another arm of an if.

The strategies are stateless and hold no reference to the agent, so they can
be tested on their own with nothing but a booking.
"""


class NotificationStrategy:
    """How one kind of news is worded, for SMS and for the dashboard."""

    #: Short label for the audit trail, e.g. "Delay notice".
    log_label = "Notification"

    def compose_sms(self, booking):
        """The text sent to the passenger's handset.

        Kept to one segment where possible. This is an SMS, not the spoken
        script it replaced, and splitting across segments costs money per
        message for no benefit to the reader.
        """
        raise NotImplementedError

    def compose_note(self, booking):
        """The note shown on the passenger's own dashboard.

        Longer and gentler than the SMS - there is no per-character cost and
        the passenger is reading it deliberately rather than glancing at a
        notification.
        """
        raise NotImplementedError


class FirstNoticeStrategy(NotificationStrategy):
    """The passenger has not been told anything about this delay yet."""

    log_label = "Delay notice"

    def compose_sms(self, booking):
        return (
            f"RailBot: your train {booking.train.name} to "
            f"{booking.train.destination} - now {booking.current_delay} min late, "
            f"departs {booking.expected_departure} from platform {booking.platform}."
        )

    def compose_note(self, booking):
        return (
            f"Manager Agent texted you about the {booking.current_delay} minute "
            f"delay. Your train now departs at {booking.expected_departure} "
            f"from platform {booking.platform}."
        )


class CorrectionStrategy(NotificationStrategy):
    """The passenger holds a departure time that has since moved.

    Worded as a correction rather than as news, because a passenger who gets
    a second message reading like a first one has to work out for themselves
    which of the two times is current.
    """

    log_label = "Updated time"

    def compose_sms(self, booking):
        return (
            f"RailBot: updated delay for {booking.train.name} to "
            f"{booking.train.destination} - now {booking.current_delay} min late, "
            f"departs {booking.expected_departure} from platform {booking.platform}."
        )

    def compose_note(self, booking):
        return (
            "Manager Agent texted you the updated departure time. "
            f"Your train now departs at {booking.expected_departure} "
            f"from platform {booking.platform}."
        )


def strategy_for(booking):
    """Pick the wording from what the passenger currently holds.

    notified_departure is the time this passenger was last told. Unset means
    they have heard nothing about this delay, so it is first news; set means
    they hold a time that the Scheduler has since moved, so it is a
    correction. The Manager Agent only reaches this function for bookings
    where the two differ, so there is no third case.
    """
    return CorrectionStrategy() if booking.notified_departure else FirstNoticeStrategy()
