"""Database tables for RailBot BD.

The shapes here mirror what the React dashboards already consume, so the
frontend needs no changes.
"""

import random
import string

from django.conf import settings
from django.db import models


def generate_pnr():
    """A booking reference in the same shape a real one takes: BR + 8
    alphanumerics. Collisions are astronomically unlikely at this length,
    but callers still retry on IntegrityError rather than trust that alone
    (see views.create_booking).
    """
    body = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"BR{body}"


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

    # Total seats sold per class, e.g. {"SNIGDHA": 60, "SHOVAN": 88, ...} -
    # keyed the same as seat_classes. How many are still free for a given
    # date is never stored here; it is counted live off confirmed Bookings
    # (see views.available_seats), so this number never has to be kept in
    # sync by hand either.
    seat_capacity = models.JSONField(default=dict, blank=True)

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


class TrainStop(models.Model):
    """One station a train calls at, in the order it calls there.

    What makes "search between any two stops on this line" possible - a
    booking's own scheduled_departure is read off the `departure` of the
    stop the passenger boards at, and its fare is priced off the distance
    between two stops, not the train's whole route. arrival is null at the
    first stop and departure is null at the last, matching how a train has
    nowhere to arrive from and nowhere left to depart to at its own ends.
    """

    train = models.ForeignKey(Train, on_delete=models.CASCADE, related_name="stops")
    station = models.ForeignKey(
        "Station", on_delete=models.CASCADE, related_name="train_stops"
    )
    sequence = models.IntegerField()
    arrival = models.CharField(max_length=5, null=True, blank=True)
    departure = models.CharField(max_length=5, null=True, blank=True)

    # Cumulative distance from the train's origin, in km. Used to price a
    # partial-route booking off the actual leg travelled rather than the
    # train's full-route distance_km.
    distance_km = models.FloatField(default=0)

    class Meta:
        ordering = ["train", "sequence"]

    def __str__(self):
        return f"{self.train.number} stop {self.sequence}: {self.station.name}"


class Passenger(models.Model):
    """Someone who books a seat. Phone is what the Manager Agent calls.

    Booking data only - who the agents call and what they call about. Login
    identity and role live on Profile below; a passenger's Profile links back
    to a Passenger row here once one exists (see auth_views.passenger_signup),
    but nothing requires that link, so seeded/demo bookings work with no
    account behind them at all.
    """

    name = models.CharField(max_length=80)
    phone = models.CharField(max_length=20)

    def __str__(self):
        return self.name


class OTPCode(models.Model):
    """A one-time passcode texted to a phone number via sms.net.bd.

    sms.net.bd only sends the text - it does not generate codes, expire
    them, or limit attempts the way Twilio Verify used to. This table and
    core.services.otp do that work instead: code_hash is never the plaintext
    code (see core.services.otp for the hashing), created_at is what expiry
    is measured against, attempts locks the code out after too many wrong
    guesses, and is_used stops a correct code being replayed.
    """

    phone_number = models.CharField(max_length=20)
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    attempts = models.IntegerField(default=0)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        state = "used" if self.is_used else f"{self.attempts} attempt(s)"
        return f"OTP for {self.phone_number} ({state})"


class AuthorityID(models.Model):
    """A BD Railway-issued Authority ID, pre-loaded before anyone signs up.

    Nothing here is generated by this system - these are handed out
    beforehand, and `manage.py seed` loads a handful of example codes to
    test with. An Authority signup can only succeed against a code already
    listed here, and each code can be claimed once (see is_claimed).
    """

    code = models.CharField(max_length=30, unique=True)
    note = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_claimed(self):
        return hasattr(self, "claimed_by")

    def __str__(self):
        return self.code


class Profile(models.Model):
    """Login identity and role for a Django auth User.

    Deliberately separate from Passenger: Passenger is booking data the
    agents read (a name and a phone to call); Profile is who is signed in
    and what they are allowed to do. One Django User gets exactly one
    Profile, and the role on it decides which API endpoints will answer.
    """

    ROLE_PASSENGER = "passenger"
    ROLE_AUTHORITY = "authority"
    ROLE_CHOICES = [
        (ROLE_PASSENGER, "Passenger"),
        (ROLE_AUTHORITY, "Authority"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)

    # The identity every account signs in with, regardless of role. Also
    # Django's own User.username under the hood (see auth_views) - kept here
    # too so a response can carry it without following the user relation.
    phone_number = models.CharField(max_length=20, unique=True)

    # Passenger-only. Null rather than blank-string so multiple authority
    # profiles (which never set this) don't collide under the unique
    # constraint.
    nid_number = models.CharField(max_length=17, unique=True, null=True, blank=True)

    # Set once the OTP sent at signup (see core.services.otp) is confirmed. A
    # passenger cannot log in until this is True (see auth_views.login).
    is_phone_verified = models.BooleanField(default=False)

    # Linked manually once a Station Authority matches this passenger to a
    # real booking record - signup does not create or guess this.
    passenger = models.OneToOneField(
        Passenger,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profile",
    )

    # Authority-only: the pre-issued ID this account claimed at signup.
    authority_id = models.OneToOneField(
        AuthorityID,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="claimed_by",
    )

    def own_bookings(self):
        """The bookings this account is entitled to see - and only those.

        Prefer the Passenger a Station Authority linked by hand. Where that
        link has not been made, fall back to the phone number: a seat is
        booked at the counter against a number, so a Passenger row carrying
        this account's number is this account's booking record. The fallback
        matters because signup and booking happen in either order - an account
        opened before its first booking still finds that booking afterwards,
        with nobody having to go and set the link.

        The fallback deliberately ignores records another account already
        holds. Matching on a number alone would otherwise hand over bookings
        belonging to whoever holds that record, which is the exact thing this
        method exists to prevent.

        Returns a queryset, so callers can add their own select_related.
        """
        if self.passenger_id:
            return Booking.objects.filter(passenger_id=self.passenger_id)
        return Booking.objects.filter(
            passenger__phone=self.phone_number, passenger__profile__isnull=True
        )

    def __str__(self):
        return f"{self.phone_number} ({self.role})"


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

    # Ticket identity and self-service booking detail below. Deliberately
    # not merged with `status` above: that field is the agents' delay state
    # (on-time/at-risk/delayed) and this one is the ticket's own lifecycle
    # (confirmed/cancelled) - conflating them would let a cancellation read
    # as a delay state or vice versa.
    #
    # pnr is nullable only because the field was added to a table that
    # already had rows (see the migration) - every booking gets a real one
    # at creation time, seeded or self-service, so it is never actually
    # blank after `manage.py seed`.
    pnr = models.CharField(max_length=12, unique=True, null=True, blank=True)
    booking_status = models.CharField(max_length=10, default="confirmed")

    seat_class = models.CharField(max_length=10, null=True, blank=True)
    seat_numbers = models.JSONField(default=list, blank=True)
    passenger_count = models.IntegerField(default=1)
    fare_paid = models.IntegerField(default=0)

    # Set only when a self-service booking boards or alights somewhere other
    # than the train's own origin/destination. to_dict() falls back to
    # train.origin/train.destination when these are null, which is every
    # seeded booking and every full-route booking.
    origin_station = models.ForeignKey(
        "Station",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    destination_station = models.ForeignKey(
        "Station",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

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

    class Meta:
        indexes = [
            # Seat availability is never stored - it is counted live off the
            # confirmed bookings for one train/date/class every time someone
            # searches a route, opens a seat map or books a ticket (see
            # core.services.booking.availability_by_class). That filter is
            # the hottest read in the app, and without an index it is a full
            # scan of the booking table each time.
            models.Index(
                fields=["train", "travel_date", "seat_class", "booking_status"],
                name="booking_availability_idx",
            ),
        ]

    @property
    def current_delay(self):
        """How late the train still is, after any recovery."""
        return max(self.delay_minutes - self.recovered_minutes, 0)

    def to_dict(self):
        """Serialise into the shape the Passenger Dashboard expects.

        "id" used to be f"BR-{train.number}", which collided once a
        passenger could hold two bookings on the same train (impossible
        before self-service booking existed, routine now) - React was
        silently reusing one JourneyCard for both. Built off the row's own
        pk instead, which is unique by construction; bookingId is the same
        value bare, for API calls (e.g. cancel) that need a plain int.
        """
        return {
            "id": f"BR-{self.id}",
            "bookingId": self.id,
            "train": self.train.name,
            "trainNo": self.train.number,
            "from": self.origin_station.name if self.origin_station_id else self.train.origin,
            "to": self.destination_station.name
            if self.destination_station_id
            else self.train.destination,
            "date": self.travel_date,
            "scheduledDeparture": self.scheduled_departure,
            "expectedDeparture": self.expected_departure,
            "platform": self.platform,
            "coach": self.coach,
            "status": self.status,
            "delayMinutes": self.current_delay,
            "agentNote": self.agent_note,
            "pnr": self.pnr,
            "bookingStatus": self.booking_status,
            "seatClass": self.seat_class,
            "seatNumbers": self.seat_numbers,
            "passengerCount": self.passenger_count,
            "farePaid": self.fare_paid,
        }

    def __str__(self):
        return f"{self.train.name} for {self.passenger.name}"


class BookingPassenger(models.Model):
    """One traveller on one seat of a Booking.

    Kept separate from Passenger above on purpose: Passenger is one row per
    phone number - the account the Manager Agent calls - while a single
    booking can carry several people travelling together, each with their
    own seat and (optional) ID. Nothing here is read by the agents; it only
    ever surfaces on the ticket itself.
    """

    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="passengers_detail"
    )
    name = models.CharField(max_length=80)
    age = models.IntegerField(null=True, blank=True)
    id_number = models.CharField(max_length=30, null=True, blank=True)
    seat_number = models.CharField(max_length=20, blank=True)

    def to_dict(self):
        return {
            "name": self.name,
            "age": self.age,
            "idNumber": self.id_number,
            "seatNumber": self.seat_number,
        }

    def __str__(self):
        return f"{self.name} ({self.seat_number})"


class Station(models.Model):
    """A station - both what the Resource Agent watches for crowding and
    what the booking search picks From/To from.

    Only a handful of stations carry Platforms and get watched for crowding
    (see seed.py); every station in the network gets a row here regardless,
    since the booking flow needs the full list to search between any two of
    them. capacity/passengers_on_site are null on a station nothing is
    monitoring - the Resource Agent only ever iterates Platform objects, so
    a station with no platforms is simply never asked about.
    """

    name = models.CharField(max_length=80)
    code = models.CharField(max_length=10, unique=True)
    division = models.CharField(max_length=40, null=True, blank=True)
    passengers_on_site = models.IntegerField(default=0)
    capacity = models.IntegerField(null=True, blank=True)

    def to_dict(self):
        return {
            "name": self.name,
            "code": self.code,
            "division": self.division,
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
