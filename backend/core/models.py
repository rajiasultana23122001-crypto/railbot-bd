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

    # Class codes this train sells, e.g. ["AC_B", "AC_S", "SNIGDHA", ...].
    # Fares are not stored - they are the per-km rate in SEAT_CLASSES times
    # this train's own distance_km, so a fare never has to be kept in sync by
    # hand.
    seat_classes = models.JSONField(default=list, blank=True)

    def to_dict(self):
        """Full route and fare info, for the passenger-facing train browser."""
        from core.data.network import SEAT_CLASSES

        return {
            "name": self.name,
            "number": self.number,
            "origin": self.origin,
            "destination": self.destination,
            "distanceKm": self.distance_km,
            "scheduledHalts": self.scheduled_halts,
            "route": self.route,
            "seatClasses": [
                {
                    "code": code,
                    "label": SEAT_CLASSES[code]["label"],
                    "fare": round(SEAT_CLASSES[code]["taka_per_km"] * self.distance_km),
                }
                for code in self.seat_classes
                if code in SEAT_CLASSES
            ],
        }

    def __str__(self):
        return f"{self.name} #{self.number}"


class Passenger(models.Model):
    """Someone who books a seat. Phone is what the Manager Agent calls.

    Auth fields added for Phase 3: an account is phone + NID, activated once
    the phone is OTP-confirmed through Twilio Verify. nid_verified is a
    separate flag a Station Manager sets by hand after checking the physical
    card - nothing here ever checks the NID against a government database.
    """

    name = models.CharField(max_length=80)
    phone = models.CharField(max_length=20, unique=True)

    # Null rather than blank-string so existing/seeded passengers with no NID
    # on file don't collide with each other under the unique constraint.
    nid_number = models.CharField(max_length=17, unique=True, null=True, blank=True)
    nid_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=False)

    # Bearer token issued once the phone is verified (signup) or on every
    # subsequent OTP login. Rotated each time, so an old token stops working
    # the moment a new login succeeds.
    auth_token = models.CharField(max_length=64, unique=True, null=True, blank=True)

    def __str__(self):
        return self.name


class StationManager(models.Model):
    """A station operator's login.

    Not self-service: an account only exists because someone ran
    `manage.py create_manager`, never through a public endpoint. Password is
    hashed with Django's own hasher (the same one django.contrib.auth uses),
    even though this model doesn't subclass Django's User.
    """

    username = models.CharField(max_length=50, unique=True)
    password_hash = models.CharField(max_length=128)
    auth_token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username


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
