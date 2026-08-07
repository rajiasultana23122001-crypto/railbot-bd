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

    # Passenger: NID + phone + password signup, OTP-verified via Twilio
    # Verify before the account can log in.
    path("auth/passenger/signup", auth_views.passenger_signup),
    path("auth/passenger/verify-signup", auth_views.passenger_verify_signup),

    # Authority: phone + a pre-issued Authority ID + password. No self-service
    # ID generation - the ID has to already exist in the AuthorityID table.
    path("auth/authority/signup", auth_views.authority_signup),

    # Shared: phone + password, either role. Role comes back in the response.
    path("auth/login", auth_views.login),
]
