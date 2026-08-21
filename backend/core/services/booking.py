"""Booking search and seat-availability logic.

Kept out of views.py because it is the one piece of the booking feature with
real rules in it (which leg of a route, how many seats are actually left);
everything in views.py stays thin request/response plumbing, matching how
the rest of the app already keeps decisions out of the view layer.
"""

from core.models import Booking

# Bangladesh Railway can resell the same physical seat across two
# non-overlapping legs of the same date (someone off at Cumilla, someone new
# on for Chattogram). This project doesn't model that: availability is
# tracked per (train, date, class) as a whole, so booking any leg on a date
# holds that seat for the entire date. Documented here rather than silently
# behaving like the real system and then not matching it.


def available_seats(train, seat_class, date):
    """(total_seats, [available seat numbers]) for one train/class/date."""
    total = train.seat_capacity.get(seat_class, 0)
    taken = set()
    for booking in Booking.objects.filter(
        train=train, travel_date=date, seat_class=seat_class, booking_status="confirmed"
    ):
        taken.update(booking.seat_numbers)

    all_seats = [f"{seat_class}-{n}" for n in range(1, total + 1)]
    return total, [seat for seat in all_seats if seat not in taken]


def ordered_stops(train):
    """This train's stops in route order.

    Reuses an already-prefetched list when there is one. train_search asks
    for prefetch_related("stops__station") across every train in the
    timetable, but train.stops.select_related(...) builds a *fresh*
    queryset, which ignores that cache and goes back to the database - one
    extra query per train, plus one per stop for the station names. Reading
    the cache directly keeps the search at the two queries it already pays
    for.
    """
    prefetched = getattr(train, "_prefetched_objects_cache", {}).get("stops")
    if prefetched is not None:
        return sorted(prefetched, key=lambda stop: stop.sequence)
    return list(train.stops.select_related("station").order_by("sequence"))


def leg_for(train, from_code, to_code):
    """The (origin stop, destination stop) for a train between two station
    codes, or None if the train doesn't call at both, in that order."""
    stops = ordered_stops(train)
    from_stop = next((s for s in stops if s.station.code == from_code), None)
    to_stop = next((s for s in stops if s.station.code == to_code), None)

    if from_stop is None or to_stop is None or from_stop.sequence >= to_stop.sequence:
        return None
    return from_stop, to_stop


def duration_minutes(from_stop, to_stop):
    """Minutes between a leg's departure and arrival, wrapping past midnight."""

    def to_minutes(hhmm):
        hours, minutes = (int(part) for part in hhmm.split(":"))
        return hours * 60 + minutes

    departure = to_minutes(from_stop.departure)
    arrival = to_minutes(to_stop.arrival)
    if arrival < departure:
        arrival += 24 * 60
    return arrival - departure
