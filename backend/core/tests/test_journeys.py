"""Who is allowed to see which bookings.

/api/journeys used to return every booking in the database to anyone
holding a passenger token. These tests pin down the rule that replaced it:
a token proves you are *a* passenger, which is not a reason to read another
passenger's travel plans.

The link between an account and its bookings can be made two ways, because
booking and signing up happen in either order. Both are tested here.
"""

import json

from django.test import TestCase
from rest_framework.authtoken.models import Token

from core.models import Booking, Passenger, Profile

from .builders import (
    PASSWORD,
    make_authority_account,
    make_booking,
    make_passenger_account,
    make_train,
)


class JourneyScopeTests(TestCase):
    """Two passengers, four bookings between them, one database."""

    def setUp(self):
        self.rumi, rumi_record = make_passenger_account(
            "+8801700000000", name="Istiak Ahammed Rumi", nid="1990123456789012"
        )
        self.rajia, rajia_record = make_passenger_account(
            "+8801800000000", name="Rajia Sultana", nid="1995987654321098"
        )

        self.train_701 = make_train("701", "Subarna Express")
        self.train_709 = make_train("709", "Parabat Express")
        self.train_705 = make_train("705", "Ekota Express")
        self.train_725 = make_train("725", "Padma Express")

        make_booking(self.train_701, rumi_record)
        make_booking(
            self.train_709,
            rumi_record,
            status="delayed",
            delay_minutes=35,
            expected_departure="19:20",
            agent_note="Manager Agent texted you the updated departure time.",
        )
        make_booking(self.train_705, rajia_record)
        make_booking(self.train_725, rajia_record)

    def journeys_for(self, profile):
        """The trains this account's dashboard would list."""
        token, _ = Token.objects.get_or_create(user=profile.user)
        response = self.client.get(
            "/api/journeys", HTTP_AUTHORIZATION=f"Bearer {token.key}"
        )
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_passenger_sees_only_their_own_bookings(self):
        self.assertEqual(Booking.objects.count(), 4)

        rumi = [j["trainNo"] for j in self.journeys_for(self.rumi)["journeys"]]
        rajia = [j["trainNo"] for j in self.journeys_for(self.rajia)["journeys"]]

        self.assertCountEqual(rumi, ["701", "709"])
        self.assertCountEqual(rajia, ["705", "725"])
        # Neither list is the whole database, and they do not overlap.
        self.assertEqual(set(rumi) & set(rajia), set())

    def test_alerts_received_counts_only_own_bookings(self):
        """The summary tile is derived from the same scoped queryset.

        Worth its own test: a count computed from the unscoped table would
        still leak - Rajia would see that somebody, somewhere, was texted.
        """
        self.assertEqual(self.journeys_for(self.rumi)["alertsReceived"], 1)
        self.assertEqual(self.journeys_for(self.rajia)["alertsReceived"], 0)

    def test_passenger_with_no_bookings_gets_an_empty_list(self):
        """An account with nothing booked is normal, not an error."""
        newcomer, _ = make_passenger_account(
            "+8801911111111", name="Nobody Yet", nid="1111111111"
        )
        body = self.journeys_for(newcomer)

        self.assertEqual(body["journeys"], [])
        self.assertEqual(body["alertsReceived"], 0)

    def test_authority_token_cannot_read_journeys(self):
        """Passenger-only means passenger-only, not 'signed in'."""
        authority = make_authority_account("+8801999999999")
        token, _ = Token.objects.get_or_create(user=authority.user)

        response = self.client.get(
            "/api/journeys", HTTP_AUTHORIZATION=f"Bearer {token.key}"
        )
        self.assertEqual(response.status_code, 403)

    def test_no_token_and_bad_token_are_both_refused(self):
        self.assertEqual(self.client.get("/api/journeys").status_code, 401)
        self.assertEqual(
            self.client.get(
                "/api/journeys", HTTP_AUTHORIZATION="Bearer not-a-real-token"
            ).status_code,
            401,
        )


class BookingToAccountLinkTests(TestCase):
    """How a booking finds its account, in both orders of events."""

    def setUp(self):
        self.train = make_train("707", "Mohanagar Provati")

    def signup(self, phone, nid):
        """Sign up and confirm the OTP, returning the new profile."""
        response = self.client.post(
            "/api/auth/passenger/signup",
            data=json.dumps(
                {"phone_number": phone, "nid_number": nid, "password": PASSWORD}
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content)

        # Twilio Verify is simulated without credentials, and accepts 000000.
        response = self.client.post(
            "/api/auth/passenger/verify-signup",
            data=json.dumps({"phone_number": phone, "code": "000000"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        return Profile.objects.get(phone_number=phone)

    def test_signup_claims_a_booking_already_made_at_the_counter(self):
        """Booked first, account opened afterwards: linked at signup."""
        phone = "+8801712345678"
        record = Passenger.objects.create(name="Walk-in Booking", phone=phone)
        make_booking(self.train, record)

        profile = self.signup(phone, "1234512345")

        self.assertEqual(profile.passenger_id, record.id)
        self.assertEqual([b.train.number for b in profile.own_bookings()], ["707"])

    def test_booking_made_after_signup_is_found_by_phone_number(self):
        """Account opened first: nothing to link, so the number does the work."""
        phone = "+8801787654321"
        profile = self.signup(phone, "5432154321")

        self.assertIsNone(profile.passenger_id)
        self.assertEqual(list(profile.own_bookings()), [])

        # The passenger now books a seat at the counter against their number.
        record = Passenger.objects.create(name="Later Booking", phone=phone)
        make_booking(self.train, record)

        self.assertEqual([b.train.number for b in profile.own_bookings()], ["707"])

    def test_signup_does_not_take_a_record_another_account_already_holds(self):
        """The link is one-to-one; a claimed record is left where it is.

        Two accounts cannot share a phone number, so this only arises when a
        Passenger row keeps a number the account linked to it has since moved
        off. The record is left where it is, and - the part that matters - the
        newcomer does not pick up its bookings through the phone fallback
        either.
        """
        phone = "+8801755555555"
        held, _ = make_passenger_account(phone, name="First Owner", nid="9999999999")
        held_record = held.passenger
        make_booking(self.train, held_record)

        # The first account moves to a new number, leaving its booking record
        # still carrying the old one. The number is the username too, so both
        # have to move for the old one to be free to register again.
        held.phone_number = "+8801766666666"
        held.save()
        held.user.username = "+8801766666666"
        held.user.save()

        newcomer = self.signup(phone, "8888888888")

        self.assertIsNone(newcomer.passenger_id)
        self.assertEqual(list(newcomer.own_bookings()), [])

        held_record.refresh_from_db()
        self.assertEqual(held_record.profile, held)
        self.assertEqual([b.train.number for b in held.own_bookings()], ["707"])
