"""Database tables for RailBot BD.

The shapes here mirror what the React dashboards already consume, so the
frontend needs no changes.
"""

from django.db import models


class Train(models.Model):
    """A train in the timetable."""

    name = models.CharField(max_length=80)
    number = models.CharField(max_length=10, unique=True)
    origin = models.CharField(max_length=80)
    destination = models.CharField(max_length=80)

    # Route facts the Risk Agent's model uses as features.
    distance_km = models.IntegerField(default=200)
    scheduled_halts = models.IntegerField(default=8)

    # The stations this service calls at, in order. Stored here rather than as
    # its own table because nothing queries an individual stop - the frontend
    # wants the whole list at once, to draw the route on the map.
    route = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.name} #{self.number}"


class Passenger(models.Model):
    """Someone who books a seat. Phone is what the Manager Agent calls."""

    name = models.CharField(max_length=80)
    phone = models.CharField(max_length=20)

    def __str__(self):
        return self.name


class Booking(models.Model):
    """One passenger's journey on one train.

    status is 'on-time', 'at-risk' or 'delayed' - assigned by the agents.
    agent_note records, in the passenger's words, what RailBot already did.
    """

    train = models.ForeignKey(Train, on_delete=models.CASCADE, related_name="bookings")
    passenger = models.ForeignKey(
        Passenger, on_delete=models.CASCADE, related_name="bookings"
    )

    travel_date = models.CharField(max_length=20)
    scheduled_departure = models.CharField(max_length=5)
    expected_departure = models.CharField(max_length=5)
    platform = models.CharField(max_length=4, null=True, blank=True)
    coach = models.CharField(max_length=30, null=True, blank=True)

    status = models.CharField(max_length=10, default="on-time")

    # The delay as first reported. It stays put so the Scheduler Agent always
    # sizes its recovery budget against the original slip rather than against
    # a figure it has already improved.
    delay_minutes = models.IntegerField(default=0)

    # Minutes the Scheduler Agent has clawed back so far.
    recovered_minutes = models.IntegerField(default=0)

    agent_note = models.TextField(null=True, blank=True)

    # The departure time the Manager Agent last read out to this passenger.
    # When it stops matching expected_departure, the passenger is holding an
    # out-of-date time and has to be called again.
    notified_departure = models.CharField(max_length=5, null=True, blank=True)

    @property
    def current_delay(self):
        """How late the train still is, after any recovery."""
        return max(self.delay_minutes - self.recovered_minutes, 0)

    def to_dict(self):
        """Serialise into the shape the Passenger Dashboard expects."""
        return {
            "id": f"BR-{self.train.number}",
            "train": self.train.name,
            "trainNo": self.train.number,
            "from": self.train.origin,
            "to": self.train.destination,
            "date": self.travel_date,
            "scheduledDeparture": self.scheduled_departure,
            "expectedDeparture": self.expected_departure,
            "platform": self.platform,
            "coach": self.coach,
            "status": self.status,
            "delayMinutes": self.current_delay,
            "agentNote": self.agent_note,
        }

    def __str__(self):
        return f"{self.train.name} for {self.passenger.name}"


class Station(models.Model):
    """A station the Resource Agent watches."""

    name = models.CharField(max_length=80)
    code = models.CharField(max_length=10, unique=True)
    passengers_on_site = models.IntegerField(default=0)
    capacity = models.IntegerField()

    def to_dict(self):
        return {
            "name": self.name,
            "code": self.code,
            "passengersOnSite": self.passengers_on_site,
            "capacity": self.capacity,
        }

    def __str__(self):
        return self.name


class Platform(models.Model):
    """Crowding on a single platform."""

    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="platforms"
    )
    number = models.CharField(max_length=4)
    occupancy = models.IntegerField(default=0)
    capacity = models.IntegerField()
    waiting_for = models.CharField(max_length=80, null=True, blank=True)

    # Crowding level the Resource Agent last raised for this platform, so a
    # standing condition is reported once rather than on every cycle.
    last_alert_level = models.CharField(max_length=10, null=True, blank=True)

    def to_dict(self):
        return {
            "id": self.number,
            "occupancy": self.occupancy,
            "capacity": self.capacity,
            "waitingFor": self.waiting_for,
        }

    def __str__(self):
        return f"Platform {self.number}"


class Arrival(models.Model):
    """A train due into a station, shown on the Station Master Panel."""

    station = models.ForeignKey(
        Station, on_delete=models.CASCADE, related_name="arrivals"
    )
    train = models.ForeignKey(Train, on_delete=models.CASCADE)

    scheduled = models.CharField(max_length=5)
    expected = models.CharField(max_length=5)
    platform = models.CharField(max_length=4, null=True, blank=True)
    status = models.CharField(max_length=10, default="on-time")

    def to_dict(self):
        return {
            "id": f"A-{self.train.number}",
            "train": self.train.name,
            "trainNo": self.train.number,
            "from": self.train.origin,
            "scheduled": self.scheduled,
            "expected": self.expected,
            "platform": self.platform,
            "status": self.status,
            # Sent so the map can trace this service without a second request.
            "route": self.train.route,
        }


class AgentLog(models.Model):
    """The audit trail: every autonomous decision an agent made.

    This is what the Advisor Agent reads back, and what proves the
    Observe - Reason - Act cycle actually ran. It deliberately carries no
    foreign key: the record has to outlive whatever it describes.
    """

    agent = models.CharField(max_length=40)
    severity = models.CharField(max_length=10, default="info")
    message = models.TextField()
    logged_at = models.CharField(max_length=5)
    created_at = models.DateTimeField(auto_now_add=True)

    def to_dict(self):
        return {
            "id": f"AL-{self.id}",
            "time": self.logged_at,
            "agent": self.agent,
            "severity": self.severity,
            "message": self.message,
        }

    def __str__(self):
        return f"{self.agent}: {self.message[:50]}"
