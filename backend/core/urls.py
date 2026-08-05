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

    # Passenger: phone + NID signup, OTP-verified via Twilio Verify.
    path("auth/passenger/signup", auth_views.passenger_signup),
    path("auth/passenger/verify-signup", auth_views.passenger_verify_signup),
    path("auth/passenger/login/request-otp", auth_views.passenger_login_request_otp),
    path("auth/passenger/login/verify-otp", auth_views.passenger_login_verify_otp),

    # Station Manager: no signup route - accounts only come from
    # manage.py create_manager.
    path("auth/manager/login", auth_views.manager_login),
]
