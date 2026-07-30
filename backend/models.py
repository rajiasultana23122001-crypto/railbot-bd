"""Database tables for RailBot BD.

The shapes here mirror what the React dashboards already consume, so switching
the frontend from its sample data to this API needs no component changes.
"""

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Train(db.Model):
    """A train in the timetable."""

    __tablename__ = "trains"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    number = db.Column(db.String(10), nullable=False, unique=True)
    origin = db.Column(db.String(80), nullable=False)
    destination = db.Column(db.String(80), nullable=False)

    bookings = db.relationship("Booking", back_populates="train")


class Passenger(db.Model):
    """Someone who books a seat. Phone is what the Manager Agent calls."""

    __tablename__ = "passengers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(20), nullable=False)

    bookings = db.relationship("Booking", back_populates="passenger")


class Booking(db.Model):
    """One passenger's journey on one train.

    status is 'on-time', 'at-risk' or 'delayed' — assigned by the agents.
    agent_note records, in the passenger's words, what RailBot already did.
    """

    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    train_id = db.Column(db.Integer, db.ForeignKey("trains.id"), nullable=False)
    passenger_id = db.Column(db.Integer, db.ForeignKey("passengers.id"), nullable=False)

    travel_date = db.Column(db.String(20), nullable=False)
    scheduled_departure = db.Column(db.String(5), nullable=False)
    expected_departure = db.Column(db.String(5), nullable=False)
    platform = db.Column(db.String(4))
    coach = db.Column(db.String(30))

    status = db.Column(db.String(10), nullable=False, default="on-time")
    delay_minutes = db.Column(db.Integer, nullable=False, default=0)
    agent_note = db.Column(db.Text)

    train = db.relationship("Train", back_populates="bookings")
    passenger = db.relationship("Passenger", back_populates="bookings")

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
            "delayMinutes": self.delay_minutes,
            "agentNote": self.agent_note,
        }


class Station(db.Model):
    """A station the Resource Agent watches."""

    __tablename__ = "stations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    code = db.Column(db.String(10), nullable=False, unique=True)
    passengers_on_site = db.Column(db.Integer, nullable=False, default=0)
    capacity = db.Column(db.Integer, nullable=False)

    platforms = db.relationship("Platform", back_populates="station")

    def to_dict(self):
        return {
            "name": self.name,
            "code": self.code,
            "passengersOnSite": self.passengers_on_site,
            "capacity": self.capacity,
        }


class Platform(db.Model):
    """Crowding on a single platform."""

    __tablename__ = "platforms"

    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey("stations.id"), nullable=False)
    number = db.Column(db.String(4), nullable=False)
    occupancy = db.Column(db.Integer, nullable=False, default=0)
    capacity = db.Column(db.Integer, nullable=False)
    waiting_for = db.Column(db.String(80))

    station = db.relationship("Station", back_populates="platforms")

    def to_dict(self):
        return {
            "id": self.number,
            "occupancy": self.occupancy,
            "capacity": self.capacity,
            "waitingFor": self.waiting_for,
        }


class Arrival(db.Model):
    """A train due into a station, shown on the Station Master Panel."""

    __tablename__ = "arrivals"

    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey("stations.id"), nullable=False)
    train_id = db.Column(db.Integer, db.ForeignKey("trains.id"), nullable=False)

    scheduled = db.Column(db.String(5), nullable=False)
    expected = db.Column(db.String(5), nullable=False)
    platform = db.Column(db.String(4))
    status = db.Column(db.String(10), nullable=False, default="on-time")

    train = db.relationship("Train")

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
        }


class AgentLog(db.Model):
    """The audit trail: every autonomous decision an agent made.

    This is what the Advisor Agent reads back, and what proves the
    Observe - Reason - Act cycle actually ran.
    """

    __tablename__ = "agent_logs"

    id = db.Column(db.Integer, primary_key=True)
    agent = db.Column(db.String(40), nullable=False)
    severity = db.Column(db.String(10), nullable=False, default="info")
    message = db.Column(db.Text, nullable=False)
    logged_at = db.Column(db.String(5), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": f"AL-{self.id}",
            "time": self.logged_at,
            "agent": self.agent,
            "severity": self.severity,
            "message": self.message,
        }
