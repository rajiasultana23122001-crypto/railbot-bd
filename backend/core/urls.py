"""API routes.

The paths match what the React client already calls, so moving the backend to
Django changed only the port the client points at.
"""

from django.urls import path

from . import auth_views, views

urlpatterns = [
    path("health", views.health),
    path("journeys", views.journeys),
    path("station/<str:code>", views.station),
    path("trains", views.trains),
    path("train-info", views.train_info),
    path("agent-logs", views.agent_logs),
    path("delays", views.report_delay),
    path("agents/run", views.run_agents),

    # Booking: search a route, see a seat map, book it, view or cancel the
    # ticket afterwards. Passenger-only - see views.py for why.
    path("stations", views.stations),
    path("trains/search", views.train_search),
    path("trains/<int:train_id>/seats", views.train_seats),
    path("bookings", views.create_booking),
    path("bookings/<str:pnr>", views.booking_detail),
    path("bookings/<int:booking_id>/cancel", views.cancel_booking),

    # Passenger: NID + phone + password signup, OTP-verified via sms.net.bd
    # (core.services.otp) before the account can log in.
    path("auth/passenger/signup", auth_views.passenger_signup),
    path("auth/passenger/verify-signup", auth_views.passenger_verify_signup),

    # Authority: phone + a pre-issued Authority ID + password. No self-service
    # ID generation - the ID has to already exist in the AuthorityID table.
    path("auth/authority/signup", auth_views.authority_signup),

    # Shared: phone + password, either role. Role comes back in the response.
    path("auth/login", auth_views.login),
]
