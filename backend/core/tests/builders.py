"""Small builders for test data.

Named builders rather than fixtures so each test can say, in its own body,
exactly which detail it depends on - a booking's delay, a platform's
occupancy - and leave everything else at a sensible default. A test that
reads as a paragraph is worth more than one that points at a YAML file.

Not named test_*.py, so Django's test runner does not try to collect it.
"""

from django.contrib.auth.models import User

from core.models import (
    AuthorityID,
    Booking,
    Passenger,
    Platform,
    Profile,
    Station,
    Train,
)

PASSWORD = "test-pass-123"


def make_train(number="701", name="Subarna Express", halts=8, distance=320):
    return Train.objects.create(
        name=name,
        number=number,
        origin="Dhaka (Kamalapur)",
        destination="Chattogram",
        distance_km=distance,
        scheduled_halts=halts,
        route=["Dhaka (Kamalapur)", "Cumilla", "Chattogram"],
        seat_classes=["SHOVAN", "SNIGDHA"],
    )


def make_booking(train, passenger, **overrides):
    """A booking on a train, on time and unremarkable unless told otherwise."""
    fields = {
        "travel_date": "1 Aug 2026",
        "scheduled_departure": "07:00",
        "expected_departure": "07:00",
        "platform": "4",
        "coach": "SNIGDHA / C1-24",
        "status": "on-time",
    }
    fields.update(overrides)
    return Booking.objects.create(train=train, passenger=passenger, **fields)


def make_passenger_account(phone, name="Test Passenger", nid=None, link=True):
    """A verified passenger account and the Passenger record behind it.

    Returns (profile, passenger). With link=False the two are left
    unconnected, which is how an account looks before a Station Authority
    ties it to a booking record - the case Profile.own_bookings has to
    handle by matching on the phone number instead.
    """
    passenger = Passenger.objects.create(name=name, phone=phone)
    user = User.objects.create_user(username=phone, password=PASSWORD)
    profile = Profile.objects.create(
        user=user,
        role=Profile.ROLE_PASSENGER,
        phone_number=phone,
        nid_number=nid,
        is_phone_verified=True,
        passenger=passenger if link else None,
    )
    return profile, passenger


def make_authority_account(phone, code="BR-AUTH-9001"):
    """An authority account holding a freshly issued ID."""
    authority_id = AuthorityID.objects.create(code=code, note="test")
    user = User.objects.create_user(username=phone, password=PASSWORD)
    return Profile.objects.create(
        user=user,
        role=Profile.ROLE_AUTHORITY,
        phone_number=phone,
        authority_id=authority_id,
    )


def make_station(code="DHKA"):
    return Station.objects.create(
        name="Dhaka (Kamalapur)", code=code, passengers_on_site=3180, capacity=3500
    )


def make_platform(station, number="1", occupancy=100, capacity=500, **overrides):
    return Platform.objects.create(
        station=station,
        number=number,
        occupancy=occupancy,
        capacity=capacity,
        **overrides,
    )
