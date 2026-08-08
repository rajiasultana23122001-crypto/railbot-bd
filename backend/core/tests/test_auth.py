"""Who can reach which endpoint at all.

Role separation is the claim these defend: an operator's board and a
passenger's dashboard are different things, and holding a token for one
must not open the other. The signup rules are here too, because an
Authority account is only as trustworthy as the ID it had to present.
"""

import json

from django.test import TestCase
from rest_framework.authtoken.models import Token

from core.models import AuthorityID, Profile

from .builders import PASSWORD, make_authority_account, make_passenger_account

# Endpoints an operator uses, which a passenger session must not reach.
AUTHORITY_ONLY = [
    "/api/station/DHKA",
    "/api/trains",
    "/api/agent-logs",
]


class RoleBoundaryTests(TestCase):
    def setUp(self):
        self.passenger, _ = make_passenger_account("+8801700000000", nid="1010101010")
        self.authority = make_authority_account("+8801900000000")

    def bearer(self, profile):
        # get_or_create, not create: Token is one per user, and these tests
        # ask for the same account's header more than once.
        token, _ = Token.objects.get_or_create(user=profile.user)
        return f"Bearer {token.key}"

    def test_passenger_cannot_reach_the_operator_endpoints(self):
        for path in AUTHORITY_ONLY:
            with self.subTest(path=path):
                response = self.client.get(
                    path, HTTP_AUTHORIZATION=self.bearer(self.passenger)
                )
                self.assertEqual(response.status_code, 403)

    def test_passenger_cannot_report_a_delay(self):
        """The one that changes state, so it gets its own test."""
        response = self.client.post(
            "/api/delays",
            data=json.dumps({"trainNo": "701", "minutes": 20}),
            content_type="application/json",
            HTTP_AUTHORIZATION=self.bearer(self.passenger),
        )
        self.assertEqual(response.status_code, 403)

    def test_authority_cannot_reach_the_passenger_dashboard(self):
        response = self.client.get(
            "/api/journeys", HTTP_AUTHORIZATION=self.bearer(self.authority)
        )
        self.assertEqual(response.status_code, 403)

    def test_the_timetable_is_open_to_both_roles(self):
        """Deliberately shared - both roles need to look up a train."""
        for profile in (self.passenger, self.authority):
            with self.subTest(role=profile.role):
                response = self.client.get(
                    "/api/train-info", HTTP_AUTHORIZATION=self.bearer(profile)
                )
                self.assertEqual(response.status_code, 200)

    def test_the_timetable_still_needs_a_token(self):
        self.assertEqual(self.client.get("/api/train-info").status_code, 401)

    def test_health_needs_no_token(self):
        """The one public endpoint, so a deploy can be checked without an account."""
        self.assertEqual(self.client.get("/api/health").status_code, 200)


class PassengerSignupTests(TestCase):
    def signup(self, phone="+8801711111111", nid="1234567890", password=PASSWORD):
        return self.client.post(
            "/api/auth/passenger/signup",
            data=json.dumps(
                {"phone_number": phone, "nid_number": nid, "password": password}
            ),
            content_type="application/json",
        )

    def login(self, phone="+8801711111111", password=PASSWORD):
        return self.client.post(
            "/api/auth/login",
            data=json.dumps({"phone_number": phone, "password": password}),
            content_type="application/json",
        )

    def test_login_is_refused_until_the_otp_is_confirmed(self):
        """An unverified account exists but cannot be used - that is the point."""
        self.assertEqual(self.signup().status_code, 201)
        self.assertFalse(Profile.objects.get(phone_number="+8801711111111").is_phone_verified)

        self.assertEqual(self.login().status_code, 403)

        self.client.post(
            "/api/auth/passenger/verify-signup",
            data=json.dumps({"phone_number": "+8801711111111", "code": "000000"}),
            content_type="application/json",
        )
        self.assertEqual(self.login().status_code, 200)

    def test_a_phone_number_can_only_be_registered_once(self):
        self.assertEqual(self.signup().status_code, 201)
        self.assertEqual(self.signup(nid="9876543210").status_code, 409)

    def test_an_nid_can_only_be_registered_once(self):
        self.assertEqual(self.signup().status_code, 201)
        self.assertEqual(self.signup(phone="+8801722222222").status_code, 409)

    def test_a_malformed_nid_is_rejected(self):
        """10 or 17 digits, nothing else - the two real BD formats."""
        for bad in ("123", "12345678901", "abcdefghij", "1234-567890"):
            with self.subTest(nid=bad):
                self.assertEqual(self.signup(nid=bad).status_code, 400)


class LoginTests(TestCase):
    def setUp(self):
        self.profile, _ = make_passenger_account("+8801700000000", nid="1010101010")

    def post_login(self, phone, password):
        return self.client.post(
            "/api/auth/login",
            data=json.dumps({"phone_number": phone, "password": password}),
            content_type="application/json",
        )

    def test_login_returns_the_role_so_the_frontend_need_not_ask(self):
        body = self.post_login("+8801700000000", PASSWORD).json()
        self.assertEqual(body["role"], Profile.ROLE_PASSENGER)
        self.assertTrue(body["token"])

    def test_wrong_password_and_unknown_number_give_the_same_answer(self):
        """Otherwise a login form doubles as a way to test which numbers exist."""
        wrong = self.post_login("+8801700000000", "not-the-password")
        unknown = self.post_login("+8801700000001", PASSWORD)

        self.assertEqual(wrong.status_code, 401)
        self.assertEqual(unknown.status_code, 401)
        self.assertEqual(wrong.json()["error"], unknown.json()["error"])

    def test_logging_in_again_invalidates_the_previous_token(self):
        first = self.post_login("+8801700000000", PASSWORD).json()["token"]
        second = self.post_login("+8801700000000", PASSWORD).json()["token"]

        self.assertNotEqual(first, second)
        self.assertFalse(Token.objects.filter(key=first).exists())


class AuthoritySignupTests(TestCase):
    def setUp(self):
        AuthorityID.objects.create(code="BR-AUTH-1001", note="test batch")

    def signup(self, phone="+8801900000000", code="BR-AUTH-1001"):
        return self.client.post(
            "/api/auth/authority/signup",
            data=json.dumps(
                {"phone_number": phone, "authority_id": code, "password": PASSWORD}
            ),
            content_type="application/json",
        )

    def test_an_issued_id_creates_an_account_with_no_otp_step(self):
        """The ID is the proof of authorization, so the account is live at once."""
        self.assertEqual(self.signup().status_code, 201)

        profile = Profile.objects.get(phone_number="+8801900000000")
        self.assertEqual(profile.role, Profile.ROLE_AUTHORITY)
        self.assertEqual(
            self.client.post(
                "/api/auth/login",
                data=json.dumps(
                    {"phone_number": "+8801900000000", "password": PASSWORD}
                ),
                content_type="application/json",
            ).status_code,
            200,
        )

    def test_an_id_that_was_never_issued_is_refused(self):
        """Nothing in this system generates authority IDs - they are handed out."""
        self.assertEqual(self.signup(code="BR-AUTH-0000").status_code, 400)
        self.assertFalse(Profile.objects.filter(phone_number="+8801900000000").exists())

    def test_an_id_can_only_be_claimed_once(self):
        self.assertEqual(self.signup().status_code, 201)
        self.assertEqual(self.signup(phone="+8801911111111").status_code, 409)
